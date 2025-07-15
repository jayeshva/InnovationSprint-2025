import { Router } from "express";
import { handleQuery } from "../controllers/queryController.js";

export const queryRouter = Router();

queryRouter.post("/", handleQuery);
