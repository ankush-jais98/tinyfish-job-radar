# TinyFish AI Job & Internship Radar 🐟🚀

## 🎥 Watch the Live Demo Video
https://drive.google.com/file/d/1SNec_PfG-vVFAnIXlEKbNr7JO-wOjCOT/view?usp=sharing

## Problem Clarity
This agent automates internship hunting for students by scraping live, fragmented company career pages that lack public APIs and returning structured, deduplicated JSON listings with direct apply links.

## 🚀 Two Ways to Run the Project

### 1. Web UI Mode 
I have built a custom Flask frontend so anyone can use this agent easily.
- **Run:** `python app.py`
- Open `http://127.0.0.1:5000` in your browser.
- Enter your role (e.g., ui/ux) and location. The UI will hit the TinyFish API, deduct credits in real-time, and show the exact apply links on the screen!

### 2. CLI Mode (Original Script)
For developers who prefer terminal execution.
- **Run:** `python radar.py`
- Enter role and location when prompted in the terminal.

## How TinyFish is Used
- TinyFish Agent (`client.agent.run`): Deployed across 3+ live career portals (Jane Street, Anthropic, Scale AI) to dynamically navigate pages, filter roles based on user input, and extract structured JSON data (`role`, `company`, `location`, `link`).
