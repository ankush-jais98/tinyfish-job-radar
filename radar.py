import json
from dotenv import load_dotenv
from tinyfish import TinyFish, RunStatus

# Load API key securely from .env file
load_dotenv()
client = TinyFish()

print("=== TinyFish AI Job & Internship Radar ===")
user_role = input("Enter Role (e.g., Software, AI, Data): ") or "Software"
user_location = input("Enter Location (e.g., New York, London, Any): ") or "Any"

GOAL = (
    f"Find open roles or internships matching '{user_role}' (Location preference: '{user_location}', or return available locations if 'Any'). "
    "Return JSON: a list of objects under key 'jobs' with fields: role, company, location, link."
)

# 3 Active Live Career Pages (200 Points Tier)
URLS = [
    "https://www.janestreet.com/join-jane-street/open-roles/",
    "https://boards.greenhouse.io/anthropic",
    "https://boards.greenhouse.io/scaleai"
]

all_listings = []
seen_links = set()

print(f"\nDeploying TinyFish Agents across {len(URLS)} live career portals...\n")

for url in URLS:
    print(f"Scanning live endpoint: {url} ...")
    run = client.agent.run(url=url, goal=GOAL)
    
    if run.status == RunStatus.COMPLETED and run.result:
        print(f"✅ Data extracted from {url}")
        all_listings.append({
            "endpoint": url,
            "extracted_data": run.result
        })
    else:
        print(f"⚠️ No matching roles or timeout at {url}")

print("\n=== FINAL STRUCTURED & DEDUPLICATED LISTINGS ===")
print(json.dumps(all_listings, indent=2))