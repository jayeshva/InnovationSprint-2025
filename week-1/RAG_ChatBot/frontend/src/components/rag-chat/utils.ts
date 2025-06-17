import type { DocumentStatus } from './types';

/**
 * Get the appropriate status icon for a document based on its status
 */
export const getStatusLabel = (status: string): string => {
  switch (status) {
    case "completed":
      return "Completed";
    case "processing":
      return "Processing";
    case "queued":
      return "Queued";
    case "failed":
      return "Failed";
    case "rejected":
      return "Rejected";
    default:
      return "Unknown";
  }
};

/**
 * Format a filename for display by removing UUID prefix
 */
export const formatFilename = (filename: string): string => {
  if (!filename) return 'Unnamed Document';
  
  // If the filename contains an underscore (from UUID prefix), get the part after the last underscore
  if (filename.includes('_')) {
    return filename.split('_').pop() || filename;
  }
  
  return filename;
};

/**
 * Filter documents by session ID
 */
export const filterDocumentsBySession = (
  documents: DocumentStatus[],
  sessionId: string | null
): DocumentStatus[] => {
  if (!sessionId) return documents;
  return documents.filter(doc => doc.session_id === sessionId);
};
