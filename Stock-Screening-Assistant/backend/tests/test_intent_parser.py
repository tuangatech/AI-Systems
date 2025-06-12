# test_intent_parser.py
from backend.agents.intent_parser import IntentParserAgent


def test_intent_parser_agent():
    agent = IntentParserAgent()

    test_cases = [
        {
            "query": "Show me 3 undervalued tech stocks under $150 with dividends",
            "expected": {
                "clarification_needed": False,
                "sector": "technology"
            }
        },
        {
            "query": "Top 5 high dividend REITs",
            "expected": {
                "clarification_needed": False,
                "sector": "real_estate"
            }
        },
        {
            "query": "Give me safe stocks under $50",
            "expected": {
                "clarification_needed": True,
                "error": "Missing sector in query. Please specify a valid sector."
            }
        },
        {
            "query": "Top healthcare stocks with revenue growth > 10",
            "expected": {
                "clarification_needed": False,
                "sector": "healthcare",
                "filters": {"revenueGrowth_gt": 10}
            }
        },
        {
            "query": "Find stocks in luxury sector under $200",
            "expected": {
                "clarification_needed": True,
                "error_contains": "'luxury' is not a valid sector."
            }
        },
    ]

    for case in test_cases:
        print(f"\nTesting Query: {case['query']}")
        result = agent.invoke({"query": case["query"]})
        print("Parsed Result:", result)

        assert result["clarification_needed"] == case["expected"]["clarification_needed"]

        if case["expected"]["clarification_needed"]:
            if "error" in case["expected"]:
                assert result["error"] == case["expected"]["error"]
            elif "error_contains" in case["expected"]:
                assert case["expected"]["error_contains"] in result["error"]
        else:
            assert result["intent"]["sector"] == case["expected"]["sector"]
            if "filters" in case["expected"]:
                assert result["intent"]["filters"] == case["expected"]["filters"]