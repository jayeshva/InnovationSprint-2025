import json
import requests
from bs4 import BeautifulSoup
import gzip
import io
from urllib.parse import urlparse

def lambda_handler(event, context):
    try:
        # Extract URL from request body
        body = event.get("body")
        if isinstance(body, str):
            body = json.loads(body)
        url = event.get("url") or (body or {}).get("url")

        # Validate presence of URL
        if not url:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing URL"})
            }

        # Validate URL format
        parsed_url = urlparse(url)
        if not (parsed_url.scheme in ("http", "https") and parsed_url.netloc):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid URL format"})
            }

        # Fetch the URL with safety checks
        headers = {"User-Agent": "WebCrawlerAgent/1.0"}
        resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True, stream=True)

        # Limit download size (1MB)
        MAX_BYTES = 1024 * 1024  # 1 MB
        content = resp.raw.read(MAX_BYTES, decode_content=True)

        # Check status
        if resp.status_code != 200:
            return {
                "statusCode": resp.status_code,
                "body": json.dumps({"error": f"Failed to fetch URL: {url}"})
            }

        # Decode content (handle gzip manually if needed)
        if resp.headers.get('Content-Encoding') == 'gzip':
            buf = io.BytesIO(content)
            f = gzip.GzipFile(fileobj=buf)
            html = f.read().decode(resp.encoding or 'utf-8', errors='replace')
        else:
            html = content.decode(resp.encoding or 'utf-8', errors='replace')

        # Clean HTML using BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Remove scripts/styles/noscript tags
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()

        # Get clean text
        text = soup.get_text(separator=" ", strip=True)

        # Limit snippet to 3000 characters
        snippet = text[:3000] + "..." if len(text) > 3000 else text

        return {
            "statusCode": 200,
            "body": json.dumps({"text": snippet})
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
