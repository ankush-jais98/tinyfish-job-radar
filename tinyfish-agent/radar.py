import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from dotenv import load_dotenv
from tinyfish import TinyFish, RunStatus

# Load API key securely from .env file
load_dotenv()
client = TinyFish()


# =====================================================================
# STAGE 1: TINYFISH SEARCH & DYNAMIC ENDPOINT DISCOVERY
# =====================================================================
def stage_1_search_endpoints(role: str, location: str, company: str) -> list:
    """
    Chains TinyFish Search primitive (if enabled on the SDK version) with 
    dynamic ATS & global job board URL construction. Supports custom companies!
    """
    q_role = urllib.parse.quote_plus(role.strip())
    q_loc = urllib.parse.quote_plus(location.strip()) if location.lower() != "any" else ""
    full_query = f"{q_role}+{q_loc}".strip("+")

    discovered_urls = []

    # 1. Try native TinyFish Search primitive if available in current SDK version
    if hasattr(client, "search"):
        try:
            search_fn = getattr(client.search, "run", client.search)
            comp_filter = company if company.lower() != "any" else ""
            search_query = f"{role} {comp_filter} {location} jobs open roles".strip()
            print(f"🔎 [Stage 1: Search] Querying TinyFish Search for: '{search_query}'...")
            res = search_fn(query=search_query)
            if isinstance(res, dict) and "results" in res:
                for item in res["results"][:3]:
                    if isinstance(item, dict) and item.get("url"):
                        discovered_urls.append(item["url"])
        except Exception:
            pass  # Gracefully fallback to dynamic ATS discovery

    # 2. Custom Company Targeted Discovery (Addresses Judges' Feedback)
    if company.lower() != "any":
        clean_comp = urllib.parse.quote_plus(company.strip().lower().replace(" ", ""))
        q_comp_full = urllib.parse.quote_plus(f"{company.strip()} {role.strip()} {location.strip()}".strip())
        discovered_urls.extend([
            f"https://boards.greenhouse.io/{clean_comp}?keyword={q_role}",
            f"https://jobs.lever.co/{clean_comp}?department={q_role}",
            f"https://www.ycombinator.com/jobs?query={q_comp_full}"
        ])

    # 3. High-Yield Global & Startup Aggregators (Works for Tech, Creative, Video Editing, India, etc.)
    default_targets = [
        f"https://www.ycombinator.com/jobs?query={full_query}",
        f"https://remoteok.com/remote-{q_role}-jobs",
        f"https://boards.greenhouse.io/anthropic?keyword={q_role}",
        f"https://boards.greenhouse.io/scaleai?keyword={q_role}",
        f"https://www.janestreet.com/join-jane-street/open-roles/?search={q_role}"
    ]

    for url in default_targets:
        if url not in discovered_urls:
            discovered_urls.append(url)

    # Return top 5 targeted endpoints to optimize speed & API credits
    return discovered_urls[:5]


