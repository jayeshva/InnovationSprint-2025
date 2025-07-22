import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# LangChain and LangGraph imports
from langchain_aws import ChatBedrock
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.utilities import SerpAPIWrapper
from langchain.prompts import PromptTemplate
from langchain.embeddings import HuggingFaceEmbeddings
from langgraph.graph import StateGraph, END
from typing import TypedDict
from langfuse.langchain import CallbackHandler
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.integrations.langchain.runnable_rails import RunnableRails


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
HR_DOCS_PATH = os.getenv("HR_DOCS_PATH", "week-6/internal-research-agent/hr_policies")

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
langfuse_callback = CallbackHandler()  # LangFuse tracer

try:
    rails_config = RailsConfig.from_path("./week-6/internal-research-agent/guardrails_config")
    logger.info("Guardrails loaded successfully")
except Exception as e:
    logger.warning(f"Failed to load guardrails: {e}")
    rails_config = None

class EnhancedResearchAgent:
    def __init__(self):
        self.llm = ChatBedrock(model_id=BEDROCK_MODEL_ID, region_name=AWS_REGION, callbacks=[langfuse_callback])
        self.guarded_llm = self._setup_guarded_llm()
        self.hr_retriever = self._setup_hr_retriever()
        self.web_search = SerpAPIWrapper(serpapi_api_key=SERPAPI_API_KEY)

        self.router_prompt = PromptTemplate(
    input_variables=["query"],
    template=(
        "You are a tool router for Presidio’s Internal Research Agent. "
        "Your job is to read the user query and decide which tools are most relevant to answer it.\n\n"
        "Available tools:\n"
        "- HRPolicyRAG: Use this for questions about HR policies such as leave rules, benefits, holidays, working hours, or employee guidelines.\n"
        "- WebSearch: Use this for external queries—like comparing industry benchmarks, regulations, market trends, or external standard and that too only about job and software company\n"
        "- AggregateTool: Use this **only if** the query needs answers from **multiple sources** (e.g., both internal and external information).\n"
        "- unrelevant: Use this **only if** the query is unwanted to the presidio internal research agent (e.g., Stock market, politics, movies, games, entertainment etc..).\n"
        "- casual: Use this only for greetings, small talk, or general unrelated questions (e.g., 'hello', 'how are you', 'what’s up', 'what can you do').\n\n"
        "Instructions:\n"
        "1. Return only a comma-separated list of tool names from the available tools.\n"
        "2. Do not explain. Just return the list.\n"
        "3. Never invent a tool name.\n"
        "4. If unsure, default to: WebSearch.\n\n"
        "Examples:\n"
        "Q: 'Hello, how are you?' → Answer: casual\n"
        "Q: 'Leave policy for new joiners' → Answer: HRPolicyRAG\n"
        "Q: 'Compare hiring trend with industry' → Answer: WebSearch\n"
        "Q: 'How to invest in mutual funds?' → Answer: unrelevant\n"
        "Q: 'Tell me about latest movies on Netflix' → Answer: unrelevant\n"
        "Q: 'What's the weather in Chennai today?' → Answer: unrelevant\n"
        "Q: 'Summarize our Q1 feedback and compare with industry' → Answer: WebSearch, AggregateTool\n\n"
        "Question: {query}\n"
        "Answer:"
    )
)


        self.greeting_prompt = PromptTemplate(
        input_variables=["query"],
        template=(
        "You are a polite and conversational assistant. "
        "If the user greets you (e.g., says hello or asks how you are), respond warmly but briefly.\n\n"
        "User: {query}\n"
        "Response:"
        )
       )


        self.synthesis_prompt = PromptTemplate(
        input_variables=["results", "question"],
        template=(
        "You are a research assistant. Synthesize a clear and concise answer using the provided sources.\n"
        "Do not include source metadata in the final output. Do not hallucinate or assume missing information.\n\n"
        "Question: {question}\n\n"
        "Sources:\n{results}\n\n"
        "Final Answer:"
           )
        )


        self.evaluation_prompt = PromptTemplate(
        input_variables=["question", "answer"],
        template=(
        "Evaluate whether the answer correctly and concisely addresses the question.\n"
        "Return only 'PASS' or 'FAIL'. Do not explain.\n\n"
        "Question: {question}\n"
        "Answer: {answer}\n\n"
        "Evaluation:"
         )
        )


        self.optimized_hr_prompt = PromptTemplate(
            input_variables=["context", "question"],
             template=(
        "You are an expert in HR policies. Use ONLY the context below to answer the question.\n"
        "If the answer is not found in the context, say 'Information not available in HR records.'\n\n"
        "Context:\n{context}\n\n"
        "Question: {question}\n"
        "Answer:"
    )
        )

    def _setup_hr_retriever(self):
        try:
            loaders = [PyPDFLoader(os.path.join(HR_DOCS_PATH, f)) if f.endswith('.pdf') else TextLoader(os.path.join(HR_DOCS_PATH, f)) for f in os.listdir(HR_DOCS_PATH)]
            pages = [p for loader in loaders for p in loader.load()]
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
            chunks = splitter.split_documents(pages)
            vector_store = FAISS.from_documents(chunks, embedding_model)
            return vector_store.as_retriever(search_kwargs={"k": 3})
        except Exception as e:
            logger.error(f"HR retriever setup failed: {e}")
            return None

    def _setup_guarded_llm(self):
        """Setup LLM with guardrails if available"""
        if rails_config:
            try:
                # Create RunnableRails wrapper
                guarded_llm = RunnableRails(rails_config, llm=self.llm)
                logger.info("Guardrails wrapper created successfully")
                return guarded_llm
            except Exception as e:
                logger.warning(f"Failed to create guardrails wrapper: {e}")
                return self.llm
        else:
            logger.info("Using LLM without guardrails")
            return self.llm

    def hr_policy_tool(self, query: str) -> str:
        if not self.hr_retriever:
            return "HR Policy retriever is not available."
        docs = self.hr_retriever.invoke(query)
        context = "\n\n".join([d.page_content for d in docs])
        return self.guarded_llm.invoke(self.optimized_hr_prompt.format(context=context, question=query)).content

    async def web_search_tool(self, query: str) -> str:
        return self.web_search.run(query)

    def greeting_tool(self, query: str) -> str:
        return self.guarded_llm.invoke(self.greeting_prompt.format(query=query)).content
    
    def unrelevant_tool(self, query: str) -> str:
        return "I'm sorry, but I'm designed to help with internal company research and HR-related questions. I cannot assist with that topic."


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
    try:
        res = agent.guarded_llm.invoke(agent.router_prompt.format(query=query)).content
        tools = [t.strip() for t in res.split(',') if t.strip()]
        # Handle the unrelevant case
        if 'unrelevant' in tools:
            return {**state, 'selected_tools': ['unrelevant']}
        return {**state, 'selected_tools': tools}
    except Exception as e:
        logger.error(f"Router error: {e}")
        return {**state, 'selected_tools': ['casual']}

