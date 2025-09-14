import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from langchain.tools import tool
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeatherAPIError(Exception):
    """Custom exception for Weather API errors"""
    pass

def get_weather_forecast(days: int = 14) -> List[Dict]:
    """
    Fetches weather forecast for Atlanta using OpenWeatherMap API v3.0.
    Returns cleaned data for the specified number of days.
    
    Args:
        days: Number of days to forecast (max 16 for free tier, default: 14)
        
    Returns:
        List of dictionaries containing daily weather data
        
    Raises:
        WeatherAPIError: If API call fails or returns error
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        raise WeatherAPIError("OPENWEATHER_API_KEY not found in environment variables")
    
    # Atlanta coordinates (lat, lon)
    lat, lon = 33.7490, -84.3880
    
    # API endpoint for 16-day forecast
    url = f"https://api.openweathermap.org/data/3.0/onecall"
    
    params = {
        "lat": lat,
        "lon": lon,
        "exclude": "minutely,hourly,current,alerts",
        "appid": api_key,
        "units": "imperial"  # Use imperial for Fahrenheit
    }
    
    try:
        logger.info(f"Fetching {days}-day weather forecast for Atlanta...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'daily' not in data:
            raise WeatherAPIError("No daily forecast data in API response")
        
        # Process and clean the forecast data
        cleaned_forecast = []
        for i, day_data in enumerate(data['daily'][:days]):
            try:
                forecast_day = {
                    'date': datetime.fromtimestamp(day_data['dt']).strftime('%Y-%m-%d'),
                    'day_of_week': datetime.fromtimestamp(day_data['dt']).strftime('%A'),
                    'max_temp_f': round(day_data['temp']['max'], 1),
                    'min_temp_f': round(day_data['temp']['min'], 1),
                    'feels_like_day_f': round(day_data['feels_like']['day'], 1),
                    'humidity': day_data['humidity'],
                    'precipitation_probability': day_data.get('pop', 0) * 100,  # Convert to percentage
                    'weather_condition': day_data['weather'][0]['main'],
                    'weather_description': day_data['weather'][0]['description'],
                    'wind_speed_mph': round(day_data['wind_speed'], 1),
                    'cloud_coverage': day_data['clouds']
                }
                cleaned_forecast.append(forecast_day)
                
            except KeyError as e:
                logger.warning(f"Missing key {e} in day {i} forecast data, skipping...")
                continue
        
        logger.info(f"Successfully retrieved forecast for {len(cleaned_forecast)} days")
        return cleaned_forecast
        
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {e}"
        logger.error(error_msg)
        raise WeatherAPIError(error_msg)
    except ValueError as e:
        error_msg = f"Failed to parse API response: {e}"
        logger.error(error_msg)
        raise WeatherAPIError(error_msg)

def calculate_demand_factor(weather_data: List[Dict]) -> List[Dict]:
    """
    Calculates ice cream demand adjustment factor based on weather conditions.
    
    Args:
        weather_data: List of daily weather forecasts
        
    Returns:
        List of dictionaries with added demand_factor
    """
    demand_forecast = []
    
    for day in weather_data:
        # Base demand factor (1.0 = normal demand)
        demand_factor = 1.0
        
        # Temperature impact (exponential increase with heat)
        if day['max_temp_f'] > 85:
            demand_factor *= 1.0 + (day['max_temp_f'] - 85) * 0.05  # 5% increase per degree above 85
        elif day['max_temp_f'] < 60:
            demand_factor *= 0.7  # 30% reduction in cold weather
        
        # Humidity impact (higher humidity feels hotter)
        if day['humidity'] > 70 and day['max_temp_f'] > 75:
            demand_factor *= 1.2
        
        # Precipitation impact (rain reduces demand)
        if day['precipitation_probability'] > 50:
            demand_factor *= 0.6  # 40% reduction on rainy days
        elif day['precipitation_probability'] > 25:
            demand_factor *= 0.8  # 20% reduction on potentially rainy days
        
        # Sunny weather boost
        if day['weather_condition'] == 'Clear' and day['max_temp_f'] > 75:
            demand_factor *= 1.3
        
        # Ensure reasonable bounds
        demand_factor = max(0.3, min(3.0, demand_factor))
        
        day_with_demand = day.copy()
        day_with_demand['demand_factor'] = round(demand_factor, 2)
        demand_forecast.append(day_with_demand)
    
    return demand_forecast

@tool
def get_weather_and_demand_forecast(days: int = 8) -> str:
    """
    Fetches weather forecast for Atlanta and calculates ice cream demand adjustment factors.
    Returns a summary of the weather impact on demand for the specified number of days.
    
    Args:
        days: Number of days to forecast (default: 8)
        
    Returns:
        String summary of weather impact on demand
    """
    try:
        weather_data = get_weather_forecast(days)
        demand_data = calculate_demand_factor(weather_data)
        
        # Create a summary string for the LLM
        summary_lines = [
            f"Weather Impact on Ice Cream Demand Forecast for Atlanta:",
            f"Forecast Period: {demand_data[0]['date']} to {demand_data[-1]['date']}",
            f"{'-' * 60}"
        ]
        
        for day in demand_data:
            summary_lines.append(
                f"{day['day_of_week']} ({day['date']}): "
                f"{day['max_temp_f']}°F, {day['weather_description']}, "
                f"Demand Factor: {day['demand_factor']}x"
            )
        
        # Add overall impact summary
        avg_demand_factor = sum(day['demand_factor'] for day in demand_data) / len(demand_data)
        summary_lines.extend([
            f"{'-' * 60}",
            f"Average Demand Factor: {avg_demand_factor:.2f}x normal",
            f"Overall Impact: {'↑ Increase' if avg_demand_factor > 1.0 else '↓ Decrease'} in expected demand"
        ])
        
        return "\n".join(summary_lines)
        
    except WeatherAPIError as e:
        return f"Error fetching weather data: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in weather tool: {e}")
        return f"Failed to generate weather forecast: {str(e)}"

# Alternative tool that returns raw data for other tools to use
@tool
def get_weather_data_raw(days: int = 8) -> List[Dict]:
    """
    Fetches raw weather forecast data for Atlanta. Returns list of daily forecasts.
    Use this tool when you need the actual data values for calculations.
    
    Args:
        days: Number of days to forecast (default: 8)
        
    Returns:
        List of dictionaries with detailed weather data
    """
    try:
        weather_data = get_weather_forecast(days)
        return calculate_demand_factor(weather_data)
    except Exception as e:
        logger.error(f"Error in get_weather_data_raw: {e}")
        return []
    
@tool
def get_average_demand_factor(days: int = 8) -> float:
    """
    Calculates and returns the average ice cream demand adjustment factor based on weather conditions.
    This is useful for quick decision-making without needing the full weather details.
    
    Args:
        days: Number of days to calculate average for (default: 8)
        
    Returns:
        Float representing the average demand multiplier factor
    """
    try:
        weather_data = get_weather_forecast(days)
        demand_data = calculate_demand_factor(weather_data)
        
        if not demand_data:
            logger.warning("No demand data available, returning default factor 1.0")
            return 1.0
        
        avg_demand_factor = sum(day['demand_factor'] for day in demand_data) / len(demand_data)
        logger.info(f"Calculated average demand factor: {avg_demand_factor:.2f}x for {days} days")
        
        return round(avg_demand_factor, 2)
        
    except Exception as e:
        logger.error(f"Error calculating average demand factor: {e}")
        return 1.0  # Return neutral factor on error

# Example usage
if __name__ == "__main__":
    # Test the function
    try:
        forecast = get_weather_forecast(5)
        print("5-Day Weather Forecast for Atlanta:")
        for day in forecast:
            print(f"{day['date']}: {day['max_temp_f']}°F, {day['weather_description']}")
        
        print("\n" + "="*50 + "\n")
        
        # Test the LangChain tool PROPERLY
        # Tools expect a dictionary input, even if it's empty
        summary = get_weather_and_demand_forecast.invoke({})    # invoke({"days": 8})
        print("8-Day Weather Summary (default):")
        print(summary)
        
        print("\n" + "="*50 + "\n")

        # Test the average demand factor tool
        avg_factor = get_average_demand_factor.invoke({"days": 8})
        print(f"8-Day Average Demand Factor: {avg_factor}x")
        
        print("\n" + "="*50 + "\n")
        
        # Test the raw data tool
        raw_data = get_weather_data_raw.invoke({"days": 3})
        print("Raw 3-Day Weather Data:")
        for day in raw_data:
            print(f"{day['date']}: {day['max_temp_f']}°F, Demand Factor: {day['demand_factor']}x")
        
    except Exception as e:
        print(f"Error: {e}")