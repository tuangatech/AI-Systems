import unittest
from unittest.mock import patch, MagicMock
from app.graph.state import create_initial_state, AgentState
from app.agents.data_analyst import data_analyst_agent
from app.agents.meteorologist import meteorologist_agent
import json

# ** Tests only the agent logic, NOT the tools they call **
class TestAgents(unittest.TestCase):
    
    def setUp(self):
        self.initial_state = create_initial_state("vanilla", 8)
    
    # Replaces real tools with mock objects during the test. 
    # @patch temporarily replaces the specified functions with mock objects
    @patch('app.agents.data_analyst.get_product_info')
    @patch('app.agents.data_analyst.get_historical_sales')
    @patch('app.agents.data_analyst.get_baseline_forecast')
    def test_data_analyst_agent(self, mock_forecast, mock_sales, mock_product):
        """Test Data Analyst agent with mocked tools"""
        
        # Mock tool responses
        # Defines what the mocked tools should return when called
        # avoid actual database/API calls during testing
        # .invoke.return_value sets what the tool returns when .invoke() is called
        mock_product.invoke.return_value = {
            "success": True,
            "product_code": "vanilla",
            "product_name": "Vanilla Ice Cream",
            "current_inventory": 1500,
            "reorder_point": 1000
        }
        
        mock_sales.invoke.return_value = {
            "success": True,
            "sales_data": [],
            "summary": {"total_sales_units": 5000}
        }
        
        mock_forecast.invoke.return_value = {
            "success": True,
            "total_predicted_demand": 4200,
            "forecast": []
        }
        
        # Executes the agent function with the initial state
        result_state = data_analyst_agent(self.initial_state)
        
        # Assertions to verify that the agent worked correctly
        self.assertEqual(result_state.current_step, "data_analysis_complete")   # updated the current step
        self.assertIsNotNone(result_state.product_info)                         # product info was set
        self.assertIsNotNone(result_state.baseline_forecast)                    # forecast was set
        self.assertEqual(result_state.product_info["current_inventory"], 1500)  # correct inventory value
    
    @patch('app.agents.meteorologist.get_weather_data_raw')
    @patch('app.agents.meteorologist.get_average_demand_factor')
    def test_meteorologist_agent(self, mock_avg_factor, mock_weather):
        """Test Meteorologist agent with mocked tools"""
        
        # Mock tool responses
        mock_weather.invoke.return_value = [
            {"date": "2025-09-15", "max_temp_f": 88, "demand_factor": 1.5}
        ]
        
        mock_avg_factor.invoke.return_value = 1.8
        
        # Run the agent
        result_state = meteorologist_agent(self.initial_state)
        
        # Assertions
        self.assertEqual(result_state.current_step, "weather_analysis_complete")
        self.assertEqual(result_state.average_demand_factor, 1.8)
        self.assertEqual(len(result_state.weather_forecast), 1)


if __name__ == '__main__':
    unittest.main()