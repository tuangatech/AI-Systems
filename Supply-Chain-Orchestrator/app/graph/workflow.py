from langgraph.graph import StateGraph, END
from app.graph.state import AgentState
from app.agents.data_analyst import data_analyst_agent
from app.agents.weather import weather_agent
from app.agents.supply_commander import supply_commander_agent
from app.agents.reporter import reporter_agent

# def create_supply_chain_workflow():
#     """Create the complete supply chain workflow graph"""
#     workflow = StateGraph(AgentState)
    
#     # Add all agents as nodes
#     workflow.add_node("data_analyst", data_analyst_agent)
#     workflow.add_node("weather", weather_agent)
#     workflow.add_node("supply_commander", supply_commander_agent)
#     workflow.add_node("reporter", reporter_agent)
    
#     # Define the execution flow
#     workflow.set_entry_point("data_analyst")
#     workflow.add_edge("data_analyst", "weather")
#     workflow.add_edge("weather", "supply_commander")
#     workflow.add_edge("supply_commander", "reporter")
#     workflow.add_edge("reporter", END)
    
#     return workflow.compile()

def create_supply_chain_workflow():
    """Create the complete supply chain workflow graph with parallel data_analyst and weather agents"""
    workflow = StateGraph(AgentState)

    # Add all agents as nodes
    workflow.add_node("data_analyst", data_analyst_agent)
    workflow.add_node("weather", weather_agent)
    workflow.add_node("supply_commander", supply_commander_agent)
    workflow.add_node("reporter", reporter_agent)

    # --- Define Conditional Logic to Wait for Both Agents ---

    def after_data_analyst_route(state: AgentState):
        """After Data Analyst runs, decide whether to run Weather or move forward"""
        # If weather result already exists, both are done → go to supply_commander
        if len(state.weather_forecast) > 0:
            return "supply_commander"
        # Otherwise, need to run weather agent next
        return "weather"

    def after_weather_route(state: AgentState):
        """After Weather runs, check if baseline_forecast exists"""
        if state.baseline_forecast is not None:
            return "supply_commander"
        return "data_analyst"

    # --- Set up edges ---

    # Start with Data Analyst (arbitrary choice; could be either)
    workflow.set_entry_point("data_analyst")

    # From data_analyst, conditionally route
    workflow.add_conditional_edges(
        "data_analyst",
        after_data_analyst_route,
        {
            "weather": "weather",
            "supply_commander": "supply_commander"
        }
    )

    # From weather, conditionally route
    workflow.add_conditional_edges(
        "weather",
        after_weather_route,
        {
            "data_analyst": "data_analyst",
            "supply_commander": "supply_commander"
        }
    )

    # Once both are done, flow proceeds to supply_commander
    workflow.add_edge("supply_commander", "reporter")
    workflow.add_edge("reporter", END)

    return workflow.compile()


# Global workflow instance
supply_chain_workflow = create_supply_chain_workflow()