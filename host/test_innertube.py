import re
import json
import urllib.request
import urllib.error
import time

def extract_html_formats(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    })
    
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8")
    except Exception as e:
        print(f"Error fetching HTML: {e}")
        return
    
    print(f"Fetch time: {time.time() - t0:.2f}s")
    
    # Extract ytInitialPlayerResponse
    match = re.search(r'var ytInitialPlayerResponse\s*=\s*({.+?});var', html)
    if not match:
        match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?})\s*</script>', html)
    
    if match:
        try:
            data = json.loads(match.group(1))
            ad = data.get("streamingData", {}).get("adaptiveFormats", [])
            print(f"Found {len(ad)} adaptive formats")
            max_h = max([f.get("height", 0) for f in ad] + [0])
            print(f"Max Height: {max_h}")
        except Exception as e:
            print(f"JSON Parse error: {e}")
    else:
        print("ytInitialPlayerResponse not found")

extract_html_formats("LXb3EKWsInQ")
