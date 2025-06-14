import React, { useState, useRef } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Upload, Trash2, Sparkles, Send } from "lucide-react";
import { motion } from "framer-motion";

export default function RagChatPage() {
  const [files, setFiles] = useState([]);
  const [filePreviews, setFilePreviews] = useState([]);
  const [chatHistory, setChatHistory] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef();

  // Fetch file list on load (optional)
  React.useEffect(() => {
    fetchFiles();
  }, []);

  async function fetchFiles() {
    const res = await fetch("http://localhost:8000/files/");
    const data = await res.json();
    setFiles(data.files || []);
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setLoading(true);
    await fetch("http://localhost:8000/upload/", {
      method: "POST",
      body: formData,
    });
    setLoading(false);
    fetchFiles();
    // Preview
    const text = await file.text();
    setFilePreviews((prev) => [...prev, { name: file.name, text: text.slice(0, 2000) + (text.length > 2000 ? "..." : "") }]);
  };

  const handleFileDelete = async (filename) => {
    setLoading(true);
    await fetch(`http://localhost:8000/files/${filename}`, { method: "DELETE" });
    setLoading(false);
    fetchFiles();
    setFilePreviews((prev) => prev.filter((f) => f.name !== filename));
  };

  const handleAssist = async () => {
    // re-chunk and upload all files again (or just simulate for now)
    fetchFiles();
  };

  const handleSend = async () => {
    if (!input) return;
    setLoading(true);
    setChatHistory((h) => [...h, { sender: "user", text: input }]);
    const res = await fetch("http://localhost:8000/chat/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_message: input }),
    });
    const data = await res.json();
    setChatHistory((h) => [...h, { sender: "ai", text: data.answer }]);
    setInput("");
    setLoading(false);
  };

  return (
    <div className="w-full h-screen bg-gray-50 flex overflow-hidden">
      {/* LEFT SIDEBAR */}
      <motion.div
        initial={{ x: -80, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ type: "spring", stiffness: 50, damping: 10 }}
        className="w-1/3 min-w-[340px] bg-white shadow-xl border-r flex flex-col p-4 gap-4"
      >
        <h2 className="text-xl font-bold mb-2">📄 My Documents</h2>
        <div>
          <Button
            className="w-full flex items-center gap-2"
            onClick={() => fileInputRef.current.click()}
            variant="outline"
          >
            <Upload size={18} /> Upload File
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".txt,.md,.pdf"
            onChange={handleFileUpload}
          />
        </div>
        <div className="flex flex-col gap-2">
          {files.map((fname, idx) => (
            <Card key={fname} className="flex items-center gap-2 p-2 justify-between group">
              <div>
                <div className="font-semibold">{fname}</div>
                <pre className="max-h-[80px] overflow-y-auto text-xs text-gray-600 bg-gray-50 mt-1 rounded">{(filePreviews.find(f => f.name === fname) || {}).text}</pre>
              </div>
              <Button
                size="icon"
                variant="ghost"
                className="opacity-60 hover:opacity-100"
                onClick={() => handleFileDelete(fname)}
              >
                <Trash2 size={18} />
              </Button>
            </Card>
          ))}
        </div>
        <Button className="mt-4 flex gap-2 items-center" onClick={handleAssist} disabled={loading}>
          <Sparkles size={18} /> Assist (Process & Chunk)
        </Button>
      </motion.div>

      {/* RIGHT CHAT */}
      <div className="flex-1 flex flex-col h-full">
        <div className="flex-1 overflow-y-auto p-8 flex flex-col gap-4 bg-gradient-to-br from-slate-100 to-white">
          {chatHistory.map((msg, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              className={`max-w-2xl ${msg.sender === "user" ? "self-end bg-blue-100 text-blue-800" : "self-start bg-white text-gray-900"} rounded-2xl shadow p-4`}
            >
              {msg.text}
            </motion.div>
          ))}
          {loading && <div className="animate-pulse self-start text-gray-500">AI is typing…</div>}
        </div>
        <div className="p-4 border-t flex gap-2 bg-white">
          <Textarea
            className="flex-1 rounded-xl shadow resize-none"
            placeholder="Type your question..."
            value={input}
            minRows={1}
            maxRows={4}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <Button onClick={handleSend} className="rounded-full h-12 w-12 p-0" disabled={loading || !input}>
            <Send size={22} />
          </Button>
        </div>
      </div>
    </div>
  );
}
