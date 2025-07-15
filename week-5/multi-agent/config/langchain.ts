import { BedrockChat } from "@langchain/community/chat_models/bedrock";

export const llm = new BedrockChat({
  region: "us-east-1",
  model: "anthropic.claude-3-sonnet-20240229-v1:0",
  temperature: 0.6,
  streaming: true,
});