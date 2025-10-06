from typing import Dict, Any
from app.graph.state import AgentState
from app.tools.database_tools import get_product_info, get_historical_sales, get_supplier_info
from app.tools.forecast_tools import get_baseline_forecast
import logging

logger = logging.getLogger(__name__)

def data_analyst_agent(state: AgentState) -> AgentState:
    """
    Data Analyst Agent: Gathers product information, inventory, and generates baseline forecast.
    """
    logger.info(f"Data Analyst processing product: {state.product_code}")
    
    updates = {}
    
    try:
        # Get product and inventory info
        product_result = get_product_info.invoke({"product_code": state.product_code})
        if product_result.get("success"):
            updates["product_info"] = product_result
        
        # Get supplier information
        supplier_result = get_supplier_info.invoke({"product_code": state.product_code})
        if supplier_result.get("success") and supplier_result.get("suppliers"):
            updates["supplier_info"] = supplier_result.get("suppliers")
        
        # Get historical sales data for analysis
        historical_result = get_historical_sales.invoke({"product_code": state.product_code, "days": state.forecast_days})
        logger.info(f"* Historical data retrieved: \n{historical_result}")
        if historical_result.get("success"):            
            updates["historical_sales_data"] = historical_result.get("sales_data", [])
            logger.info(f"Retrieved {len(historical_result['sales_data'])} historical sales records")

        # Get baseline forecast
        forecast_result = get_baseline_forecast.invoke({
            "product_code": state.product_code, 
            "forecast_days": state.forecast_days
        })
        if forecast_result.get("success"):
            # Calculate total predicted demand
            total_demand = sum(day["predicted_demand"] for day in forecast_result["forecast"])
            
            # Create ForecastResult with expected fields
            forecast_data = {
                "product_code": forecast_result["product_code"],
                "success": forecast_result["success"],
                "forecast": forecast_result["forecast"],
                "total_predicted_demand": total_demand,
                "model_used": "exponential_smoothing"
            }
            updates["baseline_forecast"] = forecast_data
        
        updates["current_step"] = "data_analysis_complete"
        updates["errors"] = state.errors  # Preserve existing errors
        
    except Exception as e:
        error_msg = f"Data Analyst error: {str(e)}"
        logger.error(error_msg)
        updates["errors"] = state.errors + [error_msg]
    
    return updates