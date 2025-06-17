/**
 * API base URL for backend communication
 */
export const API_BASE_URL = "http://localhost:8000";

/**
 * Maximum file size for document uploads (in bytes)
 * 10MB = 10 * 1024 * 1024
 */
export const MAX_FILE_SIZE = 10 * 1024 * 1024;

/**
 * Supported file types for document uploads
 */
export const SUPPORTED_FILE_TYPES = [".pdf", ".docx", ".txt"];

/**
 * Local storage keys
 */
export const STORAGE_KEYS = {
  CHAT_HISTORY: "chatHistory",
  SESSION_ID: "chatSessionId"
};

/**
 * Document status polling interval (in milliseconds)
 */
export const DOCUMENT_STATUS_POLLING_INTERVAL = 2000;
