"""Section-level migration code for migrate-to-codex.

Each module owns one source-to-Codex surface: instructions, skills/commands,
subagents, MCP/config, hooks, plugin-like sources, or shared primitives.
`cli.py` should orchestrate these modules instead of embedding conversions.
"""
