from langchain_core.runnables import RunnableMap, RunnableLambda
from agents.data_processor import DataProcessorAgent
from agents.explanation import ExplanationAgent

def route_clarification_logic(inputs: dict) -> bool:
    return inputs.get("clarification_needed", False)

clarification_router = RunnableLambda(lambda x: x if not route_clarification_logic(x) else {'short_circuit': True})

data_processor = RunnableLambda(lambda x: DataProcessorAgent().invoke(x))
explainer = RunnableLambda(lambda x: ExplanationAgent().invoke(x))

# This chain processes the intent, checks for clarification needs, and generates explanations if needed.
inter_agent_chain = (
    RunnableMap({
        "clarification_check": clarification_router,
        "processed": lambda x: data_processor.invoke(x) if not x.get("clarification_needed") else None,
    })
    | RunnableLambda(lambda x: x["processed"] if x["clarification_check"] != {'short_circuit': True} else x)
    | explainer
)