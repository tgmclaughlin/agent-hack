# agent-hack

The simplest possible agent: LLM + Tools + Loop

## Setup

1. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Install dependencies: `uv sync`
3. Copy `.env.example` to `.env` and add your Anthropic API key
4. Run: `uv run python agent.py`
