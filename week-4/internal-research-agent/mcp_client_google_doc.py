import os
import logging
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPGoogleDocsClient:
    def __init__(self):
        self.session = None
        self.server_params = StdioServerParameters(command="python", args=["./mcp_tool.py"], env=None)

    async def start(self):
       if not os.path.exists("mcp_tool.py"):
          logger.warning("MCP server not found")
          return

       try:
        logger.info("Starting stdio_client...")
        self.client_context = stdio_client(self.server_params)

        logger.info("Calling __aenter__ to get streams...")
        self.read_stream, self.write_stream = await self.client_context.__aenter__()
        logger.info("Streams opened.")

        self.session = ClientSession(self.read_stream, self.write_stream)

        logger.info("Calling initialize...")
        await self.session.initialize()
        logger.info("MCP Google Docs client initialized successfully.")

       except Exception as e:
        logger.error(f"Client start failed: {e}")
        self.session = None

    async def stop(self):
        if self.session:
            await self.session.close()

    async def semantic_search(self, query: str, max_results: int = 5) -> str:
        try:
            result = await self.session.call_tool("semantic_search", {"query": query, "max_results": max_results})
            return result.content[0].text if result.content else ""
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return f"Error in semantic search: {e}"

    async def search_documents(self, query: str, max_results: int = 5) -> str:
        try:
            result = await self.session.call_tool("search_documents", {"query": query, "max_results": max_results})
            return result.content[0].text if result.content else ""
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return f"Error searching documents: {e}"
