from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.agents.intent_parser import IntentParserAgent
from backend.agents.data_processor import DataProcessorAgent
# from tasks.celery_tasks import run_research_task
from backend.models.schemas import IntentSchema, StockSchema
import logging

logger = logging.getLogger(__name__)
# http://localhost:8000/docs — Swagger UI
app = FastAPI(
    title="Stock Screening Assistant",
    description="API for screening stocks based on financial metrics and filters.",
    version="1.0.0"
)

# CORS middleware (for dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

intent_parser = IntentParserAgent()
data_processor = DataProcessorAgent()

@app.post("/parse")
async def parse_user_query(query: dict):
    user_input = query.get("query")

    if not user_input:
        raise HTTPException(status_code=400, detail="Query input is required")

    try:
        parse_intent = intent_parser.parse_intent(user_input)
        validated_intent = IntentSchema(**parse_intent)
        logger.info("> Parsing successful", extra={
            "intent": validated_intent.model_dump(),
            "query": user_input,  
            "endpoint": "/parse"
        })
        return validated_intent.model_dump()
    except Exception as e:
        logger.error("Parsing failed", extra={
            "error": str(e),
            "query": user_input,  
            "endpoint": "/parse"
        })
        raise HTTPException(status_code=500, detail="Internal parsing error")

@app.post("/screen", response_model=StockSchema)
async def screen_stocks(request: IntentSchema):
    try:
        # Convert request to dict and process
        result = data_processor.process_intent(request.model_dump())
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        logger.info("> Screening successful", extra={
            "total_found": result["total_found"],
            "after_filters": result["after_filters"],
            "endpoint": "/screen"
        })
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/research")
async def start_research(tickers: dict):
    tickers_list = tickers.get("tickers")
    task = run_research_task.delay(tickers_list)
    return {"task_id": task.id}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}