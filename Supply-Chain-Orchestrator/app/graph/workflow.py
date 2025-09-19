from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.agents.data_analyst import data_analyst_agent
from app.agents.weather import weather_agent
from app.agents.supply_commander import supply_commander_agent
from app.agents.reporter import reporter_agent

def create_supply_chain_workflow():
    """Create the complete supply chain workflow graph"""
    workflow = StateGraph(AgentState)
    
    # Add all agents as nodes
    workflow.add_node("data_analyst", data_analyst_agent)
    workflow.add_node("weather", weather_agent)
    workflow.add_node("supply_commander", supply_commander_agent)
    workflow.add_node("reporter", reporter_agent)
    
    # Define the execution flow
    workflow.set_entry_point("data_analyst")
    workflow.add_edge("data_analyst", "weather")
    workflow.add_edge("weather", "supply_commander")
    workflow.add_edge("supply_commander", "reporter")
    workflow.add_edge("reporter", END)
    
    return workflow.compile()

# Global workflow instance
supply_chain_workflow = create_supply_chain_workflow()