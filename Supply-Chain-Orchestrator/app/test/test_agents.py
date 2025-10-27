import unittest
from unittest.mock import patch
from app.graph.state import create_initial_state
from app.agents.data_analyst import data_analyst_agent
from app.agents.weather import weather_agent

class TestAgents(unittest.TestCase):
    
    def setUp(self):
        """Set up initial state for each test"""
        # Create a fresh state for each test to ensure isolation
        self.initial_state = create_initial_state("vanilla", 8)
        # Mock responses for all external tools
        self.mock_product_info = {
            "success": True, 
            "product_name": "Vanilla Ice Cream",
            "current_inventory": 150
        }
        self.mock_supplier_info = {
            "success": True,
            "suppliers": ["Supplier A", "Supplier B"]
        }
        self.mock_historical_sales = {
            "success": True,
            "sales_data": [{"date": "2025-10-01", "sales": 100}]
        }
        self.mock_forecast = {
            "success": True,
            "forecast": [
                {"date": "2025-10-02", "predicted_demand": 102},
                {"date": "2025-10-03", "predicted_demand": 105}
            ],
            "product_code": "vanilla"
        }
    
    # DATA ANALYST AGENT TESTS
    def test_data_analyst_successful_flow(self):
        """
        Test the happy path where all external calls succeed
        This verifies the agent integrates all data correctly
        """
        
        # Patch all external dependencies
		# Replaces real tools with mock objects during the test. 
		# @patch temporarily replaces the specified functions with mock objects
        with patch('app.agents.data_analyst.get_product_info') as mock_product, \
             patch('app.agents.data_analyst.get_supplier_info') as mock_supplier, \
             patch('app.agents.data_analyst.get_historical_sales') as mock_historical, \
             patch('app.agents.data_analyst.get_baseline_forecast') as mock_forecast_tool:
            
            # Configure mock return values
			# Mock tool responses
			# Defines what the mocked tools should return when called
			# avoid actual database/API calls during testing
			# .invoke.return_value sets what the tool returns when .invoke() is called
            mock_product.invoke.return_value = self.mock_product_info
            mock_supplier.invoke.return_value = self.mock_supplier_info
            mock_historical.invoke.return_value = self.mock_historical_sales
            mock_forecast_tool.invoke.return_value = self.mock_forecast
            
            # Execute the agent
            result = data_analyst_agent(self.initial_state)
            
            # Verify all external tools were called with correct parameters
            mock_product.invoke.assert_called_once_with({"product_code": "vanilla"})
            mock_supplier.invoke.assert_called_once_with({"product_code": "vanilla"})
            mock_historical.invoke.assert_called_once_with({"product_code": "vanilla", "days": 14})
            mock_forecast_tool.invoke.assert_called_once_with({
                "product_code": "vanilla", 
                "forecast_days": 8
            })
            
            # Verify the agent processed and transformed data correctly
            self.assertEqual(result["product_info"], self.mock_product_info)
            self.assertEqual(result["supplier_info"], ["Supplier A", "Supplier B"])
            self.assertEqual(result["historical_sales_data"], [{"date": "2025-10-01", "sales": 100}])
            
            # Verify forecast data was properly transformed
            self.assertTrue("baseline_forecast" in result)
            # Test the specific logic for calculating total predicted demand, this verifies the business logic is correct
            self.assertEqual(result["baseline_forecast"]["total_predicted_demand"], 207)  # 102 + 105
            self.assertEqual(result["baseline_forecast"]["model_used"], "exponential_smoothing")
            
            # Verify state progression
            self.assertEqual(result["current_step"], "data_analysis_complete")
            self.assertEqual(result["errors"], [])  # No errors in successful flow
    
    def test_data_analyst_partial_failures(self):
        """
        Test the agent's resilience when some external calls fail
        This ensures graceful degradation
        """
        with patch('app.agents.data_analyst.get_product_info') as mock_product, \
             patch('app.agents.data_analyst.get_supplier_info') as mock_supplier, \
             patch('app.agents.data_analyst.get_historical_sales') as mock_historical, \
             patch('app.agents.data_analyst.get_baseline_forecast') as mock_forecast:
            
            # Some calls succeed, some fail
            mock_product.invoke.return_value = self.mock_product_info
            mock_supplier.invoke.return_value = {"success": False}  # Supplier call fails
            mock_historical.invoke.return_value = self.mock_historical_sales
            mock_forecast.invoke.return_value = self.mock_forecast
            
            result = data_analyst_agent(self.initial_state)
            # print(f"--Result from partial failure test: {result}")
            
            # Verify successful data is included
            self.assertIn("product_info", result)
            self.assertIn("historical_sales_data", result)
            self.assertIn("baseline_forecast", result)
            
            # Verify failed call doesn't add its data
            self.assertNotIn("supplier_info", result)
            
            # Verify no errors were added (non-critical failures are handled gracefully)
            self.assertEqual(result["errors"], [])
    
    # WEATHER AGENT TESTS
    def test_weather_agent_successful_flow(self):
        """
        Test weather agent successfully fetches and processes weather data
        """
        mock_weather_data = {
            "days": [
                {"date": "2025-10-01", "temperature": 45, "condition": "sunny"}
            ]
        }
        mock_demand_factor = {"average_factor": 1.2}
        
        with patch('app.agents.weather.get_weather_data_raw') as mock_weather, \
             patch('app.agents.weather.get_average_demand_factor') as mock_factor:
            
            mock_weather.invoke.return_value = mock_weather_data
            mock_factor.invoke.return_value = mock_demand_factor
            
            result = weather_agent(self.initial_state)
            
            # Verify correct API calls
            mock_weather.invoke.assert_called_once_with({"days": 8})
            mock_factor.invoke.assert_called_once_with({"days": 8})
            
            # Verify data integration
            self.assertEqual(result["weather_forecast"], mock_weather_data)
            self.assertEqual(result["average_demand_factor"], mock_demand_factor)
            self.assertEqual(result["current_step"], "weather_analysis_complete")
            self.assertEqual(result["errors"], [])

    
    def test_weather_agent_with_different_forecast_days(self):
        """
        Test that weather agent correctly uses the forecast_days from state
        This ensures parameter propagation is working
        """
        # Test with different forecast days
        state_5_days = create_initial_state("chocolate", 5)
        
        with patch('app.agents.weather.get_weather_data_raw') as mock_weather, \
             patch('app.agents.weather.get_average_demand_factor') as mock_factor:
            
            mock_weather.invoke.return_value = {"days": []}
            mock_factor.invoke.return_value = {"average_factor": 1.0}
            
            weather_agent(state_5_days)
            
            # Verify the correct number of days was passed to weather tools
            mock_weather.invoke.assert_called_once_with({"days": 5})
            mock_factor.invoke.assert_called_once_with({"days": 5})

if __name__ == '__main__':
    unittest.main()