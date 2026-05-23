import requests
import base64
import json

# Read image as base64
with open('C:/Users/15041/.openclaw/workspace/repl_test_response.png', 'rb') as f:
    img_data = f.read()
img_b64 = base64.b64encode(img_data).decode()

# Call minimax API directly
api_url = "https://api.minimaxi.com/anthropic/v1/images/parse"
# Actually minimax uses the same endpoint structure for images
# Let me try with the correct API

import os
api_key = os.environ.get('MINIMAX_API_KEY', '')
if not api_key:
    # Try to get from config
    print("No MINIMAX_API_KEY env var")

print(f"Image size: {len(img_data)} bytes, base64 length: {len(img_b64)}")
print("Image data starts with:", img_b64[:50])