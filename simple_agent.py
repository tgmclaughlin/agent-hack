"""
The simplest possible agent to show the core concept:
An agent = LLM + Tools + Loop

This is literally all an agent is:
1. Send messages to an LLM
2. The LLM can respond with text or call tools
3. Loop back to step 1
"""
import asyncio
import os
import subprocess
import agents
import openai
from dotenv import load_dotenv


# Tools are just functions the LLM can call
@agents.tool.function_tool
def read_file(filename: str):
    """Read a file."""
    with open(filename) as f:
        return f.read()


@agents.tool.function_tool
def write_file(filename: str, content: str):
    """Write to a file."""
    with open(filename, "w") as f:
        f.write(content)
    return "File written"


@agents.tool.function_tool
def run_bash(command: str):
    """Run a bash command."""
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
        name="demo",
        instructions="You help with coding tasks.",
        model=llm,
        tools=[read_file, write_file, run_bash],
    )
    
    # 3. The conversation loop
    messages = []
    
    while True:
        # Get user input
        user_input = input("\n👤 ")
        if user_input == "exit":
            break
            
        # Add to conversation
        messages.append({"role": "user", "content": user_input})
        
        # Get LLM response (might include tool calls)
        print("🤖 ", end="", flush=True)
        response = ""
        
        async for event in agents.Runner.run_streamed(
            agent, messages, max_turns=5
        ).stream_events():
            if (event.type == "raw_response_event" and 
                event.data.type == "response.output_text.delta"):
                response += event.data.delta
                print(event.data.delta, end="", flush=True)
        
        # Save response and loop
        messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    agents.set_tracing_disabled(True)
    print("🚀 Simple Agent Demo - Type 'exit' to quit")
    asyncio.run(main())