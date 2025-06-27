# backend/models/schemas.py
from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class QueryInputSchema(BaseModel):
    query: str
    context_intent: Optional[Dict] = None

# Schema for the intent parsed from user input
class IntentSchema(BaseModel):
    sector: Optional[str] = None
    limit: Optional[int] = None
    metrics: List[str]
    filters: Optional[Dict[str, float]] = {}

# Schema for the stock screening results
class StockSchema(BaseModel):
    success: bool
    intent: Dict[str, Any]
    total_found: int
    after_filters: int
    results: List[Dict[str, Any]]
    error: Optional[str] = None