from flask import Flask, request, jsonify, render_template
import json
import os
from dotenv import load_dotenv
from tinyfish import TinyFish, RunStatus

# Load API key securely
load_dotenv()
client = TinyFish()

app = Flask(__name__)

URLS = [
    "https://www.janestreet.com/join-jane-street/open-roles/",
    "https://boards.greenhouse.io/anthropic",
    "https://boards.greenhouse.io/scaleai"
]

@app.route('/')
def index():
    
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    user_role = data.get('role', 'ui/ux') # Default ui/ux
    user_location = data.get('location', 'Any')

    GOAL = (
        f"Find open roles matching '{user_role}' in '{user_location}'. "
        "Return JSON with fields: role, company, location, link."
    )

    all_listings = []
    for url in URLS:
        try:
            run = client.agent.run(url=url, goal=GOAL)
            if run.status == RunStatus.COMPLETED and run.result:
                all_listings.append({
                    "endpoint": url,
                    "extracted_data": run.result
                })
        except Exception as e:
            pass
            
    return jsonify(all_listings)

if __name__ == '__main__':
    app.run(debug=True, port=5000)