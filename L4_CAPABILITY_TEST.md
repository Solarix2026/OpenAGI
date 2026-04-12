# OpenAGI L5 Capability Test Suite

## L4 Test

### Test 1: Semantic Routing (No Hardcode)
**Input:**
```
你能干嘛
```
**Expected:** Response lists capabilities without "morning briefing" hardcoded path.
**Verify:** Check `~/.openagi/logs/kernel.log` for `[INTENT]` → should show `"action":"system_status"`

### Test 2: Self-Selecting Domains
**Input:**
```
innovate: how to reduce hospital wait times
```
**Expected:** Domains selected by NVIDIA (not hardcoded list).
**Verify:** Check log for `_select_relevant_domains` return → should include context-dependent domains like "hospital management", "queuing theory", "triage", not just "biology economics"

### Test 3: Document Reader (Generation Tier)
**Create a test file first:**
```bash
echo "Project Alpha Q3 Review\nRevenue: $1.2M\nTeam: 5 engineers" > ~/test_revenue.txt
```
**Input:**
```
read document ~/test_revenue.txt and tell me the revenue
```
**Expected:** `$1.2M` and "Project Alpha"
**Verify:** JSON response with `"answer"` containing extracted data

### Test 4: Reasoning Engine (Structured Logic)
**Input:**
```
reason: should we adopt microservices or monolith for a 3-person startup
mode: debate
```
**Expected:** Steelman both sides → synthesis → recommendation
**Verify:** Response has FOR/AGAINST headers, final RECOMMENDATION

## L5 Test

### Test 5: Tool Invention
**Input:**
```
invent_tool: automatically check disk space weekly and alert if < 10%
```
**Expected:** Generated `.py` file in `$WORKSPACE/invented/`
**Verify:** File exists + has `def run():` + imports + error handling + registered

### Test 6: Evolution Cycle
**Input:**
```
evolve
```
**Expected:** Gap detection → curriculum generation → test execution
**Verify:** Log shows `[EVOLUTION] Gap found: ...` → `[EVOLUTION] Running test ...`

### Test 7: Meta-Cognitive Reflection
**Precondition:** Have at least 5 tool calls fail in session
**Input:**
```
analyze your recent failures and explain patterns
```
**Expected:** Identifies common failure mode (e.g., "websearch times out due to rate limits")
**Verify:** Auto-generates goal: "Improve websearch resilience"

## Scoring

| Tier | Feature | Status |
|------|---------|--------|
| L4 | Semantic Routing | |
| L4 | Context-Aware Memory | |
| L4 | Self-Selecting Domains | |
| L4 | Structured Reasoning | |
| L4 | Document Analysis | |
| L5 | Tool Invention | |
| L5 | Evolution Cycle | |
| L5 | Meta-Cognition | |

## Expected Results

**If tests 1-5 pass:** System is L4 compliant (semantic routing, real-time learning, dynamic domains).

**If tests 6-8 pass:** System is L5 ready (self-modification, persistent improvement).

**Common Failures:**
- "String matching detected" → Kernel still has `if lower in (...)` branches
- "Hardcoded domains" → Innovation uses static list, not `_select_relevant_domains`
- "Tool didn't register" → `_run_action` has special branch bypassing registry

## Debug Commands

```bash
# Check for hardcode
grep -n "if lower in" kernel.py

# Check tool registration
python -c "from tool_executor import ToolExecutor; t=ToolExecutor('.'); print(t.registry.list_tools())"

# Check semantic routing
python -c "from semantic_engine import SemanticEngine; from tool_executor import ToolExecutor; s=SemanticEngine(ToolExecutor('.').registry); print(s.classify_intent('你能干嘛'))"
```
