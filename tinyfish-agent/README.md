# TinyFish AI Job & Internship Radar

## Live Demo Video
https://drive.google.com/file/d/1SNec_PfG-vVFAnIXlEKbNr7JO-wOjCOT/view?usp=sharing

## Overview
This project automates job and internship discovery by running autonomous browser agents across live career portals and startup job boards that lack public APIs. It filters out closed roles, removes duplicate listings, calculates relevance match scores, and exports verified openings to both JSON and CSV formats.

## Key Features
- **Chained Pipeline (Search -> Fetch -> Agent):** Dynamically builds and discovers target career endpoints, runs pre-flight liveness checks to skip dead links, and deploys the TinyFish Agent for live extraction.
- **Custom Company & Role Targeting:** Supports any role (Tech, Creative, Video Editing, Data, etc.), location, and specific company filtering alongside global aggregators.
- **Zero Dummy Data & Closed Role Filtering:** Strictly validates extracted listings against user query parameters and automatically drops expired or closed postings.
- **Match Scoring & Auto CSV Export:** Ranks every verified opening with a calculated match percentage (`match_score`) and saves the final output directly to `tinyfish_radar_results.csv`.

## How to Run

### 1. CLI Mode
Run the chained pipeline directly in your terminal:
```bash
python radar.py