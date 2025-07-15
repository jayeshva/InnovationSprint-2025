import { embeddings } from "../../../config/vectorStore.js";
import { FaissStore } from "@langchain/community/vectorstores/faiss";
import { TextLoader } from "langchain/document_loaders/fs/text";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";

const financeDocsPath = "./data/finance_docs";

export async function buildFinanceVectorStore(): Promise<FaissStore> {
  const loader = new TextLoader(financeDocsPath);
  const docs = await loader.load();
  const splitter = new RecursiveCharacterTextSplitter({ chunkSize: 500, chunkOverlap: 50, separators: ["\n\n", "\n", ". ", "! ", "? ", " ", ""] });
  const splitDocs = await splitter.splitDocuments(docs);
  const vectorStore = await FaissStore.fromDocuments(splitDocs, embeddings);
  await vectorStore.save("./data/embeddings/finance");
  return vectorStore;
}

export async function loadFinanceVectorStore(): Promise<FaissStore> {
  return await FaissStore.load("./data/embeddings/finance", embeddings);
}