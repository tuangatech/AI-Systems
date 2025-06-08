# backend/agents/data_processor.py

import yfinance as yf
from typing import List, Dict, Any

def fetch_all_stocks(sector: str = None) -> List[Dict[str, Any]]:
    """
    Simulates fetching all stocks or filters by sector (stubbed).
    In real version, connect to an API like Yahoo Finance or Polygon.io.
    """
    # Mocked tickers
    tech_stocks = ["AAPL", "MSFT", "GOOGL", "META", "NVDA"]
    healthcare_stocks = ["PFE", "MRK", "JNJ", "AMGN", "GILD"]

    if sector == "technology":
        return [{"ticker": t} for t in tech_stocks]
    elif sector == "healthcare":
        return [{"ticker": t} for t in healthcare_stocks]
    else:
        return [{"ticker": t} for t in tech_stocks + healthcare_stocks]


def apply_filters(data: List[Dict], filters: Dict) -> List[Dict]:
    """Apply price, dividend, and metric filters"""
    filtered = []
    for stock in data:
        ticker = stock["ticker"]
        try:
            info = yf.Ticker(ticker).info
            price = info.get("currentPrice", float('inf'))
            dividend_yield = info.get("dividendYield", 0)

            meets_price = True
            if "price_under" in filters and price > filters["price_under"]:
                continue

            meets_dividend = True
            if "dividendYield_gt" in filters and dividend_yield < filters["dividendYield_gt"]:
                continue

            meets_custom = True
            if "peRatio_lt" in filters:
                pe_ratio = info.get("trailingPE")
                if pe_ratio and pe_ratio > filters["peRatio_lt"]:
                    continue

            filtered.append({
                "ticker": ticker,
                "price": price,
                "dividendYield": dividend_yield,
                "peRatio": info.get("trailingPE"),
                "sector": info.get("sector"),
                "name": info.get("longName")
            })
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            continue

    return filtered


def score_and_rank(data: List[Dict], metrics: List[str]) -> List[Dict]:
    """
    Simple ranking based on number of metrics met.
    Could be extended with weighted scoring later.
    """
    ranked = []
    for stock in data:
        score = 0
        for metric in metrics:
            if stock.get(metric):
                score += 1
        ranked.append({**stock, "score": score})

    return sorted(ranked, key=lambda x: x["score"], reverse=True)


def process_data(filters: Dict, sector: str = None, limit: int = 5) -> List[Dict]:
    raw_data = fetch_all_stocks(sector)
    filtered_data = apply_filters(raw_data, filters)
    ranked_data = score_and_rank(filtered_data, filters.get("metrics", []))
    return ranked_data[:limit]