---
name: self_repair
version: 1.0.0
capabilities: [diagnose, repair, test, validate]
tools_required: [code, file, shell, memory]
telos_alignment: 0.88
author: ApeironAI Lab
---

# Self-Repair Skill

## Purpose
Autonomously diagnose and repair code issues, run tests, and validate fixes. This skill embodies the metacognitive repair loop that makes the agent self-improving.

## Invocation Contract
Given a code issue, error, or failing test, this skill:
1. Analyzes the problem and identifies root cause
2. Determines appropriate repair strategy
3. Implements surgical fixes (not wholesale rewrites)
4. Runs tests to validate the fix
5. Iterates until the issue is resolved
6. Documents the repair for future reference

## Output Format
Returns detailed repair report with:
- Problem diagnosis and root cause analysis
- Repair strategy and rationale
- Code changes made (with before/after comparison)
- Test results and validation
- Lessons learned for procedural memory
- Confidence score in the fix

## Examples
**Input:** "The web scraper is failing with timeout errors on large pages"

**Output:**
```
# Self-Repair Report: Web Scraper Timeout Issue

## Problem Diagnosis
**Symptom:** Timeout errors when scraping large pages (>1MB)
**Root Cause:** Fixed timeout of 30 seconds insufficient for large pages
**Impact:** 15% of scraping operations failing

## Repair Strategy
1. Implement adaptive timeout based on page size
2. Add progress monitoring for long-running scrapes
3. Implement retry logic with exponential backoff
4. Add early termination for non-essential content

## Code Changes

### Before (scraper.py line 45):
```python
async def scrape(self, url: str) -> str:
    response = await self.client.get(url, timeout=30)
    return response.text
```

### After (scraper.py line 45):
```python
async def scrape(self, url: str) -> str:
    # Adaptive timeout: 30s base + 10s per expected MB
    size_estimate = await self._estimate_size(url)
    timeout = 30 + (size_estimate * 10)
    response = await self.client.get(url, timeout=timeout)
    return response.text
```

## Test Results
- ✅ Small pages (<100KB): 100% success (was 100%)
- ✅ Medium pages (100KB-1MB): 100% success (was 95%)
- ✅ Large pages (>1MB): 98% success (was 60%)
- ⚠️  Very large pages (>10MB): 85% success (acceptable tradeoff)

## Lessons Learned
1. Fixed timeouts don't scale with content size
2. Adaptive timeouts improve reliability significantly
3. Progress monitoring helps with user experience
4. Some edge cases may need manual intervention

## Confidence Score: 0.92
```
