import express from "express";
import { queryRouter } from "./routes/queryRouter.js";

const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());
app.use("/query", queryRouter);

app.listen(port, () => {
  console.log(`🚀 API Server running at http://localhost:${port}`);
});
