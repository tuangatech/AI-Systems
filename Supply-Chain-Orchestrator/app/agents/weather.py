from app.graph.state import AgentState
from app.tools.weather_tools import get_weather_data_raw, get_average_demand_factor
import logging

logger = logging.getLogger(__name__)

def weather_agent(state: AgentState) -> AgentState:
    """
    Weather Agent: Fetches weather data and calculates demand impact.
    """
    logger.info("Weather analyzing weather impact")
    
    updates = {}
    
    try:
        # Get detailed weather data
        weather_data = get_weather_data_raw.invoke({"days": state.forecast_days})
        updates["weather_forecast"] = weather_data
        
        # Get average demand factor
        avg_factor = get_average_demand_factor.invoke({"days": state.forecast_days})
        updates["average_demand_factor"] = avg_factor
        
        updates["current_step"] = "weather_analysis_complete"
        updates["errors"] = state.errors
        
    except Exception as e:
        error_msg = f"Weather error: {str(e)}"
        logger.error(error_msg)
        updates["errors"] = state.errors + [error_msg]
    
    return updates  # state.model_copy(update=updates)