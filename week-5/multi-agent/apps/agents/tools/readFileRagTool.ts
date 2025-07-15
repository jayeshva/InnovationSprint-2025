import { loadITVectorStore } from "../vectorStore/itVectorStore.js";
import { loadFinanceVectorStore } from "../vectorStore/financeVectorStore.js";

export const ITReadTool = async (query: string) => {
  const store = await loadITVectorStore();
  const retriever = store.asRetriever();
  return await retriever.invoke(query);
};

export const FinanceReadTool = async (query: string) => {
  const store = await loadFinanceVectorStore();
  const retriever = store.asRetriever();
  return await retriever.invoke(query);
};