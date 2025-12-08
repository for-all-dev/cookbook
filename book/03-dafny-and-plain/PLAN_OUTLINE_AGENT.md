# Outline for Chapter 03: DafnyBench with Plain Python

## Context from Exploration

**Existing Chapter 2 Structure (Dafny and Inspect):**
- 8 sections following progressive elaboration: context → background → dataset → framework → practice → implementation → refinement → conclusion
- Literary/engaging style with Cervantes-like prose
- Detailed code walkthroughs with line numbers
- Focus on Inspect AI's abstractions (Task, Solver, Scorer)
- Addresses the "touchdown dance" problem with extraction strategies

**Plain Python Implementation Key Features:**
- Manual tool-calling loop (shows what `generate()` abstracts)
- 6 specialized tools (5 insertion tools + verify_dafny)
- Dual location specification (line numbers + context matching)
- TOML configuration system for prompts and settings
- State management via message history markers
- Artifact persistence with `_final.dfy` naming
- ~1,234 lines across 7 modules

**Existing Chapter 3 Files:**
- `00-ch0.md` - Placeholder intro with notes
- `09-ch9.md` - Conclusion about when to use plain Python (3+ month codebases)

---

## Proposed Outline (8 Sections)

### **00. Introduction: Dispelling Framework Superstition**
**File:** `00-ch0.md` (already exists, needs expansion)

**Content:**
- Opening hook: The "plain Python" philosophy
- Why this chapter exists: demystify frameworks by showing raw implementation
- What we're building: same DafnyBench solver, no frameworks
- Preview of key innovations: specialized tools, TOML config, manual loops
- Transition: "Let's see what Inspect was doing for us..."

**Teaching goal:** Set expectations and motivate the chapter

---

### **01. The Manual Tool-Calling Loop** ⭐ HIGH EMPHASIS
**File:** `01-ch1.md` (new)

**Content:**
- The core loop structure (`agent.py:225-434`)
- What `generate()` abstracts away
- **Deep dive**: Message history management (assistant → tool_use → user → tool_result)
- **Deep dive**: Stop reasons (`end_turn`, `tool_use`, unexpected) and iteration control
- **Deep dive**: Message pairing discipline - why tool_results must follow assistant
- Code walkthrough with detailed annotations
- The "one more call" pattern when verification succeeds (letting model respond to success)
- Edge cases: hitting max_iterations, API errors, timeouts

**Key code sections:**
```python
for iteration in range(max_iterations):
    response = client.messages.create(...)
    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "tool_use":
        # Process tools...
        messages.append({"role": "user", "content": tool_results})
```

**Teaching goal:** Demystify the tool-calling loop that frameworks hide, with deep mechanical understanding

---

### **02. Specialized Insertion Tools** ⭐ HIGH EMPHASIS
**File:** `02-ch2.md` (new)

**Content:**
- **Deep dive**: The problem with monolithic tools (regenerating entire files)
- Five specialized insertion tools vs. one verify tool
- **Deep dive**: Tool design philosophy
  - Focused single responsibility
  - Composable operations
  - Agent-friendly APIs (what vs how)
  - Reducing cognitive load
- **Deep dive**: Trade-offs in tool granularity
  - Monolithic: simple API, complex calls
  - Specialized: complex API, simple calls
  - When to choose each approach
- API surface comparison: `verify_dafny(full_code)` vs. `insert_invariant(hint, location)`
- The three-layer architecture (generic → type-specific → utilities)
- Indentation handling and proper Dafny syntax formatting

**Tool inventory:**
- `insert_invariant()` - Loop invariants
- `insert_assertion()` - Intermediate assertions
- `insert_precondition()` - Function requires clauses
- `insert_postcondition()` - Function ensures clauses
- `insert_measure()` - Termination decreases clauses
- `verify_dafny()` - Run verification on accumulated state

**Teaching goal:** Show the design trade-offs in tool granularity with deep philosophical treatment

---

### **03. Dual Location Specification**
**File:** `03-ch3.md` (new)

**Content:**
- The challenge: How should agents specify WHERE to insert hints?
- Strategy 1: Line numbers (precise but brittle)
- Strategy 2: Context matching (flexible but ambiguous)
- Hybrid approach: both options available
- Implementation walkthrough (`find_insertion_point()`)
- Ambiguity detection and error messages
- Context_after for disambiguation
- Agent-friendly API design principles

