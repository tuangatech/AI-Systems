"""
Stock Data Processor Agent

Processes stock screening requests based on JSON intents from the Intent Parser agent.
"""

import logging
import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

import numpy as np
import pandas as pd
import yfinance as yf
import statistics
from joblib import Memory  # For caching

from .base import BaseAgent

warnings.filterwarnings('ignore')

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ==== Data Models ====

@dataclass
class StockIntent:
    intent: str
    sector: str
    metrics: List[str]
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: Optional[int] = None

    @classmethod
    def from_json(cls, json_data: Dict[str, Any]) -> 'StockIntent':
        return cls(
            intent=json_data.get("intent", ""),
            sector=json_data.get("sector", ""),
            metrics=json_data.get("metrics", []),
            filters=json_data.get("filters", {}),
            limit=json_data.get("limit")
        )


@dataclass
class StockData:
    symbol: str
    name: str
    sector: str
    price: Optional[float] = None
    peRatio: Optional[float] = None
    pbRatio: Optional[float] = None
    debtToEquity: Optional[float] = None
    revenueGrowth: Optional[float] = None
    dividendYield: Optional[float] = None
    freeCashFlowYield: Optional[float] = None
    marketCap: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'sector': self.sector,
            'price': self.price,
            'peRatio': self.peRatio,
            'pbRatio': self.pbRatio,
            'debtToEquity': self.debtToEquity,
            'revenueGrowth': self.revenueGrowth,
            'dividendYield': self.dividendYield,
            'freeCashFlowYield': self.freeCashFlowYield,
            'marketCap': self.marketCap
        }

# ==== Metric Computation ====

# class MetricCalculator:
#     @staticmethod
def safe_get(info: Dict, key: str, scale: float = 1.0) -> Optional[float]:
    try:
        val = info.get(key)
        return float(val) * scale if val and val > 0 else None
    except Exception:
        return None

# @staticmethod
def pe(info): return safe_get(info, 'trailingPE') or safe_get(info, 'forwardPE')
# @staticmethod
def pb(info): return safe_get(info, 'priceToBook')
# @staticmethod
def de(info): return safe_get(info, 'debtToEquity')
# @staticmethod
def rg(info): return safe_get(info, 'revenueGrowth') # scale = 100.0
# @staticmethod
def dy(info): return safe_get(info, 'dividendYield') # scale = 100.0
# @staticmethod
def fcfy(info):  # Free Cash Flow Yield = Free Cash Flow / Market Cap
    try:
        mcap = info.get('marketCap')
        fcf = info.get('freeCashflow')
        return (float(fcf) / float(mcap)) if mcap and fcf and mcap > 0 else None #  * 100
    except Exception:
        return None

# ==== Data Fetching ====

class StockDataFetcher:
    def __init__(self, max_workers: int = 10, delay: float = 0.1):
        self.max_workers = max_workers
        self.delay = delay

    def fetch_single(self, symbol: str, name: str, sector: str) -> Optional[StockData]:
        try:
            time.sleep(self.delay)
            ticker = yf.Ticker(symbol)
            info = ticker.info
            # logger.info(f"1. Fetched data for {symbol}: {info}")
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            # logger.info(f"Price for {symbol}: {price}")
            # logger.info(f"2. PE {pe(info)}")
            if not isinstance(info, dict) or 'symbol' not in info:  #if not info or 'symbol' not in info:
                # logger.info(f"2. No data found for {symbol}, skipping")
                return None
            return StockData(
                symbol=symbol,
                name=name,
                sector=sector,
                price=float(price) if price else None,
                peRatio=pe(info),
                pbRatio=pb(info),
                debtToEquity=de(info),
                revenueGrowth=rg(info),
                dividendYield=dy(info),
                freeCashFlowYield=fcfy(info),
                marketCap=info.get('marketCap')
            )
        except Exception as e:
            logger.error(f"Fetch failed for {symbol}: {e}")
            return None

    def fetch_multiple(self, stock_list: List[Tuple[str, str, str]]) -> List[StockData]:
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.fetch_single, *stock): stock[0] for stock in stock_list}
            for future in as_completed(futures):
                stock = future.result()
                if stock:
                    results.append(stock)
        return results

# ==== Filter Processing ====

