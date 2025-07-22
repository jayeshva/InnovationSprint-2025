
import json
import boto3
import os

AGENT_ID = os.environ["AGENT_ID"]
AGENT_ALIAS_ID = os.environ["AGENT_ALIAS_ID"]
REGION = os.environ.get("AWS_REGION", "us-east-1")

client = boto3.client("bedrock-agent-runtime", region_name=REGION)

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body", "{}"))
        query = body.get("query")
        if not query:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing user query"})}

        response = client.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId="web-crawl-session",
            inputText=f"{query}"
        )

        completion = response["completion"]["text"]

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"text": completion})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
