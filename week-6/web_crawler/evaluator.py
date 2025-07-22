import requests
import json
import os

# Load environment variables
API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL")
USER_QUERY = "Crawl and Summarise www.instagram.com"

if not API_GATEWAY_URL:
    print("❌ Please set API_GATEWAY_URL environment variable.")
    exit(1)

# Make the POST request to your API Gateway
response = requests.post(
    API_GATEWAY_URL,
    headers={"Content-Type": "application/json"},
    data=json.dumps({"query": USER_QUERY})
)

# Handle response
if response.status_code == 200:
    result = response.json()
    print("✅ Crawled Response:\n")
    print(result["text"])
else:
    print("❌ Error:", response.status_code)
    print(response.text)