class FilterProcessor:
    # metric_keys = ["peRatio", "pbRatio", "freeCashFlowYield", "price", "dividendYield", "debtToEquity", "revenueGrowth", "marketCap"]

    @classmethod
    def apply_filters(cls, stocks: List[StockData], filters: Dict[str, Any]) -> List[StockData]:
        logger.info(f"Applying filters: {filters} to {len(stocks)} stocks")
        def passes(stock: StockData) -> bool:
            # logger.info(f"Checking stock: {stock}")
            for key, value in filters.items():
                base_key, op = key.rsplit('_', 1)  # peRatio_lt -> base_key='peRatio', op='lt'
                # attr = cls.attr_map.get(base_key)
                stock_val = getattr(stock, base_key, None)
                # logger.info(f"Checking filter: {key} with value {value} for stock {stock.symbol} with value {stock_val}")
                if stock_val is None:
                    return False
                if op == 'lt' and stock_val >= value: return False
                if op == 'gt' and stock_val <= value: return False
                if op == 'eq' and stock_val != value: return False
            return True

        return [s for s in stocks if passes(s)]

# ==== S&P 500 Data Source ====

# Setup shared memory cache
CACHE_DIR = ".sp500_cache"
memory = Memory(location=CACHE_DIR, verbose=0)
os.makedirs(CACHE_DIR, exist_ok=True)

# Define cached function outside of class
@memory.cache
def _load_sp500_table() -> pd.DataFrame:
    logger.info("Fetching fresh data from Wikipedia...")
    return pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0] 

class SP500DataSource:
    def __init__(self, ttl_hours=24):
        self.ttl_hours = ttl_hours
    
    def load_table_with_refresh(self) -> pd.DataFrame:
        """Load table, respecting TTL by clearing cache if expired."""
        func = _load_sp500_table

        # Get the folder where joblib stores this function's cache
        cache_dir = os.path.join(memory.location, func.__module__, func.__qualname__)
        
        if os.path.exists(cache_dir):
            try:
                latest_mtime = max(
                    (os.path.getmtime(os.path.join(root, f)) for root, _, files in os.walk(cache_dir) for f in files),
                    default=0
                )
                age_seconds = time.time() - latest_mtime

                if age_seconds > self.ttl_hours * 3600:
                    logger.info(f"> Cache older than {self.ttl_hours}h. Clearing cache.")
                    logger.info(f"> Current cache location: {memory.location}")
                    func.cache_clear()
                else:
                    logger.info(f"> Cache is fresh (age: {age_seconds / 3600:.2f}h). Using cached data.")
            except Exception as e:
                logger.error(f"Error checking cache age: {e}. Using fresh data.")
                func.cache_clear()
        else:
            logger.info("No cache found. Fetching fresh data.")

        return _load_sp500_table()

    def get_by_sector(self, sector: str) -> List[Tuple[str, str, str]]:
        df = self.load_table_with_refresh()
        filtered = df[df["GICS Sector"] == sector]            # Global Industry Classification Standard (GICS)
        return [(row["Symbol"], row["Security"], sector) for _, row in filtered.iterrows()]

# ==== Main Agent ====

