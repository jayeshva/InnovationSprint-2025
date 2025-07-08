import os
import logging
from dotenv import load_dotenv

# LangChain and LangGraph imports
from langchain_aws import ChatBedrock
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.utilities import SerpAPIWrapper
from langchain.prompts import PromptTemplate
from langchain.embeddings import HuggingFaceEmbeddings
from mcp_client_google_doc import MCPGoogleDocsClient

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
HR_DOCS_PATH = os.getenv("HR_DOCS_PATH", "./hr_policies")

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

class EnhancedResearchAgent:
    def __init__(self):
        self.llm = ChatBedrock(model_id=BEDROCK_MODEL_ID, region_name=AWS_REGION)
        self.mcp_client = MCPGoogleDocsClient()
        self.hr_retriever = self._setup_hr_retriever()
        self.web_search = SerpAPIWrapper(serpapi_api_key="7e9e199b8417cce1ce67a3483e0c6d21a1646e41fa5e8952d1f8fddcef253c40")

        self.router_prompt = PromptTemplate(
    input_variables=["query"],
    template=(
        "You are a tool router for Presidio’s Internal Research Agent. "
        "Your job is to read the user query and decide which tools are most relevant to answer it.\n\n"

        "Available tools:\n"
        "- GoogleDocsTool: Use this for insurance-related queries or questions referring to Presidio documents, especially customer feedback, policy reports, or campaign summaries.\n"
        "- HRPolicyRAG: Use this for questions about HR policies such as leave rules, benefits, holidays, working hours, or employee guidelines.\n"
        "- WebSearch: Use this for external queries—like comparing industry benchmarks, regulations, market trends, or external standards.\n"
        "- AggregateTool: Use this **only if** the query needs answers from **multiple sources** (e.g., both internal and external information).\n"
        "- casual: Use this only for greetings, small talk, or general unrelated questions (e.g., 'hello', 'how are you', 'what’s up', 'what can you do').\n\n"

        "Instructions:\n"
        "1. Return only a comma-separated list of tool names from the available tools.\n"
        "2. Do not explain. Just return the list.\n"
        "3. Never invent a tool name.\n"
        "4. If unsure, default to: WebSearch.\n\n"

        "Examples:\n"
        "Q: 'Hello, how are you?' → Answer: casual\n"
        "Q: 'Summarize Q1 customer feedback' → Answer: GoogleDocsTool\n"
        "Q: 'Leave policy for new joiners' → Answer: HRPolicyRAG\n"
        "Q: 'Compare hiring trend with industry' → Answer: WebSearch\n"
        "Q: 'Summarize our Q1 feedback and compare with industry' → Answer: GoogleDocsTool, WebSearch, AggregateTool\n\n"

        "Question: {query}\n"
        "Answer:"
    )
)


        self.synthesis_prompt = PromptTemplate(
            input_variables=["results", "question"],
            template="Consolidate into a comprehensive answer.\nQuestion: {question}\nSources:\n{results}\nAnswer:"
        )

        self.evaluation_prompt = PromptTemplate(
            input_variables=["question", "answer"],
            template="Evaluate the answer. Return PASS or FAIL.\nQuestion: {question}\nAnswer: {answer}"
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

    async def start(self): await self.mcp_client.start()
    async def stop(self): await self.mcp_client.stop()

    async def google_docs_tool(self, query: str) -> str:
        result = await self.mcp_client.semantic_search(query)
        return f"[GoogleDocs] {result}" if result else await self.mcp_client.search_documents(query)

    def hr_policy_tool(self, query: str) -> str:
        docs = self.hr_retriever.invoke(query)
        context = "\n\n".join([d.page_content for d in docs])
        prompt = PromptTemplate(input_variables=["context", "question"], template="Context:\n{context}\nQ: {question}\nA:")
        return self.llm.invoke(prompt.format(context=context, question=query)).content

    async def web_search_tool(self, query: str) -> str:
        return self.web_search.run(query)
