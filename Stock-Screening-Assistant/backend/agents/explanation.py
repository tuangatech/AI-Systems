from .base import BaseAgent
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

class ExplanationAgent(BaseAgent):
    def __init__(self):
        self.generator = ExplanationGenerator()

    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            explanation = self.generator.explain(input)
            return {'success': True, 'explanation': explanation}
        except Exception as e:
            logger.error(f"Explanation error: {e}")
            return {'success': False, 'error': str(e)}


class ExplanationGenerator:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.5)
        self.template = PromptTemplate(
            input_variables=["input", "stocks", "sector_context"],
            template=(
                """
                You are a financial assistant.
                The user asked: {input}

                The sector-level context is:
                {sector_context}

                The following stocks were selected:
                {stocks}

                Explain clearly and concisely why each stock fits the criteria.
                """
            )
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.template)

    def explain(self, input: Dict[str, Any]) -> str:
        try:
            query = input["input"]
            results = input.get("results", [])
            if not results or len(results) < 2:
                return "No results to explain."

            sector_context_data = results[-1]
            selected_stocks = results[:-1]

            # Format sector context
            sector_context_str = "\n".join(
                f"Median {k}: {round(v, 2) if isinstance(v, float) else v}" for k, v in sector_context_data.items() if k not in ["symbol", "name", "sector"]
            )

            # Format stock descriptions
            stocks_desc = "\n".join(
                f"{s['symbol']} ({s['name']}): " + ", ".join(
                    f"{k}={round(v, 2) if isinstance(v, float) else v}" for k, v in s.items() if k not in ["symbol", "name", "sector"]
                ) for s in selected_stocks
            )

            explanation = self.chain.run(
                input=query,
                stocks=stocks_desc,
                sector_context=sector_context_str
            )
            return explanation

        except Exception as e:
            logger.error(f"LLM explanation error: {e}")
            return "Error generating explanation."