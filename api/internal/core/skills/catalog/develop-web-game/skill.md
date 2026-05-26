# Develop Web Game

Use this skill when building or iterating on a web game and you need a reliable development and testing loop.

## Core workflow

1. Make the smallest change that moves the game forward.
2. Run a Playwright-based test loop after every meaningful change.
3. Inspect screenshots and text state as the source of truth.
4. Fix console errors before moving on.
5. Repeat until the interaction feels stable and correct.

## Practical guidance

- Keep the game loop deterministic when possible.
- Expose a text-state representation for automated checks.
- Track progress and open issues so another pass can continue cleanly.
- Verify important interactions end-to-end, not just the start screen.

## Output expectations

- Focus on small deltas and visible behavior.
- Call out test failures, regressions, and missing interactions.
- Prefer clear state and reproducible test steps over broad rewrites.
