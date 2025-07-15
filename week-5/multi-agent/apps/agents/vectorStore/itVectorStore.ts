import { embeddings } from "../../../config/vectorStore.js";
import { FaissStore } from "@langchain/community/vectorstores/faiss";
import { TextLoader } from "langchain/document_loaders/fs/text";
import { RecursiveCharacterTextSplitter } from "langchain/text_splitter";

const itDocsPath = "./data/it_docs";

export async function buildITVectorStore(): Promise<FaissStore> {
  const loader = new TextLoader(itDocsPath);
  const docs = await loader.load();
  const splitter = new RecursiveCharacterTextSplitter({ chunkSize: 500, chunkOverlap: 50, separators: ["\n\n", "\n", ". ", "! ", "? ", " ", ""] });
  const splitDocs = await splitter.splitDocuments(docs);
  const vectorStore = await FaissStore.fromDocuments(splitDocs, embeddings);
  await vectorStore.save("./data/embeddings/it");
  return vectorStore;
}

export async function loadITVectorStore(): Promise<FaissStore> {
  return await FaissStore.load("./data/embeddings/it", embeddings);
}