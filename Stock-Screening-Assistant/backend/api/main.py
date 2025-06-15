from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.agents.intent_parser import IntentParserAgent
from backend.agents.data_processor import DataProcessorAgent
# from tasks.celery_tasks import run_research_task
from backend.models.schemas import IntentSchema, StockSchema, QueryInputSchema
from backend.chains.inter_agent_chain import inter_agent_chain
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

@app.post("/query")
async def handle_query(query: QueryInputSchema):
    user_input = query.query.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Query input is required")

    try:
        result = inter_agent_chain.invoke({"query": user_input})
        if result.get("short_circuit"):
            return {
                "success": False,
                "clarification_needed": True,
                "message": result.get("error", "Clarification required."),
                "parsed_intent": result.get("parsed", {})
            }

        # logger.info(f"Result from inter-agent chain: \n{result}")
        return {
            "success": True,
            "explanation": result.get("explanation"),
            "results": result.get("results", []),
            "intent": result.get("intent", {}),
        }
    except Exception as e:
        logger.exception("Query handling failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy"}