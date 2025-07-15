import { llm } from "../../config/langchain.js";

export async function generalAgentNode({ input }: { input: string }) {
  const prompt = [
    {
      role: "system",
      content: "You are a friendly assistant who answers greetings, small talk, and general help requests.",
    },
    {
      role: "user",
      content: input,
    },
  ];

  const response = await llm.invoke(prompt);

  return {
    next: "end",
    response: response.content,
  };
}