class DataProcessorAgent(BaseAgent):
    def __init__(self, max_workers: int = 10, rate_limit_delay: float = 0.1):
        self.data_source = SP500DataSource()
        self.fetcher = StockDataFetcher(max_workers, rate_limit_delay)
        self.filterer = FilterProcessor()
        self._sector_cache = defaultdict(dict)  # Cache for sector stocks and medians
    
    # input {"intent": intent, "query": user query}, passed from inter_agent_chain
    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"DataProcessorAgent invoke: Checking input: {input}")
            intent = StockIntent.from_json(input.get("intent")) 
            query = input.get("query", "")
            sector = intent.sector

            # if intent.intent != "screen":
            #     raise ValueError(f"Unsupported intent: {intent.intent}")

            # Use cached stocks if available. All stocks of a sector are fetched only once.
            # Check if sector exists and has "stocks"
            # @TODO: Use Redis for caching beyond instance lifetime
            if sector in self._sector_cache and "stocks" in self._sector_cache[sector]:
                stocks = self._sector_cache[sector]["stocks"]
                logger.info(f"Using cached stocks for sector: {sector} with {len(stocks)} entries")
            else:
                stock_list = self.data_source.get_by_sector(sector)
                stocks = self.fetcher.fetch_multiple(stock_list) # calculate metrics (pe_ratio, revenue_growth, etc.) in parallel
                self._sector_cache[sector]["stocks"] = stocks
                
                # normalized_sector = sector.lower().replace(" ", "_")
                # import os
                # import json
                # filepath = os.path.join(f"{normalized_sector}.json")
                # with open(filepath, "w") as f:
                #     json.dump([stock.to_dict() for stock in stocks], f, indent=2)
            if not stocks:
                return {'success': False, 'error': 'No data fetched', 'results': [], 'intent': intent, 'input': query}
            
            filtered = self.filterer.apply_filters(stocks, intent.filters)
            # Get the first filter key from intent.filters
            first_filter_key = next(iter(intent.filters))

            if first_filter_key:
                # Remove suffix to get the actual metric name (e.g., "peRatio" from "peRatio_lt")
                metric_name = first_filter_key.rsplit("_", 1)[0]

                # Sort using the extracted metric; handle missing attributes gracefully
                filtered.sort(key=lambda s: getattr(s, metric_name, 0) or 0, reverse=False)  # Ascending by default
            else:
                # Fallback: default sorting by marketCap if no valid filter found
                filtered.sort(key=lambda s: s.marketCap or 0, reverse=True)

            if intent.limit:
                filtered = filtered[:intent.limit]
            else:
                filtered = filtered[:5] # Default to top 5 if no limit specified

            logger.info(f"Found {len(stocks)} stocks, after filtering {len(filtered)} stocks")

            # Prepare output combining metrics and filters
            metric_keys = set(intent.metrics + [k.split("_")[0] for k in intent.filters.keys()])
            output = []

            # Add filtered stocks with metrics to output
            for stock in filtered:
                stock_dict = stock.to_dict()
                entry = {k: stock_dict[k] for k in ["symbol", "name", "sector"]}
                for metric in metric_keys:
                    if metric in stock_dict:
                        entry[metric] = stock_dict[metric]
                output.append(entry)

            if sector in self._sector_cache and "medians" in self._sector_cache[sector]:
                # Use cached sector medians if available
                sector_medians = self._sector_cache[sector]["medians"]
                logger.info(f"Using cached sector medians for sector: {sector}")
            else:
                # Calculate sector medians and append. All stocks of a sector
                all_dicts = [s.to_dict() for s in stocks]
                metric_keys_full = ["peRatio", "pbRatio", "freeCashFlowYield", "price", "dividendYield", "debtToEquity", "revenueGrowth", "marketCap"]
                medians = {}
                for key in metric_keys_full:
                    values = [d.get(key) for d in all_dicts if isinstance(d.get(key), (int, float))]
                    if values:
                        medians[key] = round(statistics.median(values), 2)

                sector_medians = {"symbol": "Sector", "name": "Median", "sector": intent.sector}
                # Add metric values from medians based on metric_keys
                for key in metric_keys:
                    sector_medians[key] = medians.get(key)

                self._sector_cache[intent.sector] = {"medians": sector_medians}
            
            output.append(sector_medians)
            results = {
                "success": True,
                "intent": intent,
                "total_found": len(stocks),
                "after_filters": len(filtered),
                "results": output,
                "query": query, # pass to ExplanationAgent to explain
            }
            logger.info(f">> DataProcessorAgent output:\n{results}")

            return results

        except Exception as e:
            logger.exception(f"Error processing intent: {e}")
            return {"success": False, "error": str(e), "results": []}

# Example usage and testing
if __name__ == "__main__":
    # fetch = StockDataFetcher()
    # data = fetch.fetch_single("AAPL", "Apple", "Technology")
    # logger.info(f"Fetched data for AAPL: {data.to_dict() if data else 'No data'}")
    # Initialize the agent
    agent = DataProcessorAgent()
    
    # Test cases
    test_intents = [
        {
            "intent": "screen",
            "sector": "technology",
            "limit": 3,
            "metrics": ["peRatio", "pbRatio", "freeCashFlowYield", "debtToEquity", "price"],
            "filters": {
                # "price_under": 50,
                # "dividendYield_gt": 0
                "price_lt": 400,
                "peRatio_lt": 40,
                # "debtToEquity_lt": 5,
            }
        },
        # {
        #     "intent": "screen",
        #     "sector": "technology",
        #     "limit": 5,
        #     "metrics": ["peRatio", "pbRatio", "freeCashFlowYield"]
        # },
        # {
        #     "intent": "screen",
        #     "sector": "energy",
        #     "metrics": ["dividendYield"],
        #     "limit": 5,
        #     "filters": {
        #         "dividendYield_gt": 4
        #     }
        # }
    ]
    
    # Process each intent
    for i, intent in enumerate(test_intents, 1):
        print(f"\n{'='*50}")
        print(f"Test Case {i}")
        print(f"{'='*50}")
        
        result = agent.invoke(intent)
        
        if result['success']:
            print(f"Success! Found {result['after_filters']} stocks matching criteria:")
            print(f"Intent: {result['intent']}")
            # print(f"Result: {result['results']}")
            for stock in result['results']:
                print(f"  {stock['symbol']}: {stock['name']}")
                for metric in intent['metrics']:
                    if metric in stock:
                        print(f"    {metric}: {stock[metric]}")
        else:
            print(f"Error: {result['error']}")