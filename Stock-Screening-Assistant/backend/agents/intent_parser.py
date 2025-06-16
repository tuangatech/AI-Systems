# backend/agents/intent_parser.py

import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

from .base import BaseAgent
from .schemas import IntentSchema

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
                # "- 'metrics' attribute always includes 'price' and 'peRatio'\n"
                "Example output:\n"
                '{{"sector": "technology", "limit": 3, "metrics": ["price", "peRatio", "pbRatio"], "filters": {{"price_lt": 50, "dividendYield_gt": 0, "freeCashFlowYield_gt": 5}}}}\n'
                '{{"sector": "REIT", "limit": 5, "metrics": ["price", "dividendYield"], "filters": {{"debtToEquity_lt": 1.0, "revenueGrowth_gt": 5}}}}\n'
                "Return ONLY 1 raw JSON object without any explanations or markdown formatting."
            ),
            MessagesPlaceholder(variable_name="messages")
        ])
        self.chain = self.prompt_template | self.llm

    # input: {"query": "Show me 3 undervalued tech stocks under $50 with dividends", "context_intent": {'sector': 'energy', ...}}
    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        query = input.get("query")
        context_intent = input.get("context_intent")  # Optional previous intent

        if not query:
            raise ValueError("Missing 'query' in input")
        
        message = HumanMessage(content=f"Parse this request:\n{query}\nRespond only with JSON, NO TEXT BEFORE OR AFTER.")
        try:
            result = self.chain.invoke({"messages": [message]})
            content = result.content.strip()

            logger.info(f"LLM Response Content: {content}")

            # Try parsing JSON safely
            parsed = IntentSchema.model_validate_json(content)
            logger.info(f"Parsed intent: {parsed.model_dump()}")

            # If parsed intent is vague (e.g., missing key info), merge with context
            final_intent = self._update_intent(context_intent, parsed.model_dump())
            logger.info(f"Final intent: {final_intent}")
                
        except Exception as e:
            logger.warning(f"LLM failed to produce valid JSON: {e}")
            return {
                "clarification_needed": True,
                "error": "Could not parse your request. Please clarify your sector or filters.",
                "raw_response": result.content,
                "query": query
            }

        sector = final_intent.get('sector', '')
        if not sector:
            logger.warning("Missing sector in query.")
            return {
                "clarification_needed": True,
                "error": "Missing sector in query. Please specify a valid sector.",
                "parsed": final_intent,
                "query": query
            }

        normalized_sector = sector.strip().lower().replace(" ", "_")
        logger.info(f"Normalized sector: {normalized_sector}")
        if normalized_sector not in VALID_SECTORS:
            logger.warning(f"Invalid sector: {sector}")
            results = {
                "clarification_needed": True,
                "error": f"'{sector}' is not a valid sector. Please try one of: {', '.join(VALID_SECTORS.values())}",
                "parsed": final_intent,
                "query": query
            }
            # logger.info(f">> IntentParserAgent results:\n {results}")
            return results 
        else:
            final_intent["sector"] = VALID_SECTORS[normalized_sector]
            # logger.info(f"Valid sector: {final_intent.sector}")

        results = {
            "clarification_needed": False,
            "intent": final_intent,
            "query": query
        }
        logger.info(f">> IntentParserAgent results:\n {results}")
        return results
    
    def _update_intent(self, context: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        final_intent = current.copy()
        
        # Handle metrics: add 'price' or 'peRatio' if not present
        current_metrics = current.get('metrics', [])
        if 'price' not in final_intent['metrics']:
            final_intent['metrics'] = final_intent['metrics'] + ['price']
        if 'peRatio' not in final_intent['metrics']:
            final_intent['metrics'] = final_intent['metrics'] + ['peRatio']
        
        if context: 
            # No filters means user asked a follow up question like "How about energy stocks?"
            if not final_intent.get('filters') and context.get('filters'):
                final_intent['filters'] = context['filters']
                if not final_intent.get('limit') and context.get('limit'):
                    final_intent['limit'] = context['limit']
                # Merge metrics from context and current, then deduplicate
                context_metrics = context.get('metrics', [])
                current_metrics = final_intent.get('metrics', [])
                merged_metrics = list(set(context_metrics + current_metrics))
                final_intent['metrics'] = merged_metrics
        
        return final_intent
    
# 1. Query: Show me 3 undervalued tech stocks under $50 with dividends
# Parsed Intent: {'intent': 'screen', 'sector': 'technology', 'limit': 3, 'metrics': ['peRatio', 'pbRatio', 'dividendYield'], 
# 'filters': {'price_under': 50, 'dividendYield_gt': 0, 'peRatio_lt': 20, 'pbRatio_lt': 3, 'freeCashFlowYield_gt': 5}}
# 2. Query: Find me 5 safe stocks with dividends
# Parsed Intent: {'intent': 'screen', 'limit': 5, 'metrics': ['dividendYield'], 
# 'filters': {'debtToEquity_lt': 0.5, 'dividendYield_gt': 0, 'revenueGrowth_gt': 5}}

# agent = IntentParserAgent()

# input_data = {
#     "query": 'How about energy?',
#     "context_intent": "{{'sector': 'Health Care', 'limit': 3, 'metrics': ['price', 'dividendYield', 'peRatio'], 'filters': {{'price_lt': 150.0, 'dividendYield_gt': 0.0}}}}"
# }

# agent.invoke(input_data)