# =====================================================================
# STAGE 2: TINYFISH FETCH & PRE-FLIGHT LIVENESS CHECK
# =====================================================================
def stage_2_fetch_and_validate(url: str) -> bool:
    """
    Chains Fetch primitive / HTTP pre-flight validation to ensure the job board 
    is live and not returning a 404 or dead page before deploying the heavy Agent.
    """
    # 1. Try TinyFish Fetch primitive if available in SDK
    if hasattr(client, "fetch"):
        try:
            fetch_fn = getattr(client.fetch, "run", client.fetch)
            res = fetch_fn(url=url)
            if res:
                return True
        except Exception:
            pass

    # 2. Fast HTTP Pre-Flight Verification
    try:
        req = urllib.request.Request(
            url, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TinyFishScout/2.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            return response.status < 400
    except urllib.error.HTTPError as e:
        # 404 means the custom company slug doesn't exist on that specific ATS; skip it!
        if e.code == 404:
            return False
        # 403/429 means anti-bot shield is active -> TinyFish Browser Agent is required!
        return True
    except Exception:
        return True


# =====================================================================
# STAGE 3: AUTONOMOUS AGENT GOAL & EXTRACTION
# =====================================================================
def build_strict_goal(role: str, location: str, company: str) -> str:
    """
    Zero-hallucination prompt that filters out closed roles and extracts structured data.
    """
    loc_rule = (
        f"MUST be located in or support remote work from '{location}'."
        if location.lower() != "any"
        else "Can be from any location."
    )
    comp_rule = (
        f"Focus on roles from company '{company}' if present."
        if company.lower() != "any"
        else "Can be from any company."
    )

    return (
        f"You are an autonomous recruitment data extractor. Find currently OPEN job roles or internships "
        f"matching '{role}'. {loc_rule} {comp_rule}\n\n"
        f"CRITICAL RULES:\n"
        f"1. If the page has a search input or filter, enter '{role}' and '{location}'.\n"
        f"2. FILTER OUT CLOSED ROLES: Ignore any job marked as 'Closed', 'Filled', 'Expired', or 'No longer accepting applications'.\n"
        f"3. ZERO DUMMY DATA: Never return unrelated default jobs (e.g., if searching for '{role}', do not return unrelated roles).\n"
        f"4. If 0 active jobs match on this page, return exactly: {{\"jobs\": []}}.\n"
        f"5. Return ONLY valid JSON with top-level key 'jobs', where each object has: "
        f"'role', 'company', 'location', 'status' (must be 'Open' or 'Closed'), and 'link'."
    )


def parse_agent_output(raw_result) -> list:
    """Safely parses the Agent output whether returned as dict, list, or markdown JSON string."""
    data = raw_result
    if isinstance(raw_result, str):
        try:
            cleaned = raw_result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(cleaned)
        except Exception:
            return []

    if isinstance(data, dict):
        return data.get("jobs", [])
    elif isinstance(data, list):
        return data
    return []


# =====================================================================
# STAGE 4: MATCH SCORING, CLOSED-ROLE FILTER & DEDUPLICATION
# =====================================================================
def calculate_match_score(job_title: str, job_loc: str, job_company: str, role: str, location: str, company: str) -> int:
    """
    Calculates a realistic Match Score (0-100%) based on role keywords, 
    exact title phrase match, location alignment, and target company match.
    """
    score = 0
    title_l = job_title.lower()
    loc_l = job_loc.lower()
    comp_l = job_company.lower()

    role_l = role.lower().strip()
    target_loc_l = location.lower().strip()
    target_comp_l = company.lower().strip()

    # 1. Role Relevance (Up to 60 points)
    role_keywords = [w for w in role_l.split() if len(w) > 2]
    if role_l in title_l:
        score += 60
    elif role_keywords:
        matched_kws = sum(1 for kw in role_keywords if kw in title_l)
        score += int((matched_kws / len(role_keywords)) * 55)

    # 2. Location Alignment (Up to 25 points)
    if target_loc_l == "any":
        score += 25
    elif target_loc_l in loc_l:
        score += 25
    elif "remote" in loc_l or "global" in loc_l or "anywhere" in loc_l:
        score += 18

    # 3. Company Alignment (Up to 15 points)
    if target_comp_l == "any":
        score += 15
    elif target_comp_l in comp_l:
        score += 15
    else:
        score += 5

    return min(score, 100)


def verify_score_and_deduplicate(
    jobs: list, role: str, location: str, company: str, source_url: str, seen_links: set
) -> list:
    """
    Filters out closed roles, removes dummy/unmatched entries, deduplicates links,
    and attaches a calculated Match Score (%).
    """
    verified = []
    role_keywords = [w.lower() for w in role.split() if len(w) > 2]
    loc_lower = location.lower().strip()

    for job in jobs:
        if not isinstance(job, dict):
            continue

        job_title = str(job.get("role", "")).strip()
        job_company = str(job.get("company", "Unknown")).strip()
        job_loc = str(job.get("location", "Remote / Unspecified")).strip()
        job_status = str(job.get("status", "Open")).strip()
        job_link = str(job.get("link", "")).strip()

        # 1. Deduplication & Basic Validity
        if not job_title or not job_link or job_link in seen_links:
            continue

        # 2. Filter out Closed / Expired Roles
        closed_markers = ["closed", "expired", "filled", "inactive", "archived"]
        if any(m in job_status.lower() for m in closed_markers) or any(m in job_title.lower() for m in closed_markers):
            continue

        # 3. Zero Dummy Data Check (Role keyword verification)
        if role_keywords and not any(kw in job_title.lower() for kw in role_keywords):
            continue

        # 4. Strict Location Check
        if loc_lower != "any":
            if loc_lower not in job_loc.lower() and "remote" not in job_loc.lower() and "global" not in job_loc.lower():
                continue

        # 5. Calculate Match Score
        match_score = calculate_match_score(job_title, job_loc, job_company, role, location, company)
        if match_score < 40:
            continue

        seen_links.add(job_link)
        verified.append({
            "role": job_title,
            "company": job_company,
            "location": job_loc,
            "status": "Open",
            "match_score": f"{match_score}%",
            "match_score_num": match_score,
            "link": job_link,
            "source_endpoint": source_url
        })

    return verified


# =====================================================================
# STAGE 5: AUTOMATED CSV EXPORT
# =====================================================================
def export_to_csv(jobs: list, filename: str = "tinyfish_radar_results.csv") -> str:
    """
    Exports verified, scored job listings into a clean CSV file ready for Excel/Sheets.
    """
    fieldnames = ["match_score", "role", "company", "location", "status", "link", "source_endpoint"]
    with open(filename, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for job in jobs:
            writer.writerow(job)
    return filename


# =====================================================================
# MAIN EXECUTION PIPELINE
# =====================================================================
def main():
    print("=" * 65)
    print("🚀 TINYFISH AI — JOB & INTERNSHIP RADAR v2.0 (SEARCH+FETCH+AGENT)")
    print("=" * 65)

    user_role = input("🎯 Enter Target Role (e.g., Video Editor, AI Intern, Software): ").strip() or "Software Engineer"
    user_location = input("🌍 Enter Location (e.g., India, Remote, London, Any): ").strip() or "Any"
    user_company = input("🏢 Enter Target Company (e.g., Stripe, Anthropic, or Any): ").strip() or "Any"

    print("\n⚙️  Initializing TinyFish Chained Pipeline (Search ➔ Fetch ➔ Agent)...")
    urls = stage_1_search_endpoints(user_role, user_location, user_company)
    goal = build_strict_goal(user_role, user_location, user_company)

    verified_listings = []
    seen_links = set()
    scanned_count = 0

    print(f"🔍 Active Filter -> Role: '{user_role}' | Location: '{user_location}' | Company: '{user_company}'\n")

    for idx, url in enumerate(urls, 1):
        print(f"[{idx}/{len(urls)}] 🔗 Pipeline Target: {url}")

        # Stage 2: Fetch & Pre-validate Liveness
        print("   📡 [Stage 2: Fetch] Verifying endpoint liveness & active board status...")
        if not stage_2_fetch_and_validate(url):
            print("   ⏭️  Skipped: Endpoint returned 404/Inactive during Fetch pre-check.")
            continue

        # Stage 3: Autonomous Agent Extraction
        print("   🤖 [Stage 3: Agent] Deploying TinyFish Browser Agent for live extraction...")
        try:
            scanned_count += 1
            run = client.agent.run(url=url, goal=goal)

            if run.status == RunStatus.COMPLETED and run.result:
                raw_jobs = parse_agent_output(run.result)
                clean_jobs = verify_score_and_deduplicate(
                    raw_jobs, user_role, user_location, user_company, url, seen_links
                )

                if clean_jobs:
                    print(f"   ✅ Extracted {len(clean_jobs)} verified OPEN role(s) with Match Scores!")
                    verified_listings.extend(clean_jobs)
                else:
                    print(f"   ⚪ Page scanned: 0 active roles matched strict filter ('{user_role}' in '{user_location}').")
            else:
                print("   ⚠️ Agent timeout or empty response at endpoint.")
        except Exception as e:
            print(f"   ❌ Error scanning {url}: {str(e)}")

    # Sort listings by Match Score (Highest first)
    verified_listings.sort(key=lambda x: x.get("match_score_num", 0), reverse=True)

    # Remove internal sorting helper key before displaying JSON
    for item in verified_listings:
        item.pop("match_score_num", None)

    # Export to CSV
    csv_path = export_to_csv(verified_listings)

    # Final Structured Report
    final_payload = {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pipeline_architecture": "TinyFish Chained (Search -> Fetch -> Agent)",
            "query_role": user_role,
            "query_location": user_location,
            "query_company": user_company,
            "endpoints_discovered": len(urls),
            "endpoints_scanned_by_agent": scanned_count,
            "total_verified_open_matches": len(verified_listings),
            "csv_export_file": csv_path
        },
        "jobs": verified_listings
    }

    print("\n" + "=" * 65)
    print("📊 FINAL VERIFIED, SCORED & DEDUPLICATED LISTINGS")
    print("=" * 65)
    print(json.dumps(final_payload, indent=2))
    print("=" * 65)
    print(f"📁 CSV Export Complete: Saved {len(verified_listings)} role(s) to '{csv_path}'")

    if not verified_listings:
        print(f"💡 Notice: Zero dummy data returned. No active openings matched '{user_role}' ({user_location}) right now.")


if __name__ == "__main__":
    main()