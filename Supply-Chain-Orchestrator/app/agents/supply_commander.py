from app.graph.state import AgentState, Recommendation
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
import logging
import json
from dotenv import load_dotenv
import os
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)
# Load environment variables from .env file
load_dotenv()   # .env is at the project root
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini-2024-07-18")

# Initialize LLM
llm = ChatOpenAI(
    temperature=0.1, 
    model=GPT_MODEL,
    openai_api_key=OPENAI_API_KEY
)

def supply_commander_agent(state: AgentState) -> Dict[str, Any]:
    """
    Supply Commander Agent: Uses LLM to make ordering decisions based on all available data.
    """
    logger.info("Supply Commander making ordering decision")
    
    updates = {}
    
    try:
        print(f"* State at Supply Commander:\n{state}\n")
        # Prepare context for LLM
        context = prepare_decision_context(state)
        
        # Get LLM recommendation
        recommendation = get_llm_recommendation(context, state)
        logger.debug(f"LLM Recommendation: {recommendation}")
        
        updates["recommendation"] = recommendation.model_dump()
        updates["current_step"] = "decision_complete"
        updates["errors"] = state.errors
        
    except Exception as e:
        error_msg = f"Supply Commander error: {str(e)}"
        logger.error(error_msg)
        updates["errors"] = state.errors + [error_msg]
    
    return updates  # state.copy(update=updates)

def prepare_decision_context(state: AgentState) -> str:
    """Prepare context string for LLM decision making"""
    context_parts = []
    
    # Product and inventory info
    if state.product_info:
        context_parts.append(f"PRODUCT: {state.product_info.product_name}")  # Pydantic model
        context_parts.append(f"CURRENT INVENTORY: {state.product_info.current_inventory} units")
        context_parts.append(f"REORDER POINT: {state.product_info.reorder_point} units")

    # Baseline forecast
    if state.baseline_forecast:
        context_parts.append(f"BASELINE FORECAST: {state.baseline_forecast.total_predicted_demand} units over {state.forecast_days} days")
    
    # Weather impact
    context_parts.append(f"WEATHER DEMAND FACTOR: {state.average_demand_factor}x")
    
    # Supplier info
    if state.supplier_info and state.supplier_info.supplier_name:
        supp = state.supplier_info
        context_parts.append(f"SUPPLIER: {supp.supplier_name}, {supp.lead_time_days} days lead time, "
                               f"MOQ of {supp.min_order_quantity} units, Cost of ${supp.cost_per_unit}/unit")

    return "\n".join(context_parts)

def get_llm_recommendation(context: str, state: AgentState) -> Recommendation:
    """Get ordering recommendation from LLM"""
    prompt = f"""
    You are a Supply Chain Commander for an ice cream company. Make an ordering decision based on:

    {context}

    Consider:
    1. Projected demand (baseline x weather factor)
    2. Current inventory vs reorder point
    3. Supplier lead times and minimum order quantities
    4. Cost optimization

    Respond ONLY with valid JSON in this format:
    ```json
    {{
    "order_quantity": 300,
    "supplier_name": "Atlanta Ice Cream Supplier",
    "justification": "...",
    "confidence_score": 0.0 - 1.0
    }}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    # print(f"LLM Response:\n{response.content}\n")

    json_match = re.search(r'json\s*\n?({.*?})\s*\n?', response.content, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        recommendation_data = json.loads(json_str)
    else:
        raise ValueError("No JSON found in LLM response")
    
    return Recommendation(
        product_code=state.product_code,
        **recommendation_data
    )