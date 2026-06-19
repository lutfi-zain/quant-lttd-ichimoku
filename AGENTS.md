# AGENTS.md

## What is this

Ichimoku quantification project. Goal: measure Ichimoku indicator performance as a trend-following system for Bitcoin.

## Tech decisions (confirmed)

- **Language:** Python (primary)
- **Charts:** Python can do this — use `matplotlib`, `plotly`, or `mplfinance` for Ichimoku visualization. No separate frontend needed initially.
- **Future:** React frontend with charting may be added later, but not now.

## Project phase

Greenfield — no code yet. Setting up from scratch.

## Evolution

Evolve local / global AGENTS.md by spawning subagents periodically to learn from current session, then propose amandemet. The goal is to not repeating the same step every time new session spawns.

