import os
import uuid
from bedrock_claude import BedrockClaudeClient
import docx
import PyPDF2
import chromadb
import re
from datetime import datetime
from chromadb.utils import embedding_functions
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import shutil
from dotenv import load_dotenv
from pydantic import BaseModel


# Load environment variables from .env file
load_dotenv()

def secure_filename(filename):
    """
    Sanitize a filename to ensure it's safe for storage.
    Removes any path components and replaces unsafe characters.
    """
    # Remove any directory path components
    filename = os.path.basename(filename)
    
    # Replace any non-alphanumeric characters except for periods, hyphens, and underscores
    filename = re.sub(r'[^\w\.-]', '_', filename)
    
    # Ensure the filename is not empty
    if not filename:
        filename = 'unnamed_file'
        
    return filename

# =============================================================================
# DOCUMENT PROCESSING AND UTILITIES
# =============================================================================

def read_text_file(file_path: str):
    """Read content from a text file"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def read_pdf_file(file_path: str):
    """Read content from a PDF file"""
    text = ""
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
    return text

def read_docx_file(file_path: str):
    """Read content from a Word document"""
    doc = docx.Document(file_path)
    return "\n".join([paragraph.text for paragraph in doc.paragraphs])

def read_document(file_path: str):
    """Read document content based on file extension"""
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()
    
    if file_extension == '.txt':
        return read_text_file(file_path)
    elif file_extension == '.pdf':
        return read_pdf_file(file_path)
    elif file_extension == '.docx':
        return read_docx_file(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_extension}")

def split_text(text: str, chunk_size: int = 500):
    """Split text into chunks while preserving sentence boundaries"""
    sentences = text.replace('\n', ' ').split('. ')
    chunks = []
    current_chunk = []
    current_size = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        # Ensure proper sentence ending
        if not sentence.endswith('.'):
            sentence += '.'
            
        sentence_size = len(sentence)
        
        # Check if adding this sentence would exceed chunk size
        if current_size + sentence_size > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_size = sentence_size
        else:
            current_chunk.append(sentence)
            current_size += sentence_size
    
    # Add the last chunk if it exists
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

# =============================================================================
# CHROMADB SETUP AND OPERATIONS
# =============================================================================

class RAGDatabase:
    def __init__(self, db_path: str = "chroma_db", collection_name: str = "documents_collection"):
        """Initialize ChromaDB with persistence"""
        self.db_path = db_path
        self.default_collection_name = collection_name
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Configure sentence transformer embeddings
        self.sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Dictionary to track session collections
        self.session_collections = {}
        
        # Create or get default collection
        self.default_collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.sentence_transformer_ef
        )
    
    def get_collection_for_session(self, session_id: str = None):
        """Get or create a collection for a specific session"""
        if not session_id:
            return self.default_collection
            
        if session_id not in self.session_collections:
            collection_name = f"session_{session_id}"
            self.session_collections[session_id] = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.sentence_transformer_ef
            )
            
        return self.session_collections[session_id]
    
    def clear_session_data(self, session_id: str):
        """Clear all data for a specific session"""
        if not session_id:
            return False
            
        collection_name = f"session_{session_id}"
        try:
            if session_id in self.session_collections:
                del self.session_collections[session_id]
                
            if collection_name in [col.name for col in self.client.list_collections()]:
                self.client.delete_collection(collection_name)
            return True
        except Exception as e:
            print(f"Error clearing session data: {str(e)}")
            return False
    
    def process_document(self, file_path: str, session_id: str = None):
        """Process a single document and prepare it for ChromaDB"""
        try:
            # Read the document
            content = read_document(file_path)
            
            # Split into chunks
            chunks = split_text(content)
            
            # Prepare metadata
            file_name = os.path.basename(file_path)
            metadatas = [{"source": file_name, "chunk": i, "session_id": session_id} for i in range(len(chunks))]
            
            # Include session_id in the document IDs if provided
            if session_id:
                ids = [f"{session_id}_{file_name}_chunk_{i}" for i in range(len(chunks))]
            else:
                ids = [f"{file_name}_chunk_{i}" for i in range(len(chunks))]
            
            return ids, chunks, metadatas
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return [], [], []
    
    def add_to_collection(self, ids, texts, metadatas, session_id: str = None):
        """Add documents to collection in batches"""
        if not texts:
            return
            
        # Get the appropriate collection
        collection = self.get_collection_for_session(session_id)
            
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            end_idx = min(i + batch_size, len(texts))
            collection.add(
                documents=texts[i:end_idx],
                metadatas=metadatas[i:end_idx],
                ids=ids[i:end_idx]
            )
    
    def process_and_add_documents(self, folder_path: str, session_id: str = None):
        """Process all documents in a folder and add to collection"""
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            return
            
        files = [os.path.join(folder_path, file)
                for file in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, file))]
        
        for file_path in files:
            print(f"Processing {os.path.basename(file_path)}...")
            ids, texts, metadatas = self.process_document(file_path, session_id)
            self.add_to_collection(ids, texts, metadatas, session_id)
            print(f"Added {len(texts)} chunks to collection")
    
    def semantic_search(self, query: str, session_id: str = None, n_results: int = 3):
        """Perform semantic search on the collection"""
        collection = self.get_collection_for_session(session_id)
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        return results
    
    def get_context_with_sources(self, results):
        """Extract context and source information from search results"""
        # Combine document chunks into a single context
        context = "\n\n".join(results['documents'][0])
        
        # Format sources with metadata
        sources = [
            f"{meta['source']} (chunk {meta['chunk']})"
            for meta in results['metadatas'][0]
        ]
        
        return context, sources

# =============================================================================
# CONVERSATION MEMORY MANAGEMENT
# =============================================================================

class ConversationManager:
    def __init__(self):
        """Initialize conversation manager"""
        self.conversations = {}
    
    def create_session(self):
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        self.conversations[session_id] = []
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to the conversation history"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
            
        self.conversations[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_conversation_history(self, session_id: str, max_messages: int = None):
        """Get conversation history for a session"""
        if session_id not in self.conversations:
            return []
            
        history = self.conversations[session_id]
        if max_messages:
            history = history[-max_messages:]
            
        return history
    
    def format_history_for_prompt(self, session_id: str, max_messages: int = 5):
        """Format conversation history for inclusion in prompts"""
        history = self.get_conversation_history(session_id, max_messages)
        formatted_history = ""
        
        for msg in history:
            role = "Human" if msg["role"] == "user" else "Assistant"
            formatted_history += f"{role}: {msg['content']}\n\n"
            
        return formatted_history.strip()

# =============================================================================
# RAG CHATBOT CLASS
# =============================================================================

class RAGChatbot:
    def __init__(self, db: RAGDatabase = None):
        """Initialize RAG Chatbot with Claude via AWS Bedrock"""
        self.claude_client = BedrockClaudeClient()
        self.db = db
        self.conversation_manager = ConversationManager()

    def load_documents(self, folder_path: str):
        self.db.process_and_add_documents(folder_path)

    def contextualize_query(self, query: str, conversation_history: str):
        """Convert follow-up questions into standalone queries"""
        if not conversation_history.strip():
            return query

        prompt = f"""Given a chat history and the latest user question
