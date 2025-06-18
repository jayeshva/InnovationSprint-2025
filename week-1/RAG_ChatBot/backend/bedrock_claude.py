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
    # Insert the strict instruction into the first user message as a prefix
        instruction_prefix = (
    "You are a helpful assistant. Prioritize answering using the provided document context. "
    "Mention that the answer is based on the context only **if it helps the user understand the source** of the information. "
    "Avoid repeating the phrase unless it's necessary for clarity. "
    "If the answer isn't in the context and no relevant background helps, reply with:\n"
    "\"I'm unable to answer this question based on the available documents.\"\n\n"
)

    # Prepend the instruction to the first user message
        full_messages = messages.copy()
        if full_messages and full_messages[0]["role"] == "user":
          full_messages[0]["content"] = instruction_prefix + full_messages[0]["content"]
        else:
         full_messages.insert(0, {
            "role": "user",
            "content": instruction_prefix
        })

        body = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": full_messages,
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
