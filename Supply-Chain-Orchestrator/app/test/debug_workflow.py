from app.graph.workflow import create_supply_chain_workflow
from app.graph.state import create_initial_state, AgentState

def debug_workflow():
    """Debug the workflow compilation"""
    print("🔍 Debugging workflow compilation...")
    
    # Test creating the workflow
    workflow = create_supply_chain_workflow()
    print(f"Workflow type: {type(workflow)}")   # Should be CompiledStateGraph
    print(f"State model fields: {AgentState.model_fields.keys()}")

    # 🔹 Optional: Print node definitions
    print(f"Nodes in graph: {list(workflow.nodes.keys())}")
    # print(f"Edges in graph: {workflow.edges}")

    # Test with a simple state
    initial_state = create_initial_state("vanilla", 3)
    print(f"Initial state: {initial_state.model_dump()}")
    
    # Try a synchronous invoke first
    try:
        final_state = workflow.invoke(initial_state)
        print(f"Final state (sync): {type(final_state)}")
        print(f"Final state content: {final_state}")
    except Exception as e:
        print(f"Sync invoke failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_workflow()