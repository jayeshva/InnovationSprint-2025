#!/usr/bin/env python3
"""
MCP Server for Google Docs integration
Provides tools and resources for accessing Google Drive documents
"""

import json
import os
import logging
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from mcp.server import Server
import mcp.types as types
from mcp.server.stdio import stdio_server
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
GOOGLE_CREDS = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID")

class GoogleDocsServer:
    def __init__(self):
        self.server = Server(name="google-docs")
        self.drive_service = None
        self.docs_service = None
        self._initialize_services()
        self._setup_handlers()
    
    def _initialize_services(self):
        """Initialize Google Drive and Docs services"""
        try:
            if GOOGLE_CREDS:
                # Load credentials from JSON string
                with open("service-account.json", "r") as f:
                    creds_info = json.load(f)
                credentials = service_account.Credentials.from_service_account_info(
                    creds_info,
                    scopes=[
                        'https://www.googleapis.com/auth/drive.readonly',
                        'https://www.googleapis.com/auth/documents.readonly'
                    ]
                )
            else:
                # Use default credentials
                credentials = service_account.Credentials.from_service_account_file(
                    'service-account.json',
                    scopes=[
                        'https://www.googleapis.com/auth/drive.readonly',
                        'https://www.googleapis.com/auth/documents.readonly'
                    ]
                )
            
            self.drive_service = build('drive', 'v3', credentials=credentials)
            self.docs_service = build('docs', 'v1', credentials=credentials)
            logger.info("Google services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google services: {e}")
            raise
    
    def _setup_handlers(self):
        """Set up MCP handlers"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> list[types.Resource]:
            """List available Google Drive documents as resources"""
            try:
                resources = []
                
                # List documents in specified folder
                query = f"'{GDRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.document'"
                if not GDRIVE_FOLDER_ID:
                    query = "mimeType='application/vnd.google-apps.document'"
                
                results = self.drive_service.files().list(
                    q=query,
                    pageSize=50,
                    fields="nextPageToken, files(id, name, modifiedTime, description)"
                ).execute()
                
                files = results.get('files', [])
                
                for file in files:
                    resources.append(types.Resource(
                        uri=f"gdocs://document/{file['id']}",
                        name=file['name'],
                        description=file.get('description', f"Google Doc: {file['name']}"),
                        mimeType="text/plain"
                    ))
                
                logger.info(f"Listed {len(resources)} Google Docs resources")
                return resources
                
            except HttpError as e:
                logger.error(f"Error listing resources: {e}")
                return []
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read content from a Google Doc"""
            try:
                # Parse document ID from URI
                parsed = urlparse(uri)
                if parsed.scheme != "gdocs" or not parsed.path.startswith("/document/"):
                    raise ValueError(f"Invalid URI format: {uri}")
                
                doc_id = parsed.path.split("/")[-1]
                
                # Get document content
                doc = self.docs_service.documents().get(documentId=doc_id).execute()
                content = self._extract_text_from_doc(doc)
                
                logger.info(f"Read document {doc_id}, content length: {len(content)}")
                return content
                
            except HttpError as e:
                logger.error(f"Error reading resource {uri}: {e}")
                raise RuntimeError(f"Failed to read document: {e}")
            except Exception as e:
                logger.error(f"Error reading resource {uri}: {e}")
                raise RuntimeError(f"Failed to read document: {e}")
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available tools"""
            return [
                types.Tool(
                    name="search_documents",
                    description="Search for documents in Google Drive by name or content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for document names or content"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_document_content",
                    description="Get the full content of a specific Google Doc by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "The Google Doc document ID"
                            }
                        },
                        "required": ["document_id"]
                    }
                ),
                types.Tool(
                    name="list_folder_documents",
                    description="List all documents in a specific Google Drive folder",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "folder_id": {
                                "type": "string",
                                "description": "The Google Drive folder ID (optional, uses default if not provided)"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="semantic_search",
                    description="Perform semantic search across document content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Semantic search query"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict[str, Any]
        ) -> list[types.TextContent]:
            """Handle tool calls"""
            try:
                if name == "search_documents":
                    return await self._search_documents(arguments)
                elif name == "get_document_content":
                    return await self._get_document_content(arguments)
                elif name == "list_folder_documents":
                    return await self._list_folder_documents(arguments)
                elif name == "semantic_search":
                    return await self._semantic_search(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    def _extract_text_from_doc(self, doc: Dict[str, Any]) -> str:
        """Extract plain text from Google Doc structure"""
        content = doc.get('body', {}).get('content', [])
        text_parts = []
        
        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                for elem in paragraph.get('elements', []):
                    if 'textRun' in elem:
                        text_parts.append(elem['textRun'].get('content', ''))
            elif 'table' in element:
                # Handle table content
                table = element['table']
                for row in table.get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        for cell_content in cell.get('content', []):
                            if 'paragraph' in cell_content:
                                paragraph = cell_content['paragraph']
                                for elem in paragraph.get('elements', []):
                                    if 'textRun' in elem:
                                        text_parts.append(elem['textRun'].get('content', ''))
        
        return ''.join(text_parts)
    
    async def _search_documents(self, arguments: dict) -> list[types.TextContent]:
        """Search for documents by name"""
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 10)
        
        try:
            # Search by name
            search_query = f"name contains '{query}' and mimeType='application/vnd.google-apps.document'"
            if GDRIVE_FOLDER_ID:
                search_query = f"'{GDRIVE_FOLDER_ID}' in parents and " + search_query
            
            results = self.drive_service.files().list(
                q=search_query,
                pageSize=max_results,
                fields="files(id, name, modifiedTime, description)"
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                return [types.TextContent(
                    type="text",
                    text=f"No documents found matching query: {query}"
                )]
            
            result_text = f"Found {len(files)} documents matching '{query}':\n\n"
            for file in files:
                result_text += f"• {file['name']} (ID: {file['id']})\n"
                if file.get('description'):
                    result_text += f"  Description: {file['description']}\n"
                result_text += f"  Modified: {file.get('modifiedTime', 'Unknown')}\n\n"
            
            return [types.TextContent(type="text", text=result_text)]
            
        except HttpError as e:
            return [types.TextContent(
                type="text",
                text=f"Error searching documents: {e}"
            )]
    
    async def _get_document_content(self, arguments: dict) -> list[types.TextContent]:
        """Get content of a specific document"""
        doc_id = arguments.get("document_id")
        
        if not doc_id:
            return [types.TextContent(
                type="text",
                text="Error: document_id is required"
            )]
        
        try:
            doc = self.docs_service.documents().get(documentId=doc_id).execute()
            content = self._extract_text_from_doc(doc)
            
            return [types.TextContent(
                type="text",
                text=f"Document: {doc.get('title', 'Untitled')}\n\n{content}"
            )]
            
        except HttpError as e:
            return [types.TextContent(
                type="text",
                text=f"Error getting document content: {e}"
            )]
    
    async def _list_folder_documents(self, arguments: dict) -> list[types.TextContent]:
        """List documents in a folder"""
        folder_id = arguments.get("folder_id", GDRIVE_FOLDER_ID)
        
        try:
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document'"
            if not folder_id:
                query = "mimeType='application/vnd.google-apps.document'"
            
            results = self.drive_service.files().list(
                q=query,
                pageSize=50,
                fields="files(id, name, modifiedTime, description, size)"
            ).execute()
            
            files = results.get('files', [])
            
            if not files:
                return [types.TextContent(
                    type="text",
                    text="No documents found in the specified folder"
                )]
            
            result_text = f"Found {len(files)} documents:\n\n"
            for file in files:
                result_text += f"• {file['name']}\n"
                result_text += f"  ID: {file['id']}\n"
                if file.get('description'):
                    result_text += f"  Description: {file['description']}\n"
                result_text += f"  Modified: {file.get('modifiedTime', 'Unknown')}\n\n"
            
            return [types.TextContent(type="text", text=result_text)]
            
        except HttpError as e:
            return [types.TextContent(
                type="text",
                text=f"Error listing documents: {e}"
            )]
    
    async def _semantic_search(self, arguments: dict) -> list[types.TextContent]:
        """Perform semantic search across document content"""
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)
        
        try:
            # Get all documents first
            search_query = f"mimeType='application/vnd.google-apps.document'"
            if GDRIVE_FOLDER_ID:
                search_query = f"'{GDRIVE_FOLDER_ID}' in parents and " + search_query
            
            results = self.drive_service.files().list(
                q=search_query,
                pageSize=20,  # Limit to avoid too many API calls
                fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            
            # Search through document content
            relevant_docs = []
            for file in files:
                try:
                    doc = self.docs_service.documents().get(documentId=file['id']).execute()
                    content = self._extract_text_from_doc(doc)
                    
                    # Simple keyword matching (in production, you'd use proper embeddings)
                    if query.lower() in content.lower():
                        # Find relevant snippets
                        sentences = content.split('.')
                        relevant_snippets = [
                            sentence.strip() for sentence in sentences 
                            if query.lower() in sentence.lower()
                        ][:3]  # Max 3 snippets per document
                        
                        relevant_docs.append({
                            'name': file['name'],
                            'id': file['id'],
                            'snippets': relevant_snippets
                        })
                        
                        if len(relevant_docs) >= max_results:
                            break
                            
                except HttpError as e:
                    logger.warning(f"Could not read document {file['id']}: {e}")
                    continue
            
            if not relevant_docs:
                return [types.TextContent(
                    type="text",
                    text=f"No documents found containing: {query}"
                )]
            
            result_text = f"Found {len(relevant_docs)} relevant documents for '{query}':\n\n"
            for doc in relevant_docs:
                result_text += f"📄 {doc['name']} (ID: {doc['id']})\n"
                for snippet in doc['snippets']:
                    result_text += f"  • {snippet}...\n"
                result_text += "\n"
            
            return [types.TextContent(type="text", text=result_text)]
            
        except HttpError as e:
            return [types.TextContent(
                type="text",
                text=f"Error in semantic search: {e}"
            )]

async def main():

    logger.info("Starting GoogleDocsServer...")
    GoogleDocsServer()  # Initializes and sets up handlers

    logger.info("Running MCP server via stdio_server...")
    async with stdio_server():
        await asyncio.Event().wait()  # Keeps the server running



if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
