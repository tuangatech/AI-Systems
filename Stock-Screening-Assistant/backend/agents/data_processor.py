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
from typing import Any, Dict, List, Optional
from collections import defaultdict

import pandas as pd
import yfinance as yf
from joblib import Memory  # For caching
from dotenv import load_dotenv
import statistics
import datetime

from .base import BaseAgent

warnings.filterwarnings('ignore')

# Load .env
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)
CACHE_DIR = os.getenv("CACHE_DIR")

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

def safe_get(info: Dict, key: str, scale: float = 1.0) -> Optional[float]:
    try:
        val = info.get(key)
        return float(val) * scale if val and val > 0 else None
    except Exception:
        return None

def pe(info): return safe_get(info, 'trailingPE') or safe_get(info, 'forwardPE')
def pb(info): return safe_get(info, 'priceToBook')
def de(info): return safe_get(info, 'debtToEquity')
def rg(info): return safe_get(info, 'revenueGrowth') # scale = 100.0
def dy(info): return safe_get(info, 'dividendYield') # scale = 100.0
def fcfy(info):  # Free Cash Flow Yield = Free Cash Flow / Market Cap
    try:
        mcap = info.get('marketCap')
        fcf = info.get('freeCashflow')
        return (float(fcf) / float(mcap)) if mcap and fcf and mcap > 0 else None #  * 100
    except Exception:
        return None

# ==== Filter Processing ====

class FilterProcessor:
    # metric_keys = ["peRatio", "pbRatio", "freeCashFlowYield", "price", "dividendYield", "debtToEquity", "revenueGrowth", "marketCap"]

    @classmethod
    def apply_filters(cls, stocks: List[StockData], filters: Dict[str, Any]) -> List[StockData]:
        # logger.info(f"Applying filters: {filters} to {len(stocks)} stocks")
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
# Setup shared memory cache. The 'age_limit' is based on the last accessed time of a cached item, not its creation time
memory = Memory(location=CACHE_DIR, verbose=0)
os.makedirs(CACHE_DIR, exist_ok=True)

# Define cached function for all sectors data
@memory.cache
def _load_all_sectors_data(max_workers: int = 5, delay: float = 0.5) -> Dict[str, List[StockData]]:
    """Fetch and cache all S&P 500 stock data organized by sector."""
    logger.info("Fetching all S&P 500 data organized by sectors...")
    start_time = time.time()
    # Group stocks by sector
    sectors_data = defaultdict(list)
    all_stocks = []
    
    try:
        # Load S&P 500 table
        df = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")[0]
    except Exception as e:
        logger.error(f"Failed to load S&P 500 table: {e}")
        return {}
    
    # Prepare all stocks for batch fetching
    for _, row in df.iterrows():
        symbol = row["Symbol"]
        name = row["Security"] 
        sector = row["GICS Sector"]
        all_stocks.append((symbol, name, sector))
    
    logger.info(f"Fetching data for {len(all_stocks)} stocks across all sectors...")
    
    # Batch fetch all stocks using ThreadPoolExecutor
    def fetch_single(symbol: str, name: str, sector: str) -> Optional[StockData]:
        try:
            time.sleep(delay)
            ticker = yf.Ticker(symbol)
            info = ticker.info
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            if not isinstance(info, dict) or 'symbol' not in info:
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
    
    # Fetch all stocks in parallel
    try:
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_single, *stock): stock for stock in all_stocks}
            completed_count = 0
            total_count = len(futures)
            
            for future in as_completed(futures):
                stock_data = future.result()
                completed_count += 1
                
                if completed_count % 100 == 0 or completed_count == total_count:
                    logger.info(f"Progress: {completed_count}/{total_count} stocks fetched")
                
                if stock_data:
                    results.append(stock_data)
                    sectors_data[stock_data.sector].append(stock_data)
    except Exception as e:
        logger.error(f"Error fetching stock data: {e}")
        return {}
    
    load_time = time.time() - start_time
    logger.info(f"Successfully cached {len(results)} stocks across {len(sectors_data)} sectors in {load_time:.2f} seconds")
    return dict(sectors_data)

# ==== Main Agent ====

class DataProcessorAgent(BaseAgent):
    # Initialized from inter_agent_chain
    def __init__(self, max_workers: int = 4, rate_limit_delay: float = 0.7, ttl_hours: int = 6, max_retries: int = 3):
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        self.ttl_hours = ttl_hours
        self.max_retries = max_retries
        self.filterer = FilterProcessor()
        
        # Preload cache on initialization
        self._sectors_data = _load_all_sectors_data()
        self._data_loaded = True

    # input {"intent": intent, "query": user query}, passed from inter_agent_chain
    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        error = input.get("error")
        query = input.get("query", "")
        if error:
            return {"success": False, "error": error, "results": [], query: query}
        
        try:
            start_time = time.time()
            # @TODO: implement TTL check to reload (reduce_size()?) as joblib cache does not support TTL natively
            # if not self._sectors_data:  
            #     logger.warning("!! Data not loaded. Preloading sectors data...")
            self._sectors_data = _load_all_sectors_data()
            
            # logger.info(f"DataProcessorAgent invoke: Processing input: {input}")
            intent = StockIntent.from_json(input.get("intent")) 
            sector = intent.sector
            
            # Get stocks from pre-loaded cache
            if sector not in self._sectors_data:
                available_sectors = ", ".join(self._sectors_data.keys())
                return {
                    "success": False, 
                    "error": f"Sector '{sector}' not found. Available sectors: {available_sectors}",
                    "results": []
                }
            
            stocks = self._sectors_data[sector]
            # logger.info(f"Using cached stocks for sector: {sector} with {len(stocks)} entries")
            
            filtered = self.filterer.apply_filters(stocks, intent.filters)

            # Handle empty result case
            if not filtered:
                logger.warning(f"Found {len(stocks)} stocks. No matching stocks found.")
                return {
                    "success": False,
                    "intent": intent,
                    "query": query,
                    "total_found": len(stocks),
                    "after_filters": 0,
                    "results": [],
                    "error": "No matching stocks found.",
                }

            # Get the first filter key from intent.filters
            first_filter_key = next(iter(intent.filters))

            if first_filter_key:
                # Remove suffix to get the actual metric name (e.g., "peRatio" from "peRatio_lt")
                metric_name = first_filter_key.rsplit("_", 1)[0]

                # Sort using the extracted metric; consider missing attributes as 0
                filtered.sort(key=lambda s: getattr(s, metric_name, 0) or 0, reverse=False)  # Ascending by default
            else:
                # Fallback: default sorting by marketCap if no valid filter found
                filtered.sort(key=lambda s: s.marketCap or 0, reverse=True)

            if intent.limit:
                filtered = filtered[:intent.limit]
            else:
                filtered = filtered[:3] # Default to top 3 if no limit specified

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

            # Find sector medians and append. All stocks of a sector
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
            
            output.append(sector_medians)
            results = {
                "success": True,
                "intent": intent,
                "query": query, # pass to ExplanationAgent to explain
                "total_found": len(stocks),
                "after_filters": len(filtered),
                "results": output,
            }
            # logger.info(f">> DataProcessorAgent output:\n{results}")
            load_time = time.time() - start_time
            logger.info(f"DataProcessorAgent invoke() processed in {load_time:.2f} seconds")

            return results

        except Exception as e:
            logger.exception(f"Error processing intent: {e}")
            return {"success": False, "error": str(e), "query": query, "results": []}      
