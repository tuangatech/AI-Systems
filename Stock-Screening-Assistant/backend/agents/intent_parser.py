# backend/agents/intent_parser.py

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
# from langchain_core.runnables import Runnable
# from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

from .base import BaseAgent
from backend.models.schemas import IntentSchema

# Load .env
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

VALID_SECTORS = {
    'tech': 'Information Technology',
    'technology': 'Information Technology',
    'energy': 'Energy',
    'health_care': 'Health Care',
    'healthcare': 'Health Care',
    'financials': 'Financials',
    'discretionary': 'Consumer Discretionary',
    'consumer_discretionary': 'Consumer Discretionary',
    'staples': 'Consumer Staples',
    'consumer_staples': 'Consumer Staples',
    'industrials': 'Industrials',
    'materials': 'Materials',
    'utilities': 'Utilities',
    'reit': 'Real Estate',
    'real_estate': 'Real Estate',
    'communication': 'Communication Services',
    'communication_services': 'Communication Services'
}

class IntentParserAgent(BaseAgent):
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1,
            max_tokens=300,
            api_key=OPENAI_API_KEY
        )
        self.prompt_template = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a financial assistant. Parse stock screening query into structured JSON format.\n"
                "Return a JSON object with the following keys: intent, sector, limit (optional), metrics, filters (optional)\n"
                "Rules:\n"
                "- undervalued: peRatio < 25, pbRatio < 12, freeCashFlowYield > 0.05\n"
                "- safe, stable: debtToEquity < 30.0, revenueGrowth > 0.02\n"
                "- high dividend: dividendYield > 4\n"
                "- dividend paying: dividendYield > 0\n"
                "- growth: revenueGrowth > 0.10, freeCashFlowYield > 0.05\n"
                "- under $N: price_lt = N\n"
                "- top N stocks: limit = N\n"
                "- stock metrics used in 'filters' should be in 'metrics'\n"
                "- 'metrics' attribute always includes 'price' and 'peRatio'\n"
                "Example output:\n"
                '{{"sector": "technology", "limit": 3, "metrics": ["price", "peRatio", "pbRatio"], "filters": {{"price_lt": 50, "dividendYield_gt": 0, "freeCashFlowYield_gt": 5}}}}\n'
                '{{"sector": "REIT", "limit": 5, "metrics": ["price", "dividendYield"], "filters": {{"debtToEquity_lt": 1.0, "revenueGrowth_gt": 5}}}}\n'
                "Return ONLY 1 raw JSON object without any explanations or markdown formatting."
            ),
            MessagesPlaceholder(variable_name="messages")
        ])
        self.chain = self.prompt_template | self.llm

    # input: {"query": "Show me 3 undervalued tech stocks under $50 with dividends"}
    def invoke(self, input: str) -> Dict[str, Any]:
        query = input.get("query")

        message = HumanMessage(content=f"Parse this request:\n{query}\nRespond only with JSON, NO TEXT BEFORE OR AFTER.")
        try:
            result = self.chain.invoke({"messages": [message]})
            content = result.content.strip()

            logger.info(f"LLM Response Content: {content}")

            # Try parsing JSON safely
            parsed = IntentSchema.model_validate_json(content)
        except Exception as e:
            logger.warning(f"LLM failed to produce valid JSON: {e}")
            return {
                "clarification_needed": True,
                "error": "Could not parse your request. Please clarify your sector or filters.",
                "raw_response": result.content,
                "query": query
            }

        sector = parsed.sector
        if not sector:
            logger.warning("Missing sector in query.")
            return {
                "clarification_needed": True,
                "error": "Missing sector in query. Please specify a valid sector.",
                "parsed": parsed.model_dump(),
                "query": query
            }

        normalized_sector = sector.strip().lower().replace(" ", "_")
        # logger.info(f"Normalized sector: {normalized_sector}")
        if normalized_sector not in VALID_SECTORS:
            logger.warning(f"Invalid sector: {sector}")
            results = {
                "clarification_needed": True,
                "error": f"'{sector}' is not a valid sector. Please try one of: {', '.join(VALID_SECTORS.values())}",
                "parsed": parsed.model_dump(),
                "query": query
            }
            # logger.info(f">> IntentParserAgent results:\n {results}")
            return results 
        else:
            parsed.sector = VALID_SECTORS[normalized_sector]
            # logger.info(f"Valid sector: {parsed.sector}")

        results = {
            "clarification_needed": False,
            "intent": parsed.model_dump(),
            "query": query
        }
        logger.info(f">> IntentParserAgent results:\n {results}")
        return results
    
# 1. Query: Show me 3 undervalued tech stocks under $50 with dividends
# Parsed Intent: {'intent': 'screen', 'sector': 'technology', 'limit': 3, 'metrics': ['peRatio', 'pbRatio', 'dividendYield'], 
# 'filters': {'price_under': 50, 'dividendYield_gt': 0, 'peRatio_lt': 20, 'pbRatio_lt': 3, 'freeCashFlowYield_gt': 5}}
# 2. Query: Find me 5 safe stocks with dividends
# Parsed Intent: {'intent': 'screen', 'limit': 5, 'metrics': ['dividendYield'], 
# 'filters': {'debtToEquity_lt': 0.5, 'dividendYield_gt': 0, 'revenueGrowth_gt': 5}}