which might reference context in the chat history, formulate a standalone
question which can be understood without the chat history. Do NOT answer
the question, just reformulate it if needed and otherwise return it as is.

Chat history:
{conversation_history}

Question:
{query}
"""

        try:
            response = self.claude_client.chat([
                {"role": "user", "content": prompt},
            ])
            return response.strip()
        except Exception as e:
            print(f"Error contextualizing query: {str(e)}")
            return query

    def get_prompt(self, context: str, conversation_history: str, query: str):
        return f"""Based on the following context and conversation history,
please provide a relevant and contextual response. If the answer cannot
be derived from the context, only use the conversation history or say
"I cannot answer this based on the provided information."

Context from documents:
{context}

Previous conversation:
{conversation_history}

Human: {query}
Assistant:"""

    def generate_response(self, query: str, context: str, conversation_history: str = ""):
        prompt = self.get_prompt(context, conversation_history, query)
        try:
            response = self.claude_client.chat([
                {"role": "user", "content": prompt}
            ])
            return response.strip()
        except Exception as e:
            return f"Error generating response: {str(e)}"

    def create_session(self):
        return self.conversation_manager.create_session()

    def chat(self, query: str, session_id: str, n_chunks: int = 3, verbose: bool = True):
        conversation_history = self.conversation_manager.format_history_for_prompt(session_id)
        contextualized_query = self.contextualize_query(query, conversation_history)

        if verbose:
            print(f"Original Query: {query}")
            print(f"Contextualized Query: {contextualized_query}")
            print(f"Using session_id: {session_id}")

        # Pass the session_id to semantic_search
        search_results = self.db.semantic_search(contextualized_query, session_id, n_chunks)
        context, sources = self.db.get_context_with_sources(search_results)

        if verbose:
            print(f"Context: {context[:200]}...")
            print(f"Sources: {sources}")

        response = self.generate_response(contextualized_query, context, conversation_history)

        self.conversation_manager.add_message(session_id, "user", query)
        self.conversation_manager.add_message(session_id, "assistant", response)

        return {
            "response": response,
            "sources": sources,
            "contextualized_query": contextualized_query
        }

    def print_search_results(self, results):
        print("\nSearch Results:\n" + "-" * 50)
        for i in range(len(results['documents'][0])):
            doc = results['documents'][0][i]
            meta = results['metadatas'][0][i]
            distance = results['distances'][0][i]

            print(f"\nResult {i + 1}")
            print(f"Source: {meta['source']}, Chunk {meta['chunk']}")
            print(f"Distance: {distance}")
            print(f"Content: {doc[:200]}...")

# =============================================================================
# DOCUMENT UPLOAD AND PROCESSING
# =============================================================================

class DocumentProcessor:
    def __init__(self, upload_dir: str = "uploads", db: RAGDatabase = None):
        """Initialize document processor"""
        self.upload_dir = upload_dir
        self.db = db
        self.processing_status = {}
        # Dictionary to track documents by session
        self.session_documents = {}
        
        # Create upload directory if it doesn't exist
        os.makedirs(upload_dir, exist_ok=True)
    
    def validate_file_type(self, filename: str) -> bool:
        """Validate if file type is supported"""
        allowed_extensions = {'.pdf', '.docx', '.txt'}
        _, file_extension = os.path.splitext(filename)
        return file_extension.lower() in allowed_extensions
    
    def save_uploaded_file(self, file: UploadFile) -> str:
        """Save uploaded file to disk and return the file path"""
        # Generate a unique filename
        unique_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
        file_path = os.path.join(self.upload_dir, unique_filename)
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return file_path
    
    def process_document(self, file_path: str, document_id: str, session_id: str = None):
        """Process a document and add it to the database"""
        try:
            # Get the current status to preserve filename
            current_status = self.processing_status.get(document_id, {})
            filename = current_status.get("filename", os.path.basename(file_path))
            
            # Update status to processing
            self.processing_status[document_id] = {
                "filename": filename,
                "status": "processing",
                "message": "Document is being processed",
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }
            
            # Track document by session
            if session_id:
                if session_id not in self.session_documents:
                    self.session_documents[session_id] = []
                self.session_documents[session_id].append(document_id)
            
            # Process the document
            ids, texts, metadatas = self.db.process_document(file_path, session_id)
            
            # Add to collection
            self.db.add_to_collection(ids, texts, metadatas, session_id)
            
            # Update status to completed
            self.processing_status[document_id] = {
                "filename": filename,
                "status": "completed",
                "message": f"Document processed successfully with {len(texts)} chunks",
                "timestamp": datetime.now().isoformat(),
                "chunks": len(texts),
                "session_id": session_id
            }
            
        except Exception as e:
            # Update status to failed
            self.processing_status[document_id] = {
                "status": "failed",
                "message": f"Error processing document: {str(e)}",
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }
    
    def get_document_status(self, document_id: str) -> dict:
        """Get the processing status of a document"""
        return self.processing_status.get(document_id, {
            "status": "not_found",
            "message": "Document ID not found"
        })
    
    def get_all_documents(self, session_id: str = None) -> list:
        """Get a list of all documents and their processing status, optionally filtered by session"""
        if session_id:
            return [
                {
                    "document_id": doc_id,
                    **status
                }
                for doc_id, status in self.processing_status.items()
                if status.get("session_id") == session_id
            ]
        else:
            return [
                {
                    "document_id": doc_id,
                    **status
                }
                for doc_id, status in self.processing_status.items()
            ]
    
    def clear_session_documents(self, session_id: str) -> bool:
        """Clear all documents associated with a session"""
        if not session_id or session_id not in self.session_documents:
            return False
            
        # Get document IDs for this session
        doc_ids = self.session_documents[session_id]
        
        # Remove documents from processing status
        for doc_id in doc_ids:
            if doc_id in self.processing_status:
                del self.processing_status[doc_id]
        
        # Remove session from tracking
        del self.session_documents[session_id]
        
        return True

# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

# Initialize FastAPI app
app = FastAPI(title="RAG Chatbot API", description="API for RAG Chatbot with document upload and processing")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Get configuration from environment variables
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")
DB_PATH = os.environ.get("DB_PATH", "chroma_db")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "documents_collection")
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 10 * 1024 * 1024))  # Default: 10MB

# Initialize RAG database with collection name from environment variables
rag_database = RAGDatabase(db_path=DB_PATH, collection_name=COLLECTION_NAME)

# Initialize document processor with the shared RAG database
document_processor = DocumentProcessor(upload_dir=UPLOAD_DIR, db=rag_database)

chatbot = RAGChatbot(db=rag_database)

class UploadRequest(BaseModel):
    session_id: Optional[str] = None

@app.post("/upload", response_model=dict)
async def upload_document(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = Form(None),
    max_file_size: int = MAX_FILE_SIZE
):
    """
    Upload one or more documents for processing.
    
    - Accepts PDF, DOCX, and TXT files
    - Enforces file size limit (default: 10MB)
    - Returns unique identifiers for each document
    - Processes documents in the background
    - Associates documents with a session if session_id is provided
    """
    results = []
    
    for file in files:
        # Generate a unique document ID
        document_id = str(uuid.uuid4())
        
        # Validate file type
        if not document_processor.validate_file_type(file.filename):
            results.append({
                "filename": file.filename,
                "document_id": document_id,
                "status": "rejected",
                "message": "Unsupported file type. Allowed types: PDF, DOCX, TXT"
            })
            continue
        
        # Check file size
        file.file.seek(0, 2)  # Move to end of file to get size
        file_size = file.file.tell()
        file.file.seek(0)  # Reset file position
        
        if file_size > max_file_size:
            results.append({
                "filename": file.filename,
                "document_id": document_id,
                "status": "rejected",
                "message": f"File too large. Maximum size: {max_file_size / (1024 * 1024):.1f} MB"
            })
            continue
        
        try:
            # Save the file
            file_path = document_processor.save_uploaded_file(file)
            
            # Extract original filename without UUID prefix
            original_filename = file.filename
            
            # Update initial status
            document_processor.processing_status[document_id] = {
                "filename": original_filename,
                "status": "queued",
                "message": "Document queued for processing",
                "timestamp": datetime.now().isoformat(),
                "file_size": file_size,
                "session_id": session_id
            }
            
            # Process document in background
            background_tasks.add_task(
                document_processor.process_document,
                file_path,
                document_id,
                session_id
            )
            
            results.append({
                "filename": file.filename,
                "document_id": document_id,
                "status": "accepted",
                "message": "Document accepted and queued for processing",
                "session_id": session_id
            })
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "document_id": document_id,
                "status": "error",
                "message": f"Error processing upload: {str(e)}"
            })
    
    return {"documents": results}

@app.get("/document/{document_id}/status")
async def get_document_status(document_id: str):
    """Get the processing status of a document"""
    status = document_processor.get_document_status(document_id)
    
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Document not found")
    
    return status

@app.get("/documents")
async def list_documents(session_id: Optional[str] = None):
    """
    Get a list of all documents and their processing status.
    
    - If session_id is provided, only returns documents for that session
    """
    return {"documents": document_processor.get_all_documents(session_id)}

class ClearSessionRequest(BaseModel):
    session_id: str

@app.post("/clear-session")
async def clear_session(request: ClearSessionRequest):
    """
    Clear all data for a specific session.
    
    - Removes all documents associated with the session
    - Clears conversation history
    - Deletes vector data from the database
    """
    session_id = request.session_id
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")
    
    # Clear documents
    document_processor.clear_session_documents(session_id)
    
    # Clear vector data
    rag_database.clear_session_data(session_id)
    
    # Clear conversation history
    try:
        if session_id in chatbot.conversation_manager.conversations:
            del chatbot.conversation_manager.conversations[session_id]
    except Exception as e:
        print(f"Error clearing conversation history: {str(e)}")
    
    return {"success": True, "message": "Session data cleared successfully"}

class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    n_chunks: int = 3


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat with the RAG chatbot.
    
    - If no session_id is provided, a new session will be created
    - Returns the chatbot's response and sources
    """
    # Create a new session if none provided
    session_id = request.session_id or chatbot.create_session()
    result = chatbot.chat(request.query, session_id, request.n_chunks)
    
    
    return {
        "session_id": session_id,
        "response": result["response"],
        "sources": result["sources"],
        "contextualized_query": result["contextualized_query"]
    }

# =============================================================================
# SERVER STARTUP
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Get host and port from environment variables
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 8000))
    
    print(f"Starting server at http://{HOST}:{PORT}")
    print(f"API documentation available at http://{HOST}:{PORT}/docs")
    
    uvicorn.run(app, host=HOST, port=PORT)
