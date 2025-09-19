#!/usr/bin/env python3
import asyncio
from app.graph.state import create_initial_state

def test_agent_returns(agent_func, agent_name):
    """Test what an agent returns"""
    print(f"\n🔍 Testing {agent_name}...")
    state = create_initial_state("vanilla", 5)
    
    try:
        result = agent_func(state)
        print(f"   Return type: {type(result)}")
        print(f"   Return value: {result}")
        
        if not isinstance(result, dict):
            print(f"❌❌❌ {agent_name} returns {type(result)}, expected dict!")
            return False
        else:
            print(f"✅ {agent_name} returns correct type (dict)")
            return True
            
    except Exception as e:
        print(f"❌ {agent_name} failed: {e}")
        return False

async def main():
    from app.agents.data_analyst import data_analyst_agent
    from app.agents.weather import weather_agent
    from app.agents.supply_commander import supply_commander_agent
    from app.agents.reporter import reporter_agent
    
    agents = [
        ("Data Analyst", data_analyst_agent),
        ("Weather", weather_agent), 
        ("Supply Commander", supply_commander_agent),
        ("Reporter", reporter_agent)
    ]
    
    print("Testing what each agent returns:")
    print("=" * 50)
    
    all_good = True
    for agent_name, agent_func in agents:
        if not test_agent_returns(agent_func, agent_name):
            all_good = False
    
    if all_good:
        print("\n🎉 All agents return correct type (dict)")
    else:
        print("\n💥 Some agents return wrong type!")

if __name__ == "__main__":
    asyncio.run(main())