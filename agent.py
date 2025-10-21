"""
Bootstrap Challenge: Start with only READ, build up to full agent

Stage 1: READ only - Agent can examine code but not modify
Stage 2: Get agent to write the function for you that can write to files - you'll need to manually add it
Stage 3: Agent uses READ+WRITE to add SHELL itself
"""

import asyncio
import os
from dotenv import load_dotenv
import agents
import openai


# Stage 1: Start with ONLY read tool
@agents.tool.function_tool
def read(filename: str):
    """Read a file."""
    print(f"\n📖 Reading: {filename}")
    with open(filename) as f:
        return f.read()
    return None


# Stage 2: Write tool will be added here by user after agent provides code


# Stage 3: Shell tool will be added here by agent itself using write


async def main():
    load_dotenv()

    llm = agents.OpenAIChatCompletionsModel(
        "claude-sonnet-4-5-20250929",
        openai.AsyncOpenAI(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            base_url="https://api.anthropic.com/v1/",
        ),
    )

    agent = agents.Agent(
        name="bootstrap_agent",
        instructions="You help with coding tasks.",
        model=llm,
        tools=[read],  # Starting with just read!
    )

    messages = []

    print("\n🔨 BOOTSTRAP CHALLENGE")
    print("Stage 1: You have only READ. Ask me to read agent.py to learn the pattern.")
    print("Stage 2: I'll tell you what code to add for WRITE.")
    print("Stage 3: Together we'll add SHELL using our new powers!\n")

    while True:
        user_input = input("\n> ")
        if user_input == "exit":
            break

        messages.append({"role": "user", "content": user_input})

        print("", end="", flush=True)
        response = ""

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
    asyncio.run(main())
