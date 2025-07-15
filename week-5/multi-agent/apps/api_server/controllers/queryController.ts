import { supportGraph } from "../../agents/graph.js";


export const handleQuery = async (req:any, res:any) => {
  try {
    const { query } = req.body;
    const result = await supportGraph.invoke({ input: query });
    res.json({ result });
  } catch (err) {
    console.error("❌ Error handling query:", err);
    res.status(500).json({ error: "Internal server error" });
  }
};
