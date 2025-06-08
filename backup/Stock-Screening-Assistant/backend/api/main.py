from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from agents.intent_parser import parse_intent
from agents.data_processor import process_data
from tasks.celery_tasks import run_research_task
from models.schemas import IntentSchema
import logging

logger = logging.getLogger(__name__)
app = FastAPI()

# CORS middleware (for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/parse")
async def parse_user_query(query: dict):
    user_input = query.get("query")

    if not user_input:
        raise HTTPException(status_code=400, detail="Query input is required")

    try:
        raw_intent = parse_intent(user_input)
        validated_intent = IntentSchema(**raw_intent)
        return {"intent": validated_intent.dict()}
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal parsing error")

@app.post("/screen")
async def screen_stocks(query: dict):
    filters = query.get("filters")
    results = process_data(filters)
    return {"results": results}

@app.post("/research")
async def start_research(tickers: dict):
    tickers_list = tickers.get("tickers")
    task = run_research_task.delay(tickers_list)
    return {"task_id": task.id}