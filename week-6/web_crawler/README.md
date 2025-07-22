
# 🕷️ Web-Crawler Agent using AWS Bedrock

This project implements a Bedrock-integrated Web Crawler Agent that accepts URLs, fetches and cleans web content, and returns plain text snippets using two AWS Lambda functions.

## 🧩 Components

### 1. Lambda Functions
- `web_scrape`: Scrapes and cleans a given URL. Registered as a Bedrock Tool.
- `agent_invoker`: Accepts input from frontend and invokes Bedrock Agent Runtime.

### 2. Frontend
- Simple HTML page to test crawling via API Gateway.

### 3. Bedrock Setup (Console)
1. Create a Bedrock Agent
2. Register `web_scrape` tool pointing to the first Lambda
3. Create alias and test agent
4. Deploy `agent_invoker` and connect to frontend

## 🚀 Usage

Deploy both Lambda functions, configure environment variables for `agent_invoker`, and connect the frontend to your API Gateway.

---
