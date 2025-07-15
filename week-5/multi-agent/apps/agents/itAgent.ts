import { createReactAgent, AgentExecutor } from "langchain/agents";
import { ChatPromptTemplate } from "@langchain/core/prompts";

import { buildITToolset } from "./tools/index.js";
import { llm } from "../../config/langchain.js";


const tools = buildITToolset();

const prompt = ChatPromptTemplate.fromMessages([
    ["system", "You are an assistant that uses tools to answer questions about IT. You have access to the following tools: {tools}. The available tool names are: {tool_names}. Use these tools to provide accurate and helpful responses."],
    ["human", "{input}"],
    ["ai", "I'll help you with your IT question. Let me think about this step-by-step."],
    ["ai", "{agent_scratchpad}"],
]);


const agent = await createReactAgent({
    llm,
    tools,
    prompt
});

const executor = AgentExecutor.fromAgentAndTools({
    agent,
    tools,
    verbose: true,
});

export const itAgent = async (input:String) => {
    const result = await executor.invoke({ input: input });
     console.log("Agent result:", result);
    return {response : result}

}
