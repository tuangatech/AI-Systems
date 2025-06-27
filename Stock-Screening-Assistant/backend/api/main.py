from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.agents.schemas import QueryInputSchema
from backend.chains.inter_agent_chain import inter_agent_chain
import logging

# http://localhost:8000/docs — Swagger UI
app = FastAPI(
    title="Stock Screening Assistant",
    description="API for screening stocks based on financial metrics and filters.",
    version="1.0.0",
)

logger = logging.getLogger(__name__)

@app.post("/query")
async def handle_query(input: QueryInputSchema):
    user_input = input.query.strip()
    context_intent = input.context_intent or {}

    if not user_input:
        raise HTTPException(status_code=400, detail="Query input is required")

    try:
        result = inter_agent_chain.invoke({
            "query": user_input,
            "context_intent": context_intent
        })

        if result.get("short_circuit"):  # Defined by clarification_router
            return {
                "success": False,
                "clarification_needed": True,
                "error": result.get("error", "Clarification required."),
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