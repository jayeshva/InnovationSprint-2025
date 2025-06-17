import boto3
import os
import json

class BedrockClaudeClient:
    def __init__(self):
        self.region = os.getenv("AWS_REGION")
        self.model_id = os.getenv("BEDROCK_MODEL_ID")
        
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=self.region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )

    def chat(self, messages, temperature=0.6, max_tokens=1024):
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json"
        )
        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]
