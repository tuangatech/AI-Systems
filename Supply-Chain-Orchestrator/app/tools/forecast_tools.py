from langchain.tools import tool
from app.models.forecaster import DemandForecaster
import os
import pandas as pd
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
# Initialize the forecaster
database_url = os.getenv("DATABASE_URL")
forecaster = DemandForecaster(database_url)

@tool
def get_baseline_forecast(product_code: str, forecast_days: Optional[int] = 8) -> dict:
    """
    Get a baseline demand forecast for a product using historical sales data.
    Returns predicted demand for the specified number of days starting from tomorrow.
    
    Args:
        product_code: The ID of the product to forecast demand for
        forecast_days: Number of days to forecast ahead (default: 14)
        
    Returns:
        Dictionary with forecast results and metadata
    """
    return forecaster.get_baseline_forecast(product_code, forecast_days)


# Example usage
if __name__ == "__main__":    
    # Get forecast for a product
    result = forecaster.get_baseline_forecast("vanilla", 8)
    
    if result["success"]:
        print(f"Forecast for product {result['product_code']}:")
        for day_forecast in result["forecast"]:
            print(f"{day_forecast['date']}: {day_forecast['predicted_demand']:.1f} units")
        
        total_demand = sum(day["predicted_demand"] for day in result["forecast"])
        print(f"\nTotal 14-day forecast: {total_demand:.0f} units")
    else:
        print(f"Error: {result['error']}")
