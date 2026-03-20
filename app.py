from flask import Flask, request, jsonify
from flask_cors import CORS
import instaloader
import time
import os

app = Flask(__name__)
CORS(app)  # This lets your Lovable app talk to this server

BUSINESS_KEYWORDS = [
    "restaurant", "cafe", "café", "bistro", "eatery",
    "kitchen", "grill", "official", "diner", "lounge"
]

def is_influencer(post):
    username = post.owner_username.lower()
    return not any(word in username for word in BUSINESS_KEYWORDS)

# This is the URL your Lovable app will send data TO
@app.route('/scrape/instagram', methods=['POST'])
def scrape_instagram():
    data = request.json
    username  = data.get('username')
    password  = data.get('password')
    hashtags  = data.get('hashtags', [])
    limit     = data.get('limit', 20)

    L = instaloader.Instaloader()

    try:
        L.login(username, password)
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 401

    results = []

    for tag in hashtags:
        try:
            hashtag = instaloader.Hashtag.from_name(L.context, tag)
            count = 0
            for post in hashtag.get_posts():
                if count >= limit: break
                if post.typename != 'GraphVideo': continue
                if not is_influencer(post): continue
                results.append({
                    "username": post.owner_username,
                    "url": f"https://www.instagram.com/reel/{post.shortcode}/",
                    "likes": post.likes,
                    "date": str(post.date_utc.date()),
                    "caption": (post.caption or "")[:150],
                    "hashtag": f"#{tag}"
                })
                count += 1
                time.sleep(2)
        except Exception:
            continue
        time.sleep(10)

    return jsonify({"data": results, "total": len(results)})

# Health check — lets Render know the server is alive
@app.route('/')
def home():
    return jsonify({"status": "Instagram Scraper API is running! ✅"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)