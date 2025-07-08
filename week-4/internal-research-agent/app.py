import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import TypedDict
from research_agent import EnhancedResearchAgent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


agent = EnhancedResearchAgent()

class AgentState(TypedDict):
    input: str
    output: Optional[str]
    selected_tools: Optional[List[str]]
    tool_outputs: Dict[str, str]
    feedback: Optional[str]
    last_tool: Optional[str]

def router_node(state: AgentState) -> AgentState:
    query = state['input']
    res = agent.llm.invoke(agent.router_prompt.format(query=query)).content
    print(f"Router : {res}")
    return {**state, 'selected_tools': [t.strip() for t in res.split(',') if t.strip()]}

def update_state(state: AgentState, tool: str, result: str) -> AgentState:
    outputs = state['tool_outputs'].copy()
    outputs[tool] = result
    return {**state, 'tool_outputs': outputs, 'last_tool': tool}

async def google_docs_tool_node(state: AgentState) -> AgentState:
    result = await agent.google_docs_tool(state['input'])
    return update_state(state, 'GoogleDocsTool', result)

def hr_policy_tool_node(state: AgentState) -> AgentState:
    result = agent.hr_policy_tool(state['input'])
    return update_state(state, 'HRPolicyRAG', result)

async def web_search_tool_node(state: AgentState) -> AgentState:
    result = await agent.web_search_tool(state['input'])
    return update_state(state, 'WebSearch', result)

def evaluator_node(state: AgentState) -> AgentState:
    answer = state['tool_outputs'].get(state['last_tool'], '')
    eval_result = agent.llm.invoke(agent.evaluation_prompt.format(question=state['input'], answer=answer)).content
    return {**state, 'feedback': eval_result if eval_result.upper().startswith("FAIL") else None}

def evaluator_router(state: AgentState) -> str:
    if state.get('feedback'): return state['last_tool']
    done = state['tool_outputs'].keys()
    for tool in state['selected_tools']:
        if tool not in done:
            return tool
    return "aggregate"

def aggregate_node(state: AgentState) -> AgentState:
    combined = "\n\n".join(f"[{k}]: {v}" for k,v in state['tool_outputs'].items())
    final = agent.llm.invoke(agent.synthesis_prompt.format(results=combined, question=state['input']))
    return {**state, 'output': final.content}

graph = StateGraph(AgentState)
graph.add_node("router", router_node)
graph.add_node("GoogleDocsTool", google_docs_tool_node)
graph.add_node("HRPolicyRAG", hr_policy_tool_node)
graph.add_node("WebSearch", web_search_tool_node)
graph.add_node("evaluator", evaluator_node)
graph.add_node("aggregate", aggregate_node)

graph.set_entry_point("router")
graph.add_conditional_edges("router", lambda s: s['selected_tools'][0], {
    "GoogleDocsTool": "GoogleDocsTool",
    "HRPolicyRAG": "HRPolicyRAG",
    "WebSearch": "WebSearch"
})
for tool in ["GoogleDocsTool", "HRPolicyRAG", "WebSearch"]:
    graph.add_edge(tool, "evaluator")
graph.add_conditional_edges("evaluator", evaluator_router, {
    "GoogleDocsTool": "GoogleDocsTool",
    "HRPolicyRAG": "HRPolicyRAG",
    "WebSearch": "WebSearch",
    "aggregate": "aggregate"
})
graph.set_finish_point("aggregate")
compiled_graph = graph.compile()


# FastAPI app
app = FastAPI(title="Enhanced Internal Research Agent API")

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str

@app.on_event("startup")
async def startup_event():
    """Initialize the agent on startup"""
    # await agent.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await agent.stop()

@app.post('/query-old', response_model=QueryResponse)
async def query_agent(req: QueryRequest):
    """Query the research agent"""
    try:
        answer = await agent.process_query(req.question)
        return QueryResponse(answer=answer)
    except Exception as e:
        logger.error(f"API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post('/query', response_model=QueryResponse)
async def query_agent(req: QueryRequest):
    """Query the research agent"""
    try:
      result = await compiled_graph.ainvoke({
            "input": req.question,
            "tool_outputs": {}
        })
      return QueryResponse(answer=result['output'])
    except Exception as e:
        logger.error(f"API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/health')
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "mcp_connected": agent.mcp_client.session is not None}

@app.get('/resources')
async def list_resources():
    """List available Google Docs resources"""
    try:
        resources = await agent.mcp_client.list_resources()
        return {"resources": resources}
    except Exception as e:
        logger.error(f"Error listing resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(8000))