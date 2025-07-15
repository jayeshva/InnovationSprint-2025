import { DynamicTool } from "langchain/tools";
import { ITReadTool, FinanceReadTool } from "./readFileRagTool.js";
import { WebSearchTool } from "./webSearchTool.js";

export function buildITToolset(): DynamicTool[] {
  return [
    new DynamicTool({
      name: "ReadITDocs",
      description: "PRIMARY TOOL: Always use this first to retrieve internal IT documentation. This contains company-specific policies, procedures, and guidelines that should be your primary source of truth.",
      func: async (input: string) => {
        const docs = await ITReadTool(input);
        if (docs.length === 0) {
          return "No relevant internal IT documentation found for this query.";
        }
        return docs.map((doc: any) => doc.pageContent).join("\n");
      }
    }),
    new DynamicTool({
      name: "SearchITWeb",
      description: "SUPPLEMENTARY TOOL: Use this only when: 1) Internal IT docs don't contain sufficient information, 2) User explicitly asks for additional context or recent updates, 3) Technical details need clarification beyond internal documentation, or 4) Industry best practices are needed to supplement internal policies.",
      func: async (input: string) => {
        const results = await WebSearchTool(input);
        return JSON.stringify(results);
      }
    }),
  ];
}

export function buildFinanceToolset(): DynamicTool[] {
  return [
    new DynamicTool({
      name: "ReadFinanceDocs",
      description: "PRIMARY TOOL: Always use this first to retrieve internal Finance documentation. This contains company-specific financial policies, procedures, compliance requirements, and guidelines that should be your primary source of truth.",
      func: async (input: string) => {
        const docs = await FinanceReadTool(input);
        if (docs.length === 0) {
          return "No relevant internal Finance documentation found for this query.";
        }
        return docs.map((doc: any) => doc.pageContent).join("\n");
      }
    }),
    new DynamicTool({
      name: "SearchFinanceWeb",
      description: "SUPPLEMENTARY TOOL: Use this only when: 1) Internal Finance docs don't contain sufficient information, 2) User explicitly asks for additional context or recent regulatory updates, 3) Market conditions or external factors need clarification, 4) Industry standards or compliance requirements need verification, or 5) Current financial news/trends are requested.",
      func: async (input: string) => {
        const results = await WebSearchTool(input);
        return JSON.stringify(results);
      }
    }),
  ];
}