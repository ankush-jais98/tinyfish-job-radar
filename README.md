# TinyFish AI Job & Internship Radar

## Problem Clarity
This agent automates internship hunting for students by scraping live, fragmented company career pages that lack public APIs and returning structured, deduplicated JSON listings with direct apply links.

## How TinyFish is Used
- **TinyFish Agent (`client.agent.run`)**: Deployed across 3+ live career portals (Jane Street, Anthropic, Scale AI) to dynamically navigate pages, filter roles based on user input (Role & Location), and extract structured JSON data (`role`, `company`, `location`, `link`).