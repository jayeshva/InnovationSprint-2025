import { TavilySearchAPIRetriever } from "@langchain/community/retrievers/tavily_search_api";

const retriever = new TavilySearchAPIRetriever({
  k: 5,
  apiKey: process.env.TAVILY_API_KEY
});


export const WebSearchTool = async (query: string) => {
  await retriever.invoke(query)
};