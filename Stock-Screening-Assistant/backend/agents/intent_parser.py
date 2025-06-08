# from langchain_huggingface import HuggingFacePipeline
# from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
# from huggingface_hub import login
# import torch
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
import regex as re
import logging
from dotenv import load_dotenv
import os

# Go up one directory (to /backend) and load .env
# In Docker, your .env will be at /app/.env, which matches the relative path used above. 
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_NAME = "gpt-4o-mini-2024-07-18" # "meta-llama/Meta-Llama-3.1-8B-Instruct" "Qwen/Qwen3-Reranker-8B"
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be set.")

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

# print(f"GPU: {torch.cuda.get_device_name(torch.cuda.current_device())}" if torch.cuda.is_available() else "No GPU")

def extract_json(text):
    """
    Extracts the LAST VALID JSON object from a string.
    Handles nested braces properly.
    """
    # Take only the last N chars — usually where the real output is
    MAX_CHARS = 300
    text = text[-MAX_CHARS:]
    
    # Find all potential JSON starts
    candidates = []
    
    # Look for all opening braces and find their matching closing braces
    for start_idx in range(len(text)):
        if text[start_idx] == '{':
            brace_count = 0
            for end_idx in range(start_idx, len(text)):
                if text[end_idx] == '{':
                    brace_count += 1
                elif text[end_idx] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        candidate = text[start_idx:end_idx+1]
                        candidates.append((start_idx, end_idx, candidate))
                        break
    
    # Filter out nested objects - keep only outermost ones
    outermost_candidates = []
    for i, (start1, end1, candidate1) in enumerate(candidates):
        is_nested = False
        for j, (start2, end2, candidate2) in enumerate(candidates):
            if i != j and start2 < start1 and end1 < end2:
                # candidate1 is nested inside candidate2
                is_nested = True
                break
        if not is_nested:
            outermost_candidates.append(candidate1)
    
    # Try to parse from last to first
    for candidate in reversed(outermost_candidates):
        try:
            result = json.loads(candidate)
            # logger.info(f"Parsed JSON: {candidate}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Simple approach failed to parse: {e}")
            continue
    
    return None

class IntentParserAgent:
    def __init__(self, model_name=MODEL_NAME):
        self.model_name = model_name
        # https://huggingface.co/settings/tokens
        # self.hf_token = HF_TOKEN    
        self._load_model()

    def _load_model(self):
        """
        Load the OpenAI model.
        """
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=0.1,
            max_tokens=300,
            api_key=OPENAI_API_KEY
        )
        logger.info(f"Model {self.model_name} loaded successfully.")

    # def _load_model(self):
    #     login(token=self.hf_token)

    #     self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
    #     self.model = AutoModelForCausalLM.from_pretrained(
    #         self.model_name,
    #         torch_dtype=torch.float16,
    #         device_map="auto"
    #     )

    #     self.pipe = pipeline(
    #         "text-generation",
    #         model=self.model,
    #         tokenizer=self.tokenizer,
    #         max_new_tokens=300,
    #         temperature=0.2,
    #         pad_token_id=self.tokenizer.eos_token_id,
    #         eos_token_id=self.tokenizer.eos_token_id  # Stop at end-of-sequence
    #     )

    #     self.llm = HuggingFacePipeline(pipeline=self.pipe)
    #     logger.info(f"Model {self.model_name} loaded successfully.")

    def parse_intent(self, user_input: str) -> dict:

        prompt = f"""
            You are a financial assistant. Parse the following stock screening query into structured JSON format.

            Return a JSON object with the following keys:
            intent, sector (optional), limit (optional), metrics, filters (optional), rank_by (optional)

            Rules:
            - "undervalued": peRatio, pbRatio, freeCashFlowYield
            - "safe", "stable": debtToEquity, revenueGrowth
            - "high dividend": dividendYield
            - Price thresholds (e.g., under $50): price_under
            - "top N stocks": limit=N
            - Default intent is "screen"
            - If no specific metric mentioned, use default relevant ones

            Example output:
            {{"intent": "screen", "sector": "technology", "limit": 3, "metrics": ["peRatio", "pbRatio"], "filters": {{"price_under": 50, "dividendYield_gt": 0}}}}

            Return ONLY 1 raw JSON object without any explanations or markdown formatting.
            Now parse this query:
            {user_input}

            Output ONLY the JSON object below - NO TEXT BEFORE OR AFTER.
            """.strip()
        
        # response = self.llm.invoke(prompt)  # local LLM
        # logger.info(f"LLM Response: {response}")
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)]) # OpenAI API
            content = response.content.strip()
            logger.info(f"OpenAI Response Content: {content}")
            # return self.extract_json(content)
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}")
            return {"error": "Failed to get response from LLM"}
        
        parsed_json = extract_json(content)
        logger.info(f"Parsed JSON: {content}")
    
        if parsed_json:
            return parsed_json
        else:
            return {
                "error": "Failed to extract JSON",
                "raw_response": response
            }


# Mock mapping from user queries to structured intent JSON
queries = [
    "Show me 3 undervalued tech stocks under $50 with dividends",
    # "Show me undervalued tech stocks",
    "Find dividend-paying REITs under $40",
    # "Top 5 undervalued stocks in healthcare",
    # "Find me high-dividend energy stocks",
    "Find me 5 safe stocks with dividends"
]

QUERY_TO_INTENT = {
    "Show me 3 undervalued tech stocks under $50 with dividends": {
        "intent": "screen",
        "sector": "technology",
        "limit": 3,
        "metrics": ["peRatio", "pbRatio", "freeCashFlowYield"],
        "filters": {
            "price_under": 50,
            "dividendYield_gt": 0
        }
    },
    "Show me undervalued tech stocks": {
        "intent": "screen",
        "sector": "technology",
        "metrics": ["peRatio", "pbRatio", "freeCashFlowYield"]
    },
    "Find dividend-paying REITs under $40": {
        "intent": "screen",
        "sector": "realEstate",
        "metrics": ["dividendYield"],
        "filters": {
            "price_under": 40,
            "dividendYield_gt": 0
        }
    },
    "Top 5 undervalued stocks in healthcare": {
        "intent": "screen",
        "sector": "healthcare",
        "limit": 5,
        "metrics": ["peRatio", "pbRatio", "freeCashFlowYield"]
    },
    "Find me high-dividend energy stocks": {
        "intent": "screen",
        "sector": "energy",
        "metrics": ["dividendYield"],
        "filters": {
            "dividendYield_gt": 4  # High yield assumed > 4%
        }
    },
    "Find me 5 safe stocks with dividends": {
        "intent": "screen",
        "limit": 5,
        "metrics": ["debtToEquity", "revenueGrowth", "dividendYield"],
        "filters": {
            "dividendYield_gt": 0
        }
    }
}

# parsed_json = extract_json2(prompt2)
# print(f"\nParsed JSON: {parsed_json}")
# Scan through QUERY_TO_INTENT and call parse_intent for each query
intent_parser = IntentParserAgent() # "microsoft/Phi-3.5-mini-instruct" model_name="mistralai/Mistral-7B-Instruct-v0.3"
for query in queries:
    parsed_intent = intent_parser.parse_intent(query)
    logger.info(f"===\nQuery: {query}\nParsed Intent: {parsed_intent}\n")
