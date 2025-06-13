from langchain_core.runnables import RunnableMap, RunnableLambda
from agents.intent_parser import IntentParserAgent
from agents.data_processor import DataProcessorAgent
from agents.explanation import ExplanationAgent

# Instantiate agents once to maintain cache across requests
intent_parser = IntentParserAgent()
data_processor = DataProcessorAgent()
explanation_agent = ExplanationAgent()

def route_clarification_logic(inputs: dict) -> bool:
    return inputs.get("clarification_needed", False)

clarification_router = RunnableLambda(
    lambda x: x if not route_clarification_logic(x) else {"short_circuit": True, **x}
)

# Wrap agents using LangChain runnables
parser_chain = RunnableLambda(lambda x: intent_parser.invoke(x["input"]))
data_processor_chain = RunnableLambda(lambda x: data_processor.invoke(x["intent"]))
explainer_chain = RunnableLambda(lambda x: explanation_agent.invoke({**x["results"], "input": x["input"]}))

# LangChain inter-agent chain
inter_agent_chain = (
    RunnableMap({
        "parsed": parser_chain,
    })
    | RunnableLambda(
        lambda x: {     # If clarification_needed is True: return early with "short_circuit", "error", and "parsed"
            "short_circuit": True,
            "error": x["parsed"].get("error", "Clarification required."),
            "parsed": x["parsed"].get("parsed", {})
        } if x["parsed"].get("clarification_needed") else {
            "intent": x["parsed"]["intent"],
            "input": x["input"]
        }
    )
    | RunnableLambda(
        lambda x: x if x.get("short_circuit") else {  
            **x,
            "results": data_processor_chain.invoke(x)  # If not short-circuiting, continue with data processing
        }
    )
    | RunnableLambda(
        lambda x: {
            **x,
            "explanation": explainer_chain.invoke(x)
        } if "results" in x else x
    )
)
