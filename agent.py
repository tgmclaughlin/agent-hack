import asyncio
import os
import subprocess
import sys
from functools import wraps

import agents
import openai
from dotenv import load_dotenv


def sandboxed(base_dir):
    """Decorator to ensure file operations stay within base directory."""

    def decorator(func):
        @wraps(func)
        def wrapper(path: str, *args, **kwargs):
            # Convert to absolute path and validate
            abs_path = os.path.abspath(os.path.join(base_dir, path))
            if not abs_path.startswith(base_dir):
                return f"❌ Access denied: {path}"
            return func(abs_path, *args, **kwargs)

        return wrapper

    return decorator


def create_tools(base_dir):
    """Create sandboxed tools for the agent."""

    @agents.tool.function_tool
    @sandboxed(base_dir)
    def view(path: str, lines: tuple[int, int] = None):
        """View file or directory contents."""
        print(f"\n🔍 {path}")

        if os.path.isdir(path):
            items = [f for f in os.listdir(path) if not f.startswith(".")]
            return "\n".join(sorted(items)[:50])

        with open(path) as f:
            content = f.readlines()

        if lines:
            start, end = lines
            content = content[start - 1 : end]
            return "".join(f"{i + start:6}\t{line}" for i, line in enumerate(content))

        return "".join(f"{i + 1:6}\t{line}" for i, line in enumerate(content))

    @agents.tool.function_tool
    @sandboxed(base_dir)
    def write(path: str, content: str):
        """Write content to a file."""
        print(f"\n✏️ {path}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return f"Written: {path}"

    @agents.tool.function_tool
    @sandboxed(base_dir)
    def edit(path: str, old: str, new: str):
        """Replace text in a file."""
        print(f"\n✏️ {path}")
        with open(path) as f:
            content = f.read()

        if content.count(old) != 1:
            return "❌ Text must appear exactly once"

        with open(path, "w") as f:
            f.write(content.replace(old, new))
        return "Updated"

    @agents.tool.function_tool
    def bash(cmd: str):
        """Execute bash commands (restricted to working directory)."""
        print(f"\n💻 {cmd}")

        # Block dangerous patterns
        if any(x in cmd for x in ["../", "~/", "sudo", "rm -rf"]):
            return "❌ Command blocked"

        # Block absolute paths
        if any(
            part.startswith("/") for part in cmd.split() if not part.startswith("-")
        ):
            return "❌ Absolute paths not allowed"

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=base_dir,
            )
            return result.stdout or result.stderr
        except subprocess.TimeoutExpired:
            return "❌ Command timeout"
        except Exception as e:
            return f"❌ Error: {e}"

    return view, write, edit, bash


async def main():
    load_dotenv()

    # Use the directory containing this script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    print(f"🏠 Working in: {base_dir}\n")

    # Create sandboxed tools
    view, write, edit, bash = create_tools(base_dir)

    # Initialize agent
    llm = agents.OpenAIChatCompletionsModel(
        "claude-sonnet-4-20250514",
        openai.AsyncOpenAI(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            base_url="https://api.anthropic.com/v1/",
        ),
    )

    agent = agents.Agent(
        name="code_agent",
        instructions=f"Help with code in {base_dir}",
        model=llm,
        tools=[view, write, edit, bash],
    )

    # Chat loop
    messages = []
    initial_prompt = sys.argv[1] if len(sys.argv) > 1 else None

    while True:
        user_input = initial_prompt or input("👤 ")
        initial_prompt = None

        if user_input.lower() in ["exit", "quit"]:
            break

        messages.append({"role": "user", "content": user_input})
        print("\n🤖 ", end="", flush=True)

        response = ""
        async for event in agents.Runner.run_streamed(
            agent, messages, max_turns=100
        ).stream_events():
            if (
                event.type == "raw_response_event"
                and event.data.type == "response.output_text.delta"
            ):
                response += event.data.delta
                print(event.data.delta, end="", flush=True)

        messages.append({"role": "assistant", "content": response})
        print()


if __name__ == "__main__":
    agents.set_tracing_disabled(True)
    asyncio.run(main())