**Code examples:**
```python
# Precise
insert_invariant(invariant="0 <= i <= n", line_number=5)

# Flexible
insert_invariant(
    invariant="0 <= i <= n",
    context_before="while (i < n)"
)

# Disambiguated
insert_invariant(
    invariant="0 <= i <= n",
    context_before="while (i < n)",
    context_after="{"
)
```

**Teaching goal:** Demonstrate thoughtful tool API design for LLMs

---

### **04. State Management via Message History** ⭐ HIGH EMPHASIS
**File:** `04-ch4.md` (new)

**Content:**
- The state tracking problem: code evolves through insertions
- **Deep dive**: Message history as single source of truth (vs. separate state)
- State markers: `=== CURRENT_CODE_STATE ===`
- `get_code_state()` - Backtracking through messages (implementation walkthrough)
- `update_code_state()` - Appending new state (implementation walkthrough)
- **Deep dive**: Maintaining Anthropic API message pairing semantics
  - Why tool_use must be paired with tool_result
  - Where state updates fit in the sequence
  - Consequences of breaking pairing
- **Deep dive**: Why updates happen AFTER tool_results (pairing discipline)
- **Deep dive**: Trade-off: cumulative vs. atomic tool calls in single turn
  - What happens with multiple insertions in one turn
  - Why agent must verify between modifications to see cumulative effects
  - Design decision implications

**Key insight:** Multiple insertions in one turn aren't cumulative because state updates come after tool_results. Agent must verify or wait for next iteration.

**Teaching goal:** Show state management patterns without framework magic, with deep understanding of message structure and timing

---

### **05. Configuration as Code: TOML and Templates**
**File:** `05-ch5.md` (new)

**Content:**
- The problem with hardcoded prompts and magic numbers
- Configuration-driven design philosophy
- `config.toml` structure (5 sections)
  - `[evaluation]` - Loop limits, timeouts, model
  - `[logging]` - Artifacts, log levels
  - `[prompt]` - System prompt + templates with interpolation
  - `[dataset]` - HuggingFace config
- Template interpolation: `{code}` variables
- Configuration loading mechanism (`PlainConfig` dataclass)
- Global singleton pattern with `get_config()`
- Python 3.11+ `tomllib` with fallback to `tomli`

**185-line system prompt walkthrough:**
- Tool descriptions
- Workflow (analyze → identify → insert → verify → iterate)
- Both location strategies with examples
- Important rules and Dafny syntax reminders

**Teaching goal:** Show how configuration enables reusability and testing

---

### **06. Running the Plain Implementation**
**File:** `06-ch6.md` (new)

**Content:**
- CLI command: `uv run agent dafnybench plain`
- Arguments: `--model`, `--limit`
- Comparison with inspect: `plain` vs. `inspect` subcommands
- Log structure: `logs/plain_YYYYMMDD_HHMMSS.log`
- Artifact structure: `artifacts/sample_<id>_attempt_<n>.dfy` and `_final.dfy`
- Reading artifacts to understand agent behavior
- Interpreting success/failure output
- Debugging with message history inspection

**Practical walkthrough:**
```bash
# Test with 1 sample
uv run agent dafnybench plain --limit 1

# Full evaluation
uv run agent dafnybench plain --limit -1

# Different model
uv run agent dafnybench plain -m anthropic/claude-opus-4
```

**Teaching goal:** Make the implementation immediately usable

---

### **07. Code Walkthrough: Tying It All Together**
**File:** `07-ch7.md` (new)

**Content:**
- Complete architecture overview
- File-by-file walkthrough with line counts
  - `__init__.py` (81 lines) - Orchestration
  - `agent.py` (446 lines) - Manual loop
  - `tools.py` (437 lines) - Insertion tools + verify
  - `config.py` (128 lines) - TOML loading
  - `types.py` (81 lines) - Dataclasses + artifacts
  - `metrics.py` (40 lines) - Result aggregation
  - `prompt.py` (21 lines) - Backwards compat
- Data flow: dataset → agent loop → tools → verification → metrics
- Shared code: reusing `categorize_error()` from inspect_ai
- Error handling: timeouts, bypass attempts, parsing failures
- The artifact naming innovation: `_final.dfy` for successful verifications

**Teaching goal:** Provide navigable reference for the implementation

---

