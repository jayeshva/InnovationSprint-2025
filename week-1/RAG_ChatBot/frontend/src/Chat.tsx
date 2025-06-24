import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Upload, 
  FileText, 
  Bot, 
  User, 
  Settings, 
  Trash2, 
  Download,
  Copy,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  Zap,
  Brain,
  MessageSquare,
  Plus,
  Search,
  Sparkles
} from 'lucide-react';

const AdvancedRAGChat = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      type: 'assistant',
      content: "👋 Hello! I'm your AI assistant powered by advanced RAG technology. Upload documents or ask me anything!",
      timestamp: new Date().toLocaleTimeString(),
      sources: []
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('session-' + Date.now());
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [showSettings, setShowSettings] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [settings, setSettings] = useState({
    temperature: 0.7,
    maxTokens: 500,
    chunks: 3,
    model: 'gpt-4'
  });

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
    }
  }, [inputMessage]);

  const handleSendMessage = async () => {
    if (!inputMessage.trim()) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date().toLocaleTimeString(),
      sources: []
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      // Simulate API call to your RAG backend
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      const assistantMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: `I understand you're asking about "${inputMessage}". This is a simulated response. In your actual implementation, this would be the response from your RAG chatbot with relevant context from your documents.`,
        timestamp: new Date().toLocaleTimeString(),
        sources: [
          'document1.pdf (chunk 2)',
          'research_paper.docx (chunk 5)'
        ]
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toLocaleTimeString(),
        sources: []
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files);
    const newFiles = files.map(file => ({
      id: Date.now() + Math.random(),
      name: file.name,
      size: file.size,
      type: file.type,
      uploadTime: new Date().toLocaleTimeString()
    }));
    
    setUploadedFiles(prev => [...prev, ...newFiles]);
    
    // Add system message about file upload
    const uploadMessage = {
      id: Date.now(),
      type: 'system',
      content: `📁 Uploaded ${files.length} file(s): ${files.map(f => f.name).join(', ')}`,
      timestamp: new Date().toLocaleTimeString(),
      sources: []
    };
    setMessages(prev => [...prev, uploadMessage]);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const clearChat = () => {
    setMessages([{
      id: 1,
      type: 'assistant',
      content: "👋 Chat cleared! I'm ready for new questions.",
      timestamp: new Date().toLocaleTimeString(),
      sources: []
    }]);
    setSessionId('session-' + Date.now());
  };

  const MessageBubble = ({ message }) => {
    const isUser = message.type === 'user';
    const isSystem = message.type === 'system';
    
    return (
      <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-6 animate-fadeInUp`}>
        {!isUser && !isSystem && (
          <div className="flex-shrink-0 mr-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg">
              <Bot size={20} className="text-white" />
            </div>
          </div>
        )}
        
        <div className={`max-w-[75%] ${isUser ? 'order-1' : 'order-2'}`}>
          <div className={`
            relative px-6 py-4 rounded-2xl shadow-lg backdrop-blur-sm border
            ${isUser 
              ? 'bg-gradient-to-br from-blue-500 to-purple-600 text-white border-blue-400/30' 
              : isSystem
                ? 'bg-amber-50 text-amber-800 border-amber-200'
                : 'bg-white/90 text-gray-800 border-gray-200'
            }
          `}>
            {!isSystem && (
              <div className="flex items-center justify-between mb-2">
                <span className={`text-xs font-medium ${isUser ? 'text-blue-100' : 'text-gray-500'}`}>
                  {isUser ? 'You' : 'AI Assistant'}
                </span>
                <span className={`text-xs ${isUser ? 'text-blue-100' : 'text-gray-400'}`}>
                  {message.timestamp}
                </span>
              </div>
            )}
            
            <div className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </div>
            
            {message.sources && message.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200/50">
                <div className="text-xs text-gray-600 mb-2 font-medium">Sources:</div>
                <div className="flex flex-wrap gap-2">
                  {message.sources.map((source, idx) => (
                    <span key={idx} className="inline-flex items-center px-2 py-1 rounded-full bg-gray-100 text-xs text-gray-600">
                      <FileText size={12} className="mr-1" />
                      {source}
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            {!isUser && !isSystem && (
              <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-200/50">
                <button 
                  onClick={() => copyToClipboard(message.content)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                  title="Copy"
                >
                  <Copy size={14} />
                </button>
                <button className="text-gray-400 hover:text-green-500 transition-colors" title="Good response">
                  <ThumbsUp size={14} />
                </button>
                <button className="text-gray-400 hover:text-red-500 transition-colors" title="Poor response">
                  <ThumbsDown size={14} />
                </button>
              </div>
            )}
          </div>
        </div>
        
        {isUser && (
          <div className="flex-shrink-0 ml-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
              <User size={20} className="text-white" />
            </div>
          </div>
        )}
      </div>
    );
  };

  const TypingIndicator = () => (
    <div className="flex justify-start mb-6 animate-fadeInUp">
      <div className="flex-shrink-0 mr-3">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shadow-lg">
          <Bot size={20} className="text-white" />
        </div>
      </div>
      <div className="bg-white/90 backdrop-blur-sm border border-gray-200 px-6 py-4 rounded-2xl shadow-lg">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
            <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
          </div>
          <span className="text-sm text-gray-500 ml-2">AI is thinking...</span>
        </div>
      </div>
    </div>
  );

  return (
    <div className="h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex flex-col relative overflow-hidden">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-4 -right-4 w-24 h-24 bg-purple-200 rounded-full blur-xl opacity-30 animate-pulse"></div>
        <div className="absolute top-1/3 -left-8 w-32 h-32 bg-blue-200 rounded-full blur-xl opacity-20 animate-pulse" style={{animationDelay: '1s'}}></div>
        <div className="absolute bottom-1/4 right-1/3 w-20 h-20 bg-pink-200 rounded-full blur-xl opacity-25 animate-pulse" style={{animationDelay: '2s'}}></div>
      </div>

      {/* Header */}
      <header className="bg-white/80 backdrop-blur-lg border-b border-gray-200/50 p-4 flex items-center justify-between relative z-10">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center shadow-lg">
            <Brain size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
              RAG Assistant
            </h1>
            <p className="text-sm text-gray-500">Powered by Advanced AI</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className="relative">
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-4 py-2 text-sm bg-gray-100 border border-gray-200 rounded-full focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
            />
            <Search size={16} className="absolute left-2.5 top-2.5 text-gray-400" />
          </div>
          
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded-full transition-all"
            title="Settings"
          >
            <Settings size={20} />
          </button>
          
          <button
            onClick={clearChat}
            className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-full transition-all"
            title="Clear Chat"
          >
            <Trash2 size={20} />
          </button>
        </div>
      </header>

      {/* Settings Panel */}
      {showSettings && (
        <div className="absolute top-16 right-4 w-80 bg-white rounded-xl shadow-2xl border border-gray-200 p-6 z-50 animate-slideInRight">
          <h3 className="text-lg font-semibold mb-4 text-gray-800">Settings</h3>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Model</label>
              <select 
                value={settings.model}
                onChange={(e) => setSettings(prev => ({...prev, model: e.target.value}))}
                className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              >
                <option value="gpt-4">GPT-4</option>
                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Temperature: {settings.temperature}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={settings.temperature}
                onChange={(e) => setSettings(prev => ({...prev, temperature: parseFloat(e.target.value)}))}
                className="w-full"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Max Tokens: {settings.maxTokens}
              </label>
              <input
                type="range"
                min="100"
                max="2000"
                step="100"
                value={settings.maxTokens}
                onChange={(e) => setSettings(prev => ({...prev, maxTokens: parseInt(e.target.value)}))}
                className="w-full"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Context Chunks: {settings.chunks}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={settings.chunks}
                onChange={(e) => setSettings(prev => ({...prev, chunks: parseInt(e.target.value)}))}
                className="w-full"
              />
            </div>
          </div>
        </div>
      )}

      {/* File Upload Area */}
      {uploadedFiles.length > 0 && (
        <div className="bg-white/70 backdrop-blur-sm border-b border-gray-200/50 p-4">
          <div className="flex items-center space-x-2 mb-2">
            <FileText size={16} className="text-purple-600" />
            <span className="text-sm font-medium text-gray-700">Uploaded Documents</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {uploadedFiles.map((file) => (
              <div key={file.id} className="flex items-center space-x-2 bg-purple-50 text-purple-700 px-3 py-1 rounded-full text-xs">
                <FileText size={12} />
                <span>{file.name}</span>
                <button
                  onClick={() => setUploadedFiles(prev => prev.filter(f => f.id !== file.id))}
                  className="text-purple-500 hover:text-purple-700"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 relative z-10">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {isLoading && <TypingIndicator />}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="bg-white/80 backdrop-blur-lg border-t border-gray-200/50 p-4 relative z-10">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end space-x-3">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              multiple
              accept=".pdf,.docx,.txt"
              className="hidden"
            />
            
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex-shrink-0 p-3 text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded-full transition-all border border-gray-200 hover:border-purple-300"
              title="Upload Documents"
            >
              <Upload size={20} />
            </button>
            
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask me anything about your documents..."
                className="w-full px-4 py-3 pr-12 bg-white border border-gray-300 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none transition-all shadow-sm"
                rows={1}
                disabled={isLoading}
              />
              
              <button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim() || isLoading}
                className={`absolute right-2 top-1/2 transform -translate-y-1/2 p-2 rounded-full transition-all ${
                  inputMessage.trim() && !isLoading
                    ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:from-purple-600 hover:to-pink-600 shadow-lg'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}
              >
                {isLoading ? (
                  <RefreshCw size={18} className="animate-spin" />
                ) : (
                  <Send size={18} />
                )}
              </button>
            </div>
          </div>
          
          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
            <div className="flex items-center space-x-4">
              <span className="flex items-center">
                <Zap size={12} className="mr-1 text-yellow-500" />
                RAG Enabled
              </span>
              <span className="flex items-center">
                <Sparkles size={12} className="mr-1 text-purple-500" />
                Session: {sessionId.slice(-6)}
              </span>
            </div>
            <span>Press Enter to send, Shift+Enter for new line</span>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes slideInRight {
          from {
            opacity: 0;
            transform: translateX(20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        
        .animate-fadeInUp {
          animation: fadeInUp 0.3s ease-out;
        }
        
        .animate-slideInRight {
          animation: slideInRight 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};

export default AdvancedRAGChat;