import { StateGraph, END, Annotation } from "@langchain/langgraph";
import { supervisorNode } from "./supervisorAgent.js";
import { itAgent } from "./itAgent.js";
import { financeAgent } from "./financeAgent.js";
import { generalAgentNode } from "./generalAgent.js";
import { evaluatorNode } from "./evaluator.js";


// Define state using modern Annotation API
const GraphState = Annotation.Root({
    userQuery: Annotation<string>({ reducer: (x, y) => y ?? x, default: () => "" }),
    agentResponse: Annotation<string>({ reducer: (x, y) => y ?? x, default: () => "" }),
    currentAgent: Annotation<string>({ reducer: (x, y) => y ?? x, default: () => "" }),
    next: Annotation<string>({ reducer: (x, y) => y ?? x, default: () => "" }),
    input: Annotation<string>({ reducer: (x, y) => y ?? x, default: () => "" }),
});

// Route to agent after supervisor classifies
const routeToAgent = (state: typeof GraphState.State): string => {
    switch (state.next) {
        case "itAgent":
            return "itAgent";
        case "financeAgent":
            return "financeAgent";
        case "generalAgent":
            return "generalAgent";
        default:
            return "generalAgent";
    }
};

export const supportGraph = new StateGraph(GraphState)
    .addNode("supervisor", supervisorNode)

    .addNode("itAgent", async (state) => {
        const result = await itAgent((state.input || state.userQuery).toString());
        return {
            ...state,
            agentResponse: result.response,
            currentAgent: "itAgent",
            next: "evaluate",
        };
    })

    .addNode("financeAgent", async (state) => {
        const result = await financeAgent( (state.input || state.userQuery).toString() );
        return {
            ...state,
            agentResponse: result.response,
            currentAgent: "financeAgent",
            next: "evaluate",
        };
    })

    .addNode("generalAgent", async (state) => {
        const result = await generalAgentNode({ input: state.input || state.userQuery });
        return {
            ...state,
            agentResponse: result.response,
            currentAgent: "generalAgent",
            next: "evaluate",
        };
    })

    .addNode("evaluate", async (state) => {
        const result = await evaluatorNode({
            input: state.agentResponse,
            state,
        });

        return {
            ...state,
            next: result.next === "retry" ? "retry" : END,
        };
    })

    .addConditionalEdges("supervisor", routeToAgent, {
        itAgent: "itAgent",
        financeAgent: "financeAgent",
        generalAgent: "generalAgent",
    })

    .addEdge("itAgent", "evaluate")
    .addEdge("financeAgent", "evaluate")
    .addEdge("generalAgent", "evaluate")

    .addConditionalEdges("evaluate", (state) => {
        return state.next === "retry" ? state.currentAgent : END;
    }, {
        itAgent: "itAgent",
        financeAgent: "financeAgent",
        generalAgent: "generalAgent",
        [END]: END,
    })
    .setEntryPoint("supervisor")
    .compile();


export async function runSupportAgent(query: string) {
  const result = await supportGraph.invoke({
    userQuery: query,
    input: query, 
  });

  console.log("✅ Final Output:", result);
  return result;
}
