# Working guidelines

Adapted from [Andrej Karpathy's observations](https://x.com/karpathy/status/2015883857489522876) on
common LLM coding mistakes. These bias toward caution over speed — use judgment on trivial tasks.

## Think before coding

Don't assume, don't hide confusion, surface tradeoffs.

- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them rather than silently picking one.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop and name what's confusing.

## Simplicity first

The minimum code that solves the problem, nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No flexibility or configurability that wasn't requested.
- No error handling for impossible scenarios.
- If 200 lines could be 50, rewrite it.

The test: would a senior engineer call this overcomplicated?

## Surgical changes

Touch only what you must. Clean up only your own mess.

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor what isn't broken.
- Match existing style, even where you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.
- Do remove imports, variables, and functions that *your* changes orphaned.

The test: every changed line should trace directly to the request.

## Goal-driven execution

Define success criteria, then loop until verified.

- "Add validation" becomes "write tests for invalid inputs, then make them pass."
- "Fix the bug" becomes "write a test that reproduces it, then make it pass."
- "Refactor X" becomes "ensure tests pass before and after."

For multi-step work, state the plan as steps paired with their verification before starting.
Strong criteria allow independent looping; weak criteria ("make it work") force constant
clarification.

For changes with a runtime surface, verification means exercising the affected flow end-to-end —
not just a passing typecheck. The `/verify` skill does this.
