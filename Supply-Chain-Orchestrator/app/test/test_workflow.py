"""
Test script for the Meltaway Supply Chain Workflow
"""
import matplotlib
# Use non-interactive backend to avoid Tkinter issues
matplotlib.use('Agg')  # ← Add this before importing any matplotlib stuff
import asyncio
import json
from app.graph.state import create_initial_state
from app.graph.workflow import supply_chain_workflow
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_workflow_basic():
    """Test the complete workflow with a sample product"""
    print("🚀 Testing Meltaway Supply Chain Workflow")
    print("=" * 60)
    
    # Create initial state
    initial_state = create_initial_state("vanilla", 3)
    print(f"📦 Product: {initial_state.product_code}")
    print(f"📅 Forecast Days: {initial_state.forecast_days}")
    print("=" * 60)
    
    try:
        # Run the workflow
        print("🔄 Starting workflow execution...")
        final_state = supply_chain_workflow.invoke(initial_state)

        print(f"Final state type: {type(final_state)}")
        print(f"Final state content: {final_state}")

        # print("> Full state:\n", final_state.dict())
        
        print("✅ Workflow completed successfully!")
        print("=" * 60)
        
        # Display results
        print("📊 RESULTS SUMMARY:")

        # Convert to AgentState for easy access
        from app.graph.state import AgentState
        agent_state = AgentState(**final_state)
        
        print(f"Current Step: {agent_state.current_step}")
        if agent_state.product_info:
            print(f"Current Inventory: {agent_state.product_info.current_inventory} units")
        
        if agent_state.baseline_forecast:
            print(f"Baseline Forecast: {agent_state.baseline_forecast.total_predicted_demand:.0f} units")
        
        print(f"Weather Demand Factor: {agent_state.average_demand_factor:.2f}x")
        
        if agent_state.recommendation:
            print(f"Recommended Order: {agent_state.recommendation.order_quantity} units")
            print(f"Supplier: {agent_state.recommendation.supplier_name}")
            print(f"Confidence: {agent_state.recommendation.confidence_score:.1%}")
        
        if agent_state.executive_summary:
            print("\n📋 EXECUTIVE SUMMARY:")
            print(agent_state.executive_summary[:200] + "..." if len(agent_state.executive_summary) > 200 else agent_state.executive_summary)
        
        if agent_state.errors:
            print(f"\n❌ Errors encountered: {len(agent_state.errors)}")
            for error in agent_state.errors:
                print(f"  - {error}")
        
        # Save full state for inspection
        with open('workflow_test_result.json', 'w') as f:
            state_dict = agent_state.model_dump()
            # Convert any non-serializable objects
            for key, value in state_dict.items():
                if hasattr(value, 'dict'):
                    state_dict[key] = value.dict()
            json.dump(state_dict, f, indent=2)
        
        print(f"\n💾 Full results saved to 'workflow_test_result.json'")
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()

async def test_multiple_products():
    """Test workflow with different products"""
    test_products = ["vanilla", "chocolate"]
    
    for product_code in test_products:
        print(f"\n🧪 Testing product: {product_code}")
        print("-" * 40)
        
        initial_state = create_initial_state(product_code, 7)  # 7-day forecast for quick test
        
        try:
            final_state = await supply_chain_workflow.ainvoke(initial_state)
            print(f"✅ {product_code}: Success")
            if final_state.recommendation:
                print(f"   Order: {final_state.recommendation.order_quantity} units")
        except Exception as e:
            print(f"❌ {product_code}: Failed - {e}")

def test_individual_agents():
    """Test each agent individually"""
    print("\n🔍 Testing Individual Agents")
    print("=" * 60)
    
    from app.agents.data_analyst import data_analyst_agent
    
    # Test Data Analyst agent
    initial_state = create_initial_state("chocolate", 8)
    print("Testing Data Analyst agent...")
    
    try:
        state_after_analyst = data_analyst_agent(initial_state)
        print("✅ Data Analyst: Success")
        if state_after_analyst.product_info:
            print(f"   Inventory: {state_after_analyst.product_info.current_inventory} units")
    except Exception as e:
        print(f"❌ Data Analyst: Failed - {e}")

async def main():
    """Main test function"""
    print("Meltaway Supply Chain Workflow Tests")
    print("=" * 60)
    
    # Run individual tests
    # test_individual_agents()
    
    # Run basic workflow test
    await test_workflow_basic()
    
    # Run multiple products test (optional)
    # await test_multiple_products()

if __name__ == "__main__":
    asyncio.run(main())