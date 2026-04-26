---
name: web_research
version: 1.0.0
capabilities: [search, scrape, synthesize, cite]
tools_required: [web_search, scraper, memory]
telos_alignment: 0.95
author: ApeironAI Lab
---

# Web Research Skill

## Purpose
Conduct comprehensive web research on any topic. Search for relevant information, scrape detailed content from sources, synthesize findings, and provide properly cited results.

## Invocation Contract
Given a research topic or question, this skill:
1. Performs targeted web searches to find relevant sources
2. Scrapes detailed content from the most promising results
3. Synthesizes information into a coherent summary
4. Provides citations and source links for verification

## Output Format
Returns a structured research report with:
- Executive summary of key findings
- Detailed analysis by subtopic
- Source citations with URLs
- Confidence scores for each claim
- Suggestions for further research

## Examples
**Input:** "Research the environmental impact of electric vehicles vs gasoline cars"

**Output:**
```
# Electric vs Gasoline Vehicles: Environmental Impact Analysis

## Executive Summary
Electric vehicles show 40-60% lower lifetime emissions than gasoline vehicles,
with the gap widening as electricity grids become cleaner.

## Key Findings
1. Manufacturing emissions are higher for EVs (due to battery production)
2. Operational emissions are near-zero for EVs
3. Grid cleanliness significantly impacts overall emissions
4. Battery recycling reduces lifecycle impact

## Sources
- [IEA Report 2024](https://iea.org/ev-emissions)
- [Union of Concerned Scientists](https://ucsusa.org/ev-study)
- [Nature Climate Change](https://nature.com/ev-lifecycle)
```
