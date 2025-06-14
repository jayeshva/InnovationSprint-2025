import os
import uuid
import docx
import PyPDF2
import chromadb
from datetime import datetime
from openai import OpenAI
from chromadb.utils import embedding_functions

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
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Configure sentence transformer embeddings
        self.sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Create or get existing collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.sentence_transformer_ef
        )
    
    def process_document(self, file_path: str):
        """Process a single document and prepare it for ChromaDB"""
        try:
            # Read the document
            content = read_document(file_path)
            
            # Split into chunks
            chunks = split_text(content)
            
            # Prepare metadata
            file_name = os.path.basename(file_path)
            metadatas = [{"source": file_name, "chunk": i} for i in range(len(chunks))]
            ids = [f"{file_name}_chunk_{i}" for i in range(len(chunks))]
            
            return ids, chunks, metadatas
            
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return [], [], []
    
    def add_to_collection(self, ids, texts, metadatas):
        """Add documents to collection in batches"""
        if not texts:
            return
            
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            end_idx = min(i + batch_size, len(texts))
            self.collection.add(
                documents=texts[i:end_idx],
                metadatas=metadatas[i:end_idx],
                ids=ids[i:end_idx]
            )
    
    def process_and_add_documents(self, folder_path: str):
        """Process all documents in a folder and add to collection"""
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            return
            
        files = [os.path.join(folder_path, file)
                for file in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, file))]
        
        for file_path in files:
            print(f"Processing {os.path.basename(file_path)}...")
            ids, texts, metadatas = self.process_document(file_path)
            self.add_to_collection(ids, texts, metadatas)
            print(f"Added {len(texts)} chunks to collection")
    
    def semantic_search(self, query: str, n_results: int = 3):
        """Perform semantic search on the collection"""
        results = self.collection.query(
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
    def __init__(self, openai_api_key: str, db_path: str = "chroma_db"):
        """Initialize RAG Chatbot"""
        # Set OpenAI API key
        os.environ["OPENAI_API_KEY"] = openai_api_key
        self.openai_client = OpenAI()
        
        # Initialize database and conversation manager
        self.db = RAGDatabase(db_path)
        self.conversation_manager = ConversationManager()
    
    def load_documents(self, folder_path: str):
        """Load documents from a folder into the database"""
        self.db.process_and_add_documents(folder_path)
    
    def contextualize_query(self, query: str, conversation_history: str):
        """Convert follow-up questions into standalone queries"""
        if not conversation_history.strip():
            return query
            
        contextualize_prompt = """Given a chat history and the latest user question
        which might reference context in the chat history, formulate a standalone
        question which can be understood without the chat history. Do NOT answer
        the question, just reformulate it if needed and otherwise return it as is."""
        
        try:
            completion = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": contextualize_prompt},
                    {"role": "user", "content": f"Chat history:\n{conversation_history}\n\nQuestion:\n{query}"}
                ]
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error contextualizing query: {str(e)}")
            return query  # Fallback to original query
    
    def get_prompt(self, context: str, conversation_history: str, query: str):
        """Generate a prompt combining context, history, and query"""
        prompt = f"""Based on the following context and conversation history,
        please provide a relevant and contextual response. If the answer cannot
        be derived from the context, only use the conversation history or say
        "I cannot answer this based on the provided information."

        Context from documents:
        {context}

        Previous conversation:
        {conversation_history}

        Human: {query}
        Assistant:"""
        return prompt
    
    def generate_response(self, query: str, context: str, conversation_history: str = ""):
        """Generate a response using OpenAI with conversation history"""
        prompt = self.get_prompt(context, conversation_history, query)
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",  # or gpt-3.5-turbo for lower cost
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on the provided context."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,  # Lower temperature for more focused responses
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def create_session(self):
        """Create a new conversation session"""
        return self.conversation_manager.create_session()
    
    def chat(self, query: str, session_id: str, n_chunks: int = 3, verbose: bool = False):
        """Main chat function with conversation history"""
        # Get conversation history
        conversation_history = self.conversation_manager.format_history_for_prompt(session_id)
        
        # Handle follow-up questions
        contextualized_query = self.contextualize_query(query, conversation_history)
        
        if verbose:
            print(f"Original Query: {query}")
            print(f"Contextualized Query: {contextualized_query}")
        
        # Get relevant chunks
        search_results = self.db.semantic_search(contextualized_query, n_chunks)
        context, sources = self.db.get_context_with_sources(search_results)
        
        if verbose:
            print(f"Context: {context[:200]}...")
            print(f"Sources: {sources}")
        
        # Generate response
        response = self.generate_response(contextualized_query, context, conversation_history)
        
        # Add to conversation history
        self.conversation_manager.add_message(session_id, "user", query)
        self.conversation_manager.add_message(session_id, "assistant", response)
        
        return {
            "response": response,
            "sources": sources,
            "contextualized_query": contextualized_query
        }
    
    def print_search_results(self, results):
        """Print formatted search results for debugging"""
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
# EXAMPLE USAGE
# =============================================================================

def main():
    """Example usage of the RAG Chatbot"""
    
    # Initialize the chatbot
    chatbot = RAGChatbot(
        openai_api_key="your-openai-api-key-here",  # Replace with your API key
        db_path="chroma_db"
    )
    
    # Load documents (create a 'docs' folder with your documents)
    documents_folder = "docs"
    if os.path.exists(documents_folder):
        print("Loading documents...")
        chatbot.load_documents(documents_folder)
    else:
        print(f"Please create a '{documents_folder}' folder and add your documents")
        return
    
    # Create a conversation session
    session_id = chatbot.create_session()
    print(f"Created session: {session_id}")
    
    # Example conversation
    queries = [
        "When was GreenGrow Innovations founded?",
        "Where is it located?",
        "What products do they make?"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        result = chatbot.chat(query, session_id, verbose=True)
        
        print(f"\nResponse: {result['response']}")
        print(f"\nSources: {result['sources']}")

if __name__ == "__main__":
    main()