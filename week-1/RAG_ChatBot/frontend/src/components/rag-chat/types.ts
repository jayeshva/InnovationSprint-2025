export interface ChatMessage {
  sender: "user" | "ai";
  text: string;
  timestamp: string;
}

export interface DocumentStatus {
  document_id: string;
  filename: string;
  status: "queued" | "processing" | "completed" | "failed" | "rejected";
  message: string;
  timestamp: string;
  file_size?: number;
  chunks?: number;
  session_id?: string | null;
}
