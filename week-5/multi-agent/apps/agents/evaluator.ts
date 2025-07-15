import { llm } from "../../config/langchain.js";
import { evaluationPrompt } from "./prompts.js";

export async function evaluatorNode({ input, state }: { input: string; state: any }) {
  const { userQuery, agentResponse, currentAgent } = state;

  const prompt = await evaluationPrompt.format({ query: userQuery, response: agentResponse });
  const result = await llm.invoke([{ role: "user", content: prompt }]);

  const verdict = result.content?.toString().trim().toUpperCase();

  if (verdict === "YES") {
  return { next: "end" }; 
}
   return { next: "retry" }; 

}
