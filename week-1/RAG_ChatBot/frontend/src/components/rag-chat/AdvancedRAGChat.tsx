import React, { useState, useRef, useEffect } from "react";
import { Upload, Sparkles, Send, FileText, AlertCircle, CheckCircle, Clock, MessageSquare, X, Menu } from "lucide-react";
import type { ChatMessage, DocumentStatus } from "./types";
import { formatFilename } from "./utils";
import { API_BASE_URL, STORAGE_KEYS, DOCUMENT_STATUS_POLLING_INTERVAL, SUPPORTED_FILE_TYPES } from "./constants";

export default function AdvancedRAGChat() {
  const [documents, setDocuments] = useState<DocumentStatus[]>([]);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const savedSessionId = localStorage.getItem(STORAGE_KEYS.SESSION_ID);
    if (savedSessionId) {
      setSessionId(savedSessionId);
    }
    const savedChatHistory = localStorage.getItem(STORAGE_KEYS.CHAT_HISTORY);
    if (savedChatHistory) {
      try {
        setChatHistory(JSON.parse(savedChatHistory));
      } catch (error) {
        console.error("Failed to parse saved chat history:", error);
      }
    }
    fetchDocuments();
  }, []);

  useEffect(() => {
    if (chatHistory.length > 0) {
      localStorage.setItem(STORAGE_KEYS.CHAT_HISTORY, JSON.stringify(chatHistory));
    }
  }, [chatHistory]);

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem(STORAGE_KEYS.SESSION_ID, sessionId);
    }
    // Refetch documents when sessionId changes
    fetchDocuments();
  }, [sessionId]);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chatHistory]);

  useEffect(() => {
    const processingDocs = documents.filter(doc => doc.status === "queued" || doc.status === "processing");
    if (processingDocs.length === 0) return;
    const intervalId = setInterval(() => {
      processingDocs.forEach(doc => {
        fetchDocumentStatus(doc.document_id);
      });
    }, DOCUMENT_STATUS_POLLING_INTERVAL);
    return () => clearInterval(intervalId);
  }, [documents]);

  const fetchDocuments = async () => {
    try {
      // If we have a session ID, only fetch documents for that session
      const url = sessionId 
        ? `${API_BASE_URL}/documents?session_id=${sessionId}`
        : `${API_BASE_URL}/documents`;
        
      const response = await fetch(url);
      if (!response.ok) throw new Error("Failed to fetch documents");
      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (error) {
      console.error("Error fetching documents:", error);
    }
  };

  const fetchDocumentStatus = async (documentId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/document/${documentId}/status`);
      if (!response.ok) return;
      const data = await response.json();
      setDocuments(prev => prev.map(doc => doc.document_id === documentId ? { ...doc, ...data } : doc));
    } catch (error) {
      console.error(`Error fetching status for document ${documentId}:`, error);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    setLoading(true);
    
    // Create a new session if one doesn't exist
    let currentSessionId = sessionId;
    if (!currentSessionId) {
      try {
        // Create a new session by making a chat request with an empty query
        const chatResponse = await fetch(`${API_BASE_URL}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: "Hello" }),
        });
        
        if (chatResponse.ok) {
          const data = await chatResponse.json();
          currentSessionId = data.session_id;
          setSessionId(currentSessionId);
          
          // Add the initial greeting to chat history
          const aiMessage: ChatMessage = {
            sender: "ai",
            text: data.response,
            timestamp: new Date().toISOString()
          };
          setChatHistory([aiMessage]);
        }
      } catch (error) {
        console.error("Error creating new session:", error);
      }
    }
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }
    
    // Add session_id to the form data
    if (currentSessionId) {
      formData.append("session_id", currentSessionId);
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Upload failed");
      const data = await response.json();
      if (data.documents && data.documents.length > 0) {
        setDocuments(prev => [...prev, ...data.documents]);
      }

      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      console.error("Error uploading files:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!input.trim()) return;
    const userMessage: ChatMessage = {
      sender: "user",
      text: input,
      timestamp: new Date().toISOString()
    };
    setChatHistory(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    try {
      const requestBody: any = { query: input };
      if (sessionId) {
        requestBody.session_id = sessionId;
      }
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      if (!response.ok) throw new Error("Failed to get response");
      const data = await response.json();
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }
      const aiMessage: ChatMessage = {
        sender: "ai",
        text: data.response,
        timestamp: new Date().toISOString()
      };
      setChatHistory(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage: ChatMessage = {
        sender: "ai",
        text: "Sorry, I encountered an error while processing your request. Please try again.",
        timestamp: new Date().toISOString()
      };
      setChatHistory(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = async () => {
    // Clear local state and storage
    setChatHistory([]);
    
    // If we have a session ID, clear it on the server
    if (sessionId) {
      try {
        const response = await fetch(`${API_BASE_URL}/clear-session`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
        });
        
        if (!response.ok) {
          console.error("Failed to clear session on server:", await response.text());
        }
      } catch (error) {
        console.error("Error clearing session on server:", error);
      }
      
      // Clear session ID and documents
      setSessionId(null);
      setDocuments([]);
      localStorage.removeItem(STORAGE_KEYS.SESSION_ID);
    }
    
    localStorage.removeItem(STORAGE_KEYS.CHAT_HISTORY);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed": return <CheckCircle size={16} className="text-emerald-500" />;
      case "failed":
      case "rejected": return <AlertCircle size={16} className="text-red-500" />;
      case "queued":
      case "processing": return <Clock size={16} className="text-blue-500 animate-pulse" />;
      default: return <FileText size={16} className="text-slate-400" />;
    }
  };

  return (
    <div className="w-full h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 flex overflow-hidden">
      {/* Mobile Sidebar Overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      
      {/* LEFT SIDEBAR - DOCUMENTS */}
      <div className={`
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        fixed lg:relative top-0 left-0 w-80 lg:w-96 bg-white/80 backdrop-blur-xl shadow-2xl border-r border-slate-200/50 
        flex flex-col h-full transition-transform duration-300 ease-in-out z-50 lg:z-auto
      `}>
        <div className="p-6 border-b border-slate-200/50 bg-white/90">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold flex items-center gap-3 text-slate-800">
              <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl">
                <FileText size={20} className="text-white" />
              </div>
              Documents
            </h2>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <X size={20} className="text-slate-600" />
            </button>
          </div>
        </div>
        
        <div className="p-6">
          <button
            className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 
                     text-white font-medium py-3 px-4 rounded-xl flex items-center justify-center gap-3 
                     transition-all duration-200 transform hover:scale-[1.02] disabled:opacity-50 disabled:transform-none"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
          >
            <Upload size={18} /> Upload Documents
          </button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept={SUPPORTED_FILE_TYPES.join(',')}
            onChange={handleFileUpload}
            multiple
          />
          <p className="text-xs text-slate-500 mt-3 text-center">
            Supported: {SUPPORTED_FILE_TYPES.map(type => type.toUpperCase().replace('.', '')).join(', ')} (Max 10MB each)
          </p>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {documents.length === 0 ? (
            <div className="text-center text-slate-500 py-12">
              <div className="p-4 bg-slate-100 rounded-2xl w-fit mx-auto mb-4">
                <FileText size={32} className="opacity-40" />
              </div>
              <p className="font-medium text-slate-700">No documents yet</p>
              <p className="text-sm mt-1">Upload documents to get started</p>
            </div>
          ) : (
            documents.map((doc) => (
              <div key={doc.document_id} className="bg-white/60 backdrop-blur-sm rounded-2xl p-4 border border-slate-200/50 hover:shadow-lg transition-all duration-200">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(doc.status)}
                    <div className="flex flex-col">
                      <span className="font-semibold text-slate-800 truncate text-sm" title={doc.filename}>
                        {formatFilename(doc.filename)}
                      </span>
                      <span className="text-xs text-slate-500">
                        {new Date(doc.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                    doc.status === "completed" ? "bg-emerald-100 text-emerald-700" :
                    doc.status === "processing" ? "bg-blue-100 text-blue-700" :
                    doc.status === "failed" || doc.status === "rejected" ? "bg-red-100 text-red-700" :
                    "bg-slate-100 text-slate-600"
                  }`}>
                    {doc.status === "completed" && doc.chunks ? `${doc.chunks} chunks` : doc.status}
                  </span>
                </div>
                
                {doc.status === "processing" && (
                  <div className="mt-3 w-full bg-slate-200 rounded-full h-1.5">
                    <div className="bg-gradient-to-r from-blue-500 to-purple-600 h-1.5 rounded-full animate-pulse w-3/4 transition-all duration-500"></div>
                  </div>
                )}
                
                {doc.message && (
                  <p className="text-xs text-slate-600 mt-2 truncate" title={doc.message}>
                    {doc.message}
                  </p>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* RIGHT SIDE - CHAT */}
      <div className="flex-1 flex flex-col h-full">
        {/* Chat header */}
        <div className="p-4 lg:p-6 border-b border-slate-200/50 bg-white/80 backdrop-blur-xl flex justify-between items-center">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <Menu size={20} className="text-slate-600" />
            </button>
            <h2 className="text-xl lg:text-2xl font-semibold flex items-center gap-3 text-slate-800">
              <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl">
                <MessageSquare size={20} className="text-white" />
              </div>
              <span className="hidden sm:inline">RAG Assistant</span>
            </h2>
          </div>
          <button 
            className="px-4 py-2 text-stone-50 bg-purple-600 hover:cursor-pointer rounded-lg 
                     transition-all duration-200 text-sm font-medium"
            onClick={handleClearChat}
          >
            Clear Session
          </button>
        </div>
        
        {/* Chat messages */}
        <div 
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-4 lg:space-y-6"
        >
          {chatHistory.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
              <div className="p-4 bg-gradient-to-br from-blue-500 to-purple-600 rounded-3xl mb-6">
                <Sparkles size={32} className="text-white" />
              </div>
              <h3 className="text-2xl font-semibold text-slate-800 mb-3">Welcome to RAG Assistant</h3>
              <p className="text-slate-600 leading-relaxed">
                Upload your documents and start asking questions. I'll analyze the content and provide accurate, 
                contextual answers based on your uploaded materials.
              </p>
              <div className="mt-8 p-4 bg-blue-50 rounded-2xl border border-blue-200">
                <p className="text-sm text-blue-700">
                  💡 <strong>Tip:</strong> Upload PDFs, Word docs, or text files to get started!
                </p>
              </div>
            </div>
          ) : (
            chatHistory.map((message, index) => (
              <div
                key={index}
                className={`max-w-4xl flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
              >
                <div className={`
                  max-w-[85%] lg:max-w-[70%] p-4 lg:p-5 rounded-2xl shadow-sm
                  ${message.sender === "user" 
                    ? "bg-gradient-to-br from-blue-500 to-purple-600 text-white ml-4" 
                    : "bg-white/70 backdrop-blur-sm border border-slate-200/50 text-slate-800 mr-4"
                  }
                `}>
                  <div className="whitespace-pre-wrap text-sm lg:text-base leading-relaxed">
                    {message.text}
                  </div>
                  <div className={`text-xs mt-2 ${
                    message.sender === "user" ? "text-blue-100" : "text-slate-500"
                  }`}>
                    {new Date(message.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              </div>
            ))
          )}
          
          {loading && (
            <div className="max-w-4xl flex justify-start">
              <div className="bg-white/70 backdrop-blur-sm border border-slate-200/50 rounded-2xl p-5 shadow-sm mr-4">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* Chat input */}
        <div className="p-4 lg:p-6 border-t border-slate-200/50 bg-white/80 backdrop-blur-xl">
          <div className="flex gap-3 lg:gap-4 max-w-4xl mx-auto">
            <div className="flex-1 relative">
              <textarea
                className="w-full min-h-[52px] max-h-40 p-4 pr-12 bg-white/80 backdrop-blur-sm border border-slate-200 
                         rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-400
                         placeholder-slate-400 text-slate-800 transition-all duration-200"
                placeholder="Ask a question about your documents..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                disabled={loading}
                rows={1}
              />
            </div>
            <button
              className="h-[52px] w-[52px] bg-gradient-to-br from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700
                       text-white rounded-2xl flex items-center justify-center transition-all duration-200 
                       transform hover:scale-105 disabled:opacity-50 disabled:transform-none shadow-lg"
              onClick={handleSendMessage}
              disabled={loading || !input.trim()}
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
