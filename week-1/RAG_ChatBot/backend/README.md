# RAG Chatbot Backend

This is the backend for the RAG (Retrieval-Augmented Generation) Chatbot application. It provides API endpoints for document upload, processing, and chat functionality.

## Features

- Document upload and processing (PDF, DOCX, TXT)
- Document status tracking
- RAG-based chat functionality
- Background processing of documents

## Setup Instructions

### Option 1: Using the Setup Script (macOS/Linux)

```bash
# Navigate to the backend directory
cd backend

# Make the setup script executable (if not already)
chmod +x setup.sh

# Run the setup script
./setup.sh
```

The setup script will:
1. Create a virtual environment
2. Install all dependencies
3. Create the uploads directory
4. Create a template .env file (you'll need to add your OpenAI API key)

### Option 2: Manual Setup

#### 1. Create a Virtual Environment

For Windows:
```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\activate
```

For macOS/Linux:
```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
source venv/bin/activate
```

#### 2. Install Dependencies

```bash
# Install all required packages
pip install -r requirements.txt
```

#### 3. Set Environment Variables

Create a `.env` file in the backend directory configure the data


### Running the API Server

```bash
# Start the FastAPI server
python app.py
```

Or alternatively:

```bash
# Start with uvicorn directly
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Document Upload

- `POST /upload`: Upload one or more documents for processing
  - Accepts multipart/form-data with files
  - Returns document IDs and initial processing status

### Document Status

- `GET /document/{document_id}/status`: Get the processing status of a document
- `GET /documents`: List all documents and their processing status

### Chat

- `POST /chat`: Chat with the RAG chatbot
  - Parameters:
    - `query`: The user's question
    - `session_id` (optional): Session ID for conversation continuity
    - `n_chunks` (optional): Number of document chunks to retrieve

## Directory Structure

- `uploads/`: Directory where uploaded documents are stored
- `chroma_db/`: Directory where the vector database is stored