def update_state(state: AgentState, tool: str, result: str) -> AgentState:
    outputs = state['tool_outputs'].copy()
    outputs[tool] = result
    return {**state, 'tool_outputs': outputs, 'last_tool': tool}

def hr_policy_tool_node(state: AgentState) -> AgentState:
    result = agent.hr_policy_tool(state['input'])
    return update_state(state, 'HRPolicyRAG', result)

async def web_search_tool_node(state: AgentState) -> AgentState:
    result = await agent.web_search_tool(state['input'])
    return update_state(state, 'WebSearch', result)

def greeting_tool_node(state: AgentState) -> AgentState:
    result = agent.greeting_tool(state['input'])
    return {**state, 'output': result}

def evaluator_node(state: AgentState) -> AgentState:
    answer = state['tool_outputs'].get(state['last_tool'], '')
    eval_result = agent.guarded_llm.invoke(agent.evaluation_prompt.format(question=state['input'], answer=answer)).content
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
    final = agent.guarded_llm.invoke(agent.synthesis_prompt.format(results=combined, question=state['input']))
    return {**state, 'output': final.content}

def unrelevant_tool_node(state: AgentState) -> AgentState:
    result = agent.unrelevant_tool(state['input'])
    return {**state, 'output': result}

graph = StateGraph(AgentState)
graph.add_node("router", router_node)
graph.add_node("HRPolicyRAG", hr_policy_tool_node)
graph.add_node("WebSearch", web_search_tool_node)
graph.add_node("casual", greeting_tool_node)
graph.add_node("unrelevant", unrelevant_tool_node)
graph.add_node("evaluator", evaluator_node)
graph.add_node("aggregate", aggregate_node)

graph.set_entry_point("router")

def route_from_router(state: AgentState) -> str:
    if not state.get('selected_tools'):
        return "casual"
    return state['selected_tools'][0]

graph.add_conditional_edges("router", route_from_router, {
    "HRPolicyRAG": "HRPolicyRAG",
    "WebSearch": "WebSearch", 
    "casual": "casual",
    "unrelevant": "unrelevant"
})

# Add edges for tools that need evaluation
for tool in ["HRPolicyRAG", "WebSearch"]:
    graph.add_edge(tool, "evaluator")

graph.add_conditional_edges("evaluator", evaluator_router, {
    "HRPolicyRAG": "HRPolicyRAG",
    "WebSearch": "WebSearch",
    "aggregate": "aggregate"
})

# End nodes
graph.add_edge("casual", END)
graph.add_edge("unrelevant", END) 
graph.add_edge("aggregate", END)

compiled_graph = graph.compile()

app = FastAPI(title="Internal Assistant Agent API")

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str

@app.post('/query', response_model=QueryResponse)
async def query_agent(req: QueryRequest):
    try:
        result = await compiled_graph.ainvoke({
            "input": req.question,
            "tool_outputs": {}
        })
        return QueryResponse(answer=result['output'])
    except Exception as e:
        logger.error(f"API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(8000))
