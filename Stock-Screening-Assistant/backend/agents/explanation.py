from .base import BaseAgent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import os
import time
import logging
from typing import Dict, Any

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

class ExplanationAgent(BaseAgent):
    def __init__(self):
        prompt = PromptTemplate(
            input_variables=["input", "stocks", "sector_context"],
            template="""
                You are a financial assistant.
                The user asked: {input}

                The sector-level context is: {sector_context}

                The following stocks were selected: {stocks}

                Explain clearly and concisely why each stock fits what user asked for.
            """
        )

        llm = ChatOpenAI(model=MODEL_NAME, temperature=0.3, api_key=OPENAI_API_KEY)
        self.chain =  prompt | llm

    # inputs: {"results": List[Dict], "intent": Dict, "query": str}
    def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:   
        try:     
            start_time = time.time()
            query = inputs["query"]
            results = inputs["results"]
            error = inputs.get("error")

            if error:
                logger.error(f"Error in inputs: {error}")
                return f"⚠️ {error}"
            # logger.info(f"Received inputs: {inputs}")
            # logger.info(f"\nExplanationAgent invoke: Checking input: {results}")
            # logger.info(f"Received 1st result: {results[0]}")
            if not results or len(results) < 2:
                logger.warning("Not enough data to generate explanation.")
                return "Not enough data to explain."

            sector_context_data = results[-1]
            selected_stocks = results[:-1]

            # Format sector context
            sector_context_str = "\n".join(
                f"Median {k}: {round(v, 2) if isinstance(v, float) else v}"
                for k, v in sector_context_data.items()
                if k not in ["symbol", "name", "sector"]
            )

            # Format stock descriptions
            stocks_desc = "\n".join(
                f"{s['symbol']} ({s['name']}): " + ", ".join(
                    f"{k}={round(v, 2) if isinstance(v, float) else v}"
                    for k, v in s.items()
                    if k not in ["symbol", "name", "sector"]
                ) for s in selected_stocks
            )

            logger.info(f"Generating explanation for query: {query}")
            logger.info(f"Stocks: {stocks_desc}")
            # logger.info(f"Sector context: {sector_context_str}\n")

            # Run LLM chain
            response = self.chain.invoke({
                "input": query,
                "stocks": stocks_desc,
                "sector_context": sector_context_str
            })

            load_time = time.time() - start_time
            logger.info(f"ExplanationAgent invoke() processed in {load_time:.2f} seconds")
            return response.content

        except Exception as e:
            logger.error(f"LLM explanation error: {e}", exc_info=True)
            return f"Failed to generate explanation: {str(e)}"
        

if __name__ == "__main__":
    agent = ExplanationAgent()
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
    
    results = agent.invoke(test_cases[0])
    print("Explanation:", results["explanation"])
