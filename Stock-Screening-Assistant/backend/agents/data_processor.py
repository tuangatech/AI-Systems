"""
Stock Data Processor Agent

Processes stock screening requests based on JSON intents from the Intent Parser agent.
"""

import logging
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
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    debtToEquity: Optional[float] = None
    revenue_growth: Optional[float] = None
    dividend_yield: Optional[float] = None
    free_cash_flow_yield: Optional[float] = None
    market_cap: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'sector': self.sector,
            'price': self.price,
            'peRatio': self.pe_ratio,
            'pbRatio': self.pb_ratio,
            'debtToEquity': self.debtToEquity,
            'revenueGrowth': self.revenue_growth,
            'dividendYield': self.dividend_yield,
            'freeCashFlowYield': self.free_cash_flow_yield,
            'marketCap': self.market_cap
        }

# ==== Metric Computation ====

class MetricCalculator:
    @staticmethod
    def safe_get(info: Dict, key: str, scale: float = 1.0) -> Optional[float]:
        try:
            val = info.get(key)
            return float(val) * scale if val and val > 0 else None
        except Exception:
            return None

    @staticmethod
    def pe(info): return MetricCalculator.safe_get(info, 'trailingPE') or MetricCalculator.safe_get(info, 'forwardPE')
    @staticmethod
    def pb(info): return MetricCalculator.safe_get(info, 'priceToBook')
    @staticmethod
    def de(info): return MetricCalculator.safe_get(info, 'debtToEquity')
    @staticmethod
    def rg(info): return MetricCalculator.safe_get(info, 'revenueGrowth', 100.0)
    @staticmethod
    def dy(info): return MetricCalculator.safe_get(info, 'dividendYield', 100.0)
    @staticmethod
    def fcfy(info):
        try:
            mcap = info.get('marketCap')
            fcf = info.get('freeCashflow')
            return (float(fcf) / float(mcap)) * 100 if mcap and fcf and mcap > 0 else None
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
            if not isinstance(info, dict) or 'symbol' not in info:  #if not info or 'symbol' not in info:
                return None
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            return StockData(
                symbol=symbol,
                name=name,
                sector=sector,
                price=float(price) if price else None,
                pe_ratio=MetricCalculator.pe(info),
                pb_ratio=MetricCalculator.pb(info),
                debtToEquity=MetricCalculator.de(info),
                revenue_growth=MetricCalculator.rg(info),
                dividend_yield=MetricCalculator.dy(info),
                free_cash_flow_yield=MetricCalculator.fcfy(info),
                market_cap=info.get('marketCap')
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
    # attr_map = {
    #     'price': 'price',
    #     'peRatio': 'peRatio',
    #     'pbRatio': 'pbRatio',
    #     'debtToEquity': 'debtToEquity',
    #     'revenueGrowth': 'revenueGrowth',
    #     'dividendYield': 'dividendYield',
    #     'freeCashFlowYield': 'freeCashFlowYield',
    #     'marketCap': 'market_cap'
    # }

    @classmethod
    def apply_filters(cls, stocks: List[StockData], filters: Dict[str, Any]) -> List[StockData]:
        def passes(stock: StockData) -> bool:
            for key, value in filters.items():
                base_key, op = key.rsplit('_', 1)  # peRatio_lt -> base_key='peRatio', op='lt'
                # attr = cls.attr_map.get(base_key)
                stock_val = getattr(stock, base_key, None)
                if stock_val is None:
                    return False
                if op == 'lt' and stock_val >= value: return False
                if op == 'gt' and stock_val <= value: return False
                if op == 'eq' and stock_val != value: return False
            return True

        return [s for s in stocks if passes(s)]

# ==== S&P 500 Data Source ====

class SP500DataSource:
    sector_map = {
        'technology': 'Information Technology',
        'energy': 'Energy',
        'healthcare': 'Health Care',
        'financials': 'Financials',
        'consumer_discretionary': 'Consumer Discretionary',
        'consumer_staples': 'Consumer Staples',
        'industrials': 'Industrials',
        'materials': 'Materials',
        'utilities': 'Utilities',
        'real_estate': 'Real Estate',
        'REIT': 'Real Estate',
        'communication_services': 'Communication Services'
    }

    def __init__(self):
        self._cache = None

    def _load(self) -> pd.DataFrame:
        if self._cache is None:
            url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
            self._cache = pd.read_html(url)[0]
        return self._cache

    def get_by_sector(self, sector: str) -> List[Tuple[str, str, str]]:
        df = self._load()
        gics = self.sector_map.get(sector.lower(), sector) 
        filtered = df[df["GICS Sector"] == gics]            # Global Industry Classification Standard (GICS)
        return [(row["Symbol"], row["Security"], gics) for _, row in filtered.iterrows()]

# ==== Main Agent ====

class DataProcessorAgent(BaseAgent):
    def __init__(self, max_workers: int = 10, rate_limit_delay: float = 0.1):
        self.data_source = SP500DataSource()
        self.fetcher = StockDataFetcher(max_workers, rate_limit_delay)
        self.filterer = FilterProcessor()
        self._sector_cache = defaultdict(dict)  # Automatically initializes inner dict
    
    def invoke(self, input: Dict[str, Any]) -> Dict[str, Any]:
        return self._process_intent(input)

    def _process_intent(self, intent_json: Dict[str, Any]) -> Dict[str, Any]:        
        try:
            intent = StockIntent.from_json(intent_json)
            sector = intent.sector

            if intent.intent != "screen":
                raise ValueError(f"Unsupported intent: {intent.intent}")

            # Use cached stocks if available. All stocks of a sector are fetched only once.
            # Check if sector exists and has "stocks"
            if sector in self._sector_cache and "stocks" in self._sector_cache[sector]:
                stocks = self._sector_cache[sector]["stocks"]
                logger.info(f"Using cached stocks for sector: {sector} with {len(stocks)} entries")
            else:
                stock_list = self.data_source.get_by_sector(sector)
                stocks = self.fetcher.fetch_multiple(stock_list) # calculate metrics (pe_ratio, revenue_growth, etc.) in parallel
                self._sector_cache[sector]["stocks"] = stocks
            if not stocks:
                return {'success': False, 'error': 'No data fetched', 'results': []}
            
            filtered = self.filterer.apply_filters(stocks, intent.filters)
            filtered.sort(key=lambda s: s.market_cap or 0, reverse=True)

            if intent.limit:
                filtered = filtered[:intent.limit]
            else:
                filtered = filtered[:5] # Default to top 5 if no limit specified

            logger.info(f"Found {len(stocks)} stocks, after filtering {len(filtered)} stocks for intent: {intent.intent}")

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

            return {
                "success": True,
                "intent": intent_json,
                "total_found": len(stocks),
                "after_filters": len(filtered),
                "results": output,
            }

        except Exception as e:
            logger.exception("Error processing intent")
            return {"success": False, "error": str(e), "results": []}
