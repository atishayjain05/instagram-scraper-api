from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# ── Read API credentials from environment variables (safe & secret) ──
RAPIDAPI_KEY  = os.environ.get("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.environ.get("RAPIDAPI_HOST", "instagram-scraper-api2.p.rapidapi.com")

# Words that suggest the poster is a business, not an influencer
BUSINESS_KEYWORDS = [
    "restaurant", "cafe", "café", "bistro", "eatery",
    "kitchen", "grill", "official", "diner", "lounge",
    "hotel", "foods", "eats"
]

def is_influencer(username, caption):
    u = username.lower()
    return not any(w in u for w in BUSINESS_KEYWORDS)

def scrape_hashtag(tag, limit):
    """Calls RapidAPI to fetch recent posts for a hashtag"""
    url = f"https://{RAPIDAPI_HOST}/v1/hashtag"

    headers = {
        "X-RapidAPI-Key":  RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {"hashtag": tag}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"RapidAPI error for #{tag}: {e}")
        return []

    # Navigate the response — structure varies slightly by API version
    posts_raw = (
        data.get("data", {}).get("hashtag", {}).get("edge_hashtag_to_media", {}).get("edges", [])
        or data.get("result", {}).get("data", [])
        or data.get("data", [])
        or []
    )

    results = []
    for edge in posts_raw[:limit * 3]:  # grab extra to account for filtering
        node = edge.get("node", edge) if "node" in edge else edge

        # Only keep video posts (Reels)
        if not node.get("is_video", False):
            continue

        owner    = node.get("owner", {})
        username = owner.get("username", "unknown")
        shortcode = node.get("shortcode", "")
        caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
        caption  = caption_edges[0]["node"]["text"] if caption_edges else ""
        likes    = node.get("edge_liked_by", {}).get("count", 0)
        taken_at = node.get("taken_at_timestamp", "")

        # Convert timestamp to readable date
        try:
            from datetime import datetime
            date_str = datetime.utcfromtimestamp(int(taken_at)).strftime("%Y-%m-%d")
        except:
            date_str = "unknown"

        if not is_influencer(username, caption):
            continue

        results.append({
            "username": username,
            "url": f"https://www.instagram.com/reel/{shortcode}/",
            "likes": likes,
            "date": date_str,
            "caption": caption[:150],
            "hashtag": f"#{tag}"
        })

        if len(results) >= limit:
            break

    return results


# ── Main scraping endpoint ─────────────────────────────────────────
@app.route("/scrape/instagram", methods=["POST"])
def scrape_instagram():
    if not RAPIDAPI_KEY:
        return jsonify({"error": "API key not configured on server"}), 500

    body     = request.get_json() or {}
    hashtags = body.get("hashtags", [])
    limit    = int(body.get("limit", 20))

    if not hashtags:
        return jsonify({"error": "No hashtags provided"}), 400

    all_results = []
    for tag in hashtags:
        tag = tag.strip().lstrip("#")
        if tag:
            results = scrape_hashtag(tag, limit)
            all_results.extend(results)

    return jsonify({
        "data": all_results,
        "total": len(all_results)
    })


# ── Health check ──────────────────────────────────────────────────
@app.route("/")
def home():
    return jsonify({"status": "✅ Instagram Scraper API (RapidAPI) is running!"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
