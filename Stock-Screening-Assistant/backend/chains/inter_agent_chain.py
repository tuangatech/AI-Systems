from langchain_core.runnables import RunnableMap, RunnableLambda
from backend.agents.intent_parser import IntentParserAgent
from backend.agents.data_processor import DataProcessorAgent
from backend.agents.explanation import ExplanationAgent
from functools import partial

# Instantiate agents once to maintain cache across requests
intent_parser = IntentParserAgent()
data_processor = DataProcessorAgent()
explanation_agent = ExplanationAgent()

# Step 1: Run intent parser
# from main.py: inter_agent_chain.invoke({"query": user_input})
parser_step = RunnableLambda(lambda inputs: intent_parser.invoke(inputs))
# returns a dict with keys: intent (if parse successfully), input, clarification_needed, error (if any), 
# raw_response (if cannot parse input)
# and parsed (if clarification_needed is True)

# Step 2: Route based on clarification_needed flag
clarification_router = RunnableLambda(
    lambda parsed: {
        "short_circuit": True,
        "error": parsed.get("error", "Clarification required."),
        "parsed": parsed.get("parsed", {}),
        "raw_response": parsed.get("raw_response"),
    } if parsed.get("clarification_needed") else {
        "intent": parsed["intent"],
        "query": parsed["query"],
    }   # input structure for DataProcessorAgent invoke() is {"intent": intent, "query": query}
)

# Step 3: Run data processor
# processor_step = RunnableLambda(lambda x: data_processor.invoke(x)) # to pass both intent and query, rather than just x["intent"]
def run_data_processor(data, agent: DataProcessorAgent):
    # data should contain {"intent": intent, "query": query} from clarification_router
    result = agent.invoke(data)         # include intent and query in the input
    return {
        **data,
        "results": result["results"]    # Add results to the data
    } 
processor_step = RunnableLambda(partial(run_data_processor, agent=data_processor))

# Step 4: Run explanation agent
# explainer_step = RunnableLambda(lambda x: explanation_agent.invoke(x))
def run_explainer(data, agent: ExplanationAgent):
    # data should contain {"intent": intent, "query": query, "results": results}
    explanation = agent.invoke(data)
    return {**data, "explanation": explanation} # data should contain {"intent": intent, "query": query, "results": results, "explanation": explanation}

explainer_step = RunnableLambda(partial(run_explainer, agent=explanation_agent))

# Step 5: Compose full inter-agent chain
inter_agent_chain = (
    parser_step
    | clarification_router
    | RunnableLambda(lambda x: x if x.get("short_circuit") else processor_step.invoke(x))
    | RunnableLambda(lambda x: explainer_step.invoke(x) if not x.get("short_circuit") and "results" in x else x)
)
