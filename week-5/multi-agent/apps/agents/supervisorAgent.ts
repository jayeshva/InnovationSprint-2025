import { llm } from "../../config/langchain.js";
import {classificationPrompt} from "./prompts.js";

export async function supervisorNode({ input }: { input: string }) {
    const prompt = await classificationPrompt.format({ query: input });
    const response = await llm.invoke([{ role: "user", content: prompt }]);

    const classification = response.content;
    console.log("super Visior", classification)
    if (classification === "IT") return { next: "itAgent", input };
    if (classification === "Finance") return { next: "financeAgent", input };
    if (classification === "General") return { next: "generalAgent", input };
    return { next: "end", input: "Could not classify query." };
}