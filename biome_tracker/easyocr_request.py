import requests
import io

# URLs
image_url = "https://i.postimg.cc/FKtqPgBg/teleporter.png"
#api_url = "https://api.easyocr.org/ocr"
# Optional fallback if the main one is down: 
api_url = "https://cn-api.easyocr.org/ocr"

print("Downloading image from URL...")
image_response = requests.get(image_url)

if image_response.status_code == 200:
    # Treat the downloaded bytes as a file object
    image_bytes = io.BytesIO(image_response.content)
    files = {'file': ('teleporter.png', image_bytes, 'image/png')}
    
    # Adding a User-Agent helps bypass some basic Cloudflare bot blocks
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print("Sending image to EasyOCR API...")
    try:
        response = requests.post(api_url, files=files, headers=headers)
        if response.status_code == 200:
            result = response.json()
            print("\n--- Extracted Text ---")
            print(result.get('words', 'No words found.'))
        else:
            print(f"\nAPI Error: Received status code {response.status_code}")
            print("Response details:", response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
else:
    print(f"Failed to download the image. Status code: {image_response.status_code}")