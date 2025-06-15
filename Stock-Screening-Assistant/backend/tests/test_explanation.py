from backend.agents.explanation import ExplanationAgent
import time

agent = ExplanationAgent()

def test_explanation_agent():

    test_cases = [
        {
            'success': True,
            "intent": {
                'intent': 'screen', 'sector': 'technology', 'limit': 3, 
                'metrics': ['peRatio', 'pbRatio', 'dividendYield'], 
                'filters': {'price_lt': 250.0, 'dividendYield_gt': 0.0, 'peRatio_lt': 30.0, 'pbRatio_lt': 15.0, 'freeCashFlowYield_gt': 5.0}, 
            },
            'total_found': 69, 'after_filters': 3, 
            'input': 'Show me 3 undervalued tech stocks under $250 with dividends',
            'results': [
                {'symbol': 'CTSH', 'name': 'Cognizant', 'sector': 'Information Technology', 'peRatio': 16.621052, 'dividendYield': 154.0, 'freeCashFlowYield': 5.104351825608181, 'pbRatio': 2.6124218, 'price': 78.95}, 
                {'symbol': 'WDC', 'name': 'Western Digital', 'sector': 'Information Technology', 'peRatio': 19.075342, 'dividendYield': 72.0, 'freeCashFlowYield': 7.237229657750918, 'pbRatio': 3.7548876, 'price': 55.7}, 
                {'symbol': 'GEN', 'name': 'Gen Digital', 'sector': 'Information Technology', 'peRatio': 28.912622, 'dividendYield': 165.0, 'freeCashFlowYield': 7.10594426626676, 'pbRatio': 8.098994, 'price': 29.78}, 
                {'symbol': 'Sector', 'name': 'Median', 'sector': 'Information Technology', 'peRatio': 34.07, 'dividendYield': 143.0, 'freeCashFlowYield': 2.89, 'pbRatio': 6.9, 'price': 170.75}
            ]
        },
    ]

    for case in test_cases:
        start_time = time.time()

        print(f"\n- Testing query: {case['input']}")
        explanation = agent.invoke(case)
        print("Explanation:", explanation)

        # assert result["success"] == case["expected_success"]
        # assert len(result["results"]) == case["expected_results_length"]