### **08. When to "Rawdog" vs. Use Frameworks**
**File:** `08-ch8.md` (new)

**Content:**
- The 3-month rule: frameworks for exploration, plain for serious work
- Trade-offs table:

| Aspect | Plain Python | Frameworks (Inspect) |
|--------|-------------|---------------------|
| **Setup time** | Higher (implement loop) | Lower (batteries included) |
| **Flexibility** | Complete control | Constrained by abstractions |
| **Maintenance** | Direct, no surprises | Framework updates may break |
| **Learning curve** | Steep (must understand APIs) | Gentle (guided patterns) |
| **Debugging** | Explicit, transparent | Abstract, harder to trace |
| **Customization** | Trivial (just code) | May hit framework limits |
| **Infrastructure** | DIY (logging, dashboards) | Provided (inspect view) |

- When frameworks shine: research, rapid prototyping, standard use cases
- When plain Python shines: production systems, custom requirements, long-term codebases
- The "framework-to-plain" migration path
- Modern advantages: Anthropic structured outputs, better APIs

**Teaching goal:** Help readers make informed architectural decisions

---

### **09. Conclusion & Exercises**
**File:** `09-ch9.md` (already exists, may need minor edits)

**Content:**
- Summary: We've seen what frameworks abstract away
- Key takeaways: manual loops, specialized tools, configuration-driven design
- The broader pattern: this applies to all agent frameworks (not just Inspect)
- Transition to next chapter: Lean and pydantic-ai

**Exercises:**
1. Add a new insertion tool: `insert_lemma()` for helper lemmas
2. Implement retry logic with exponential backoff for API calls
3. Add streaming support to show incremental verification output
4. Create a visualization tool that animates the agent's insertion decisions
5. **Port the inspect implementation to use specialized insertion tools** (from ch0 notes)
6. Add conversation persistence: save/resume agent sessions
7. Implement a "dry run" mode that shows insertions without verification

**Teaching goal:** Encourage hands-on exploration and extension

---

## Narrative Arc

**Chapter 2 (Inspect):** "Here's a powerful framework that makes verification agents easy"

**Chapter 3 (Plain):** "Here's what that framework was doing for you, and why you might want to do it yourself"

**Flow:**
1. Motivate with philosophy (dispel framework superstition)
2. Show the core loop (demystify `generate()`)
3. Explore tool design (specialized vs. monolithic)
4. Dig into implementation details (location specs, state, config)
5. Make it practical (running, reading artifacts)
6. Provide reference (architecture overview)
7. Guide architectural decisions (when to use what)
8. Encourage exploration (exercises)

---

## Style Notes

- Maintain literary/engaging tone from Chapter 2
- Use code annotations and line references
- **Consolidate comparisons**: Save Inspect AI comparisons for section 08, not throughout
- Embed literal code includes from the implementation
- Keep focus on **why** decisions were made, not just **what** they are
- Reference figures: agent-helix.png can be reused
- Create new diagrams: message history structure, tool routing flow

## Emphasis Areas (per user feedback)

**High priority** - These should get deeper treatment:
1. **Manual loop mechanics** - iteration control, message pairing discipline, stop reasons
2. **Tool design philosophy** - specialized vs monolithic, composable APIs, agent-friendliness
3. **State management** - message history as truth, update timing, cumulative vs atomic

**Standard coverage** - Important but don't over-elaborate:
- TOML configuration system
- Dual location specification
- Artifact persistence

---

## Files to Create

1. `01-ch1.md` - Manual tool-calling loop
2. `02-ch2.md` - Specialized insertion tools
3. `03-ch3.md` - Dual location specification
4. `04-ch4.md` - State management
5. `05-ch5.md` - Configuration system
6. `06-ch6.md` - Running and using
7. `07-ch7.md` - Code walkthrough
8. `08-ch8.md` - When to use plain vs frameworks

**Total:** 8 new files + 2 existing (00, 09) = 10 sections

---

## Key Teaching Principles

1. **Transparency over abstraction**: Show exactly what frameworks hide
2. **Design decisions**: Explain why choices were made (trade-offs)
3. **Practical patterns**: Message pairing, state tracking, config loading
4. **Tool API design**: Agent-friendly interfaces (dual location specs)
5. **Architectural guidance**: When to framework, when to plain
6. **Reusable patterns**: These ideas apply beyond DafnyBench
