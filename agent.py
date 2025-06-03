"""
What is an agent? Just 3 things:

1. An LLM that can output function calls (not just text)
2. Functions (tools) that execute when the LLM calls them
3. A loop that feeds results back to the LLM

That's it. The LLM is in control, deciding what to do next.
"""

import asyncio
import os
from dotenv import load_dotenv
import agents
import openai


# These are tools - just regular Python functions
# The LLM can call these by outputting structured JSON


@agents.tool.function_tool
def read(filename: str):
    """Read a file."""
    print(f"\n📖 Reading: {filename}")
    with open(filename) as f:
        return f.read()


@agents.tool.function_tool
def write(filename: str, content: str):
    """Write to a file."""
    print(f"\n✍️  Writing: {filename}")
    with open(filename, "w") as f:
        f.write(content)
    return "Done"


@agents.tool.function_tool
def bash(command: str):
    """Run a shell command."""
    print(f"\n💻 Running: {command}")
    import subprocess

    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout or result.stderr


async def main():
    load_dotenv()

    # 1. Create an LLM client
    llm = agents.OpenAIChatCompletionsModel(
        "claude-sonnet-4-20250514",
        openai.AsyncOpenAI(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            base_url="https://api.anthropic.com/v1/",
        ),
    )

    # 2. Create an agent (LLM + tools)
    agent = agents.Agent(
        name="claude_code",
        instructions="You help with coding tasks.",
        model=llm,
        tools=[read, write, bash],  # <-- The LLM can call these
    )

    # 3. The loop: User → LLM → Tools → LLM → User
    messages = []

    while True:
        # User input
        user_input = input("\n> ")
        if user_input == "exit":
            break

        messages.append({"role": "user", "content": user_input})

        # LLM decides: respond with text OR call a tool
        print("", end="", flush=True)
        response = ""

        # This is where the magic happens:
        # - LLM might output text (shown to user)
        # - LLM might output tool calls (executed automatically)
        # - Results go back to LLM, which can call more tools or respond
        async for event in agents.Runner.run_streamed(
            agent, messages, max_turns=10
        ).stream_events():
            if (
                event.type == "raw_response_event"
                and event.data.type == "response.output_text.delta"
            ):
                response += event.data.delta
                print(event.data.delta, end="", flush=True)

        messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    agents.set_tracing_disabled(True)
    print("🤖 Agent = LLM + Tools + Loop")
    print("Try: 'write a file called test.txt with hello world'")
    asyncio.run(main())
