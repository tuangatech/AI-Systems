from backend.agents.data_processor import DataProcessorAgent
import time

agent = DataProcessorAgent(max_workers=5, rate_limit_delay=0.05)

def test_data_processor_agent():

    test_cases = [
        {
            "intent": {
                "intent": "screen",
                "sector": "technology",
                "limit": 5,
                "metrics": ["price", "peRatio"],
                "filters": {"peRatio_lt": 20, "dividendYield_gt": 2}
            },
            "expected_success": True,
            "expected_results_length": 6  # extra record for sector medians
        },
        {
            "intent": {
                "intent": "screen",
                "sector": "technology", # healthcare
                "limit": None,
                "metrics": ["revenueGrowth", "price"],
                "filters": {"peRatio_lt": 20}  # "revenuegrowth_gt": 0
            },
            "expected_success": True,
            "expected_results_length": 6  # extra record for sector medians
        },
        {
            "intent": {
                "intent": "screen",
                "sector": "real_estate",
                "limit": 3,
                "metrics": ["price", "dividendYield", "debtToEquity"],
                "filters": {"dividendYield_gt": 0}
            },
            "expected_success": True,
            "expected_results_length": 4  # extra record for sector medians
        }
    ]

    for case in test_cases:
        start_time = time.time()

        print(f"\n- Testing Intent: {case['intent']}")
        result = agent.invoke(case["intent"])
        print("- Screening Result:", result)

        elapsed_time = time.time() - start_time
        print(f"- Elapsed Time: {elapsed_time:.2f} seconds")

        assert result["success"] == case["expected_success"]
        assert len(result["results"]) == case["expected_results_length"]