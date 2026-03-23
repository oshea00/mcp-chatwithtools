"""
Interactive Chat with MCP Tools

This module provides an interactive chat session using OpenAI that can call MCP server tools.
"""

import asyncio
import json
import os
import shutil
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from get_mcp_tools import get_tools

load_dotenv(override=True)


class MCPToolExecutor:
    """Manages MCP server connections and tool execution."""

    def __init__(self, config_path: str):
        """
        Initialize the MCP tool executor.

        Args:
            config_path: Path to the mcp.json configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.tool_to_server = {}  # Maps tool names to server names

    def _load_config(self) -> Dict[str, Any]:
        """Load the MCP configuration file."""
        config_file = Path(self.config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(config_file, "r") as f:
            return json.load(f)

    async def initialize_tools(self) -> List[Dict[str, Any]]:
        """
        Get all tools from configured MCP servers and format them for OpenAI.

        Returns:
            List of tool definitions in OpenAI format
        """
        # Get tools from all servers
        server_tools = await get_tools(self.config_path)

        # Convert to OpenAI tool format
        openai_tools = []

        for server_info in server_tools:
            if "error" in server_info:
                print(
                    f"Warning: Error from server {server_info.get('server', 'unknown')}: {server_info['error']}",
                    file=sys.stderr,
                )
                continue

            server_name = server_info.get("server")
            tools = server_info.get("tools", [])

            for tool in tools:
                tool_name = tool.get("name")

                # Map tool name to server
                self.tool_to_server[tool_name] = server_name

                # Format for OpenAI
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool.get("description", ""),
                    },
                }

                # Add input schema if available
                if "inputSchema" in tool:
                    openai_tool["function"]["parameters"] = tool["inputSchema"]

                openai_tools.append(openai_tool)

        return openai_tools

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool on the appropriate MCP server.

        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments to pass to the tool

        Returns:
            Result of the tool execution as a string
        """
        # Find which server has this tool
        server_name = self.tool_to_server.get(tool_name)
        if not server_name:
            return json.dumps({"error": f"Tool {tool_name} not found"})

        # Get server configuration
        server_config = self.config.get("mcpServers", {}).get(server_name)
        if not server_config:
            return json.dumps({"error": f"Server {server_name} not configured"})

        async def _call_tool(session: ClientSession) -> str:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            if hasattr(result, "content"):
                content_items = []
                for item in result.content:
                    if hasattr(item, "text"):
                        content_items.append(item.text)
                    else:
                        content_items.append(str(item))
                return "\n".join(content_items)
            return str(result)

        try:
            url = server_config.get("url")
            if url:
                async with streamablehttp_client(url) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        return await _call_tool(session)

            command = server_config.get("command")
            args = server_config.get("args", [])
            env = server_config.get("env", None)

            server_params = StdioServerParameters(command=command, args=args, env=env)
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    return await _call_tool(session)

        except Exception as e:
            return json.dumps({"error": str(e)})


class ChatSession:
    """Manages an interactive chat session with OpenAI and MCP tools."""

    def __init__(self, config_path: str, model: str = "gpt-4o-mini"):
        """
        Initialize the chat session.

        Args:
            config_path: Path to the mcp.json configuration file
            model: OpenAI model to use
        """
        self.model = model
        self.messages = []
        self.tool_executor = MCPToolExecutor(config_path)
        self.tools = None

        # Initialize OpenAI client
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        base_url = os.environ.get("OPENAI_BASE_URL")
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)

    async def initialize(self):
        """Initialize the chat session by loading MCP tools."""
        print("Initializing MCP tools...")
        self.tools = await self.tool_executor.initialize_tools()
        print(f"Loaded {len(self.tools)} tools from MCP servers")
        print()

    async def send_message(self, user_message: str) -> str:
        """
        Send a message and handle the response, including tool calls.

        Args:
            user_message: The user's message

        Returns:
            The assistant's response
        """
        # Add user message to conversation
        self.messages.append({"role": "user", "content": user_message})

        # Make initial API call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self.tools if self.tools else None,
            tool_choice="auto" if self.tools else None,
        )

        assistant_message = response.choices[0].message

        # Check if the assistant wants to call tools
        if assistant_message.tool_calls:
            # Add assistant's message with tool calls to conversation
            self.messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                }
            )

            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                print(f"Calling tool: {tool_name} with args: {tool_args}")

                # Execute the tool via MCP
                tool_result = await self.tool_executor.execute_tool(
                    tool_name, tool_args
                )

                # Add tool result to conversation
                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    }
                )

            # Make second API call with tool results
            response = self.client.chat.completions.create(
                model=self.model, messages=self.messages
            )

            assistant_message = response.choices[0].message

        # Add final assistant response to conversation
        self.messages.append(
            {"role": "assistant", "content": assistant_message.content}
        )

        return assistant_message.content

    @staticmethod
    def _print_table_divider(col_widths: tuple, char: str = "-"):
        parts = [char * (w + 2) for w in col_widths]
        print("+" + "+".join(parts) + "+")

    @staticmethod
    def _print_table_row(cells: tuple, col_widths: tuple, header: bool = False):
        wrapped = [textwrap.wrap(str(c), w) or [""] for c, w in zip(cells, col_widths)]
        height = max(len(w) for w in wrapped)
        if header:
            ChatSession._print_table_divider(col_widths)
        for line_idx in range(height):
            row = ""
            for col_idx, w in enumerate(col_widths):
                cell_line = (
                    wrapped[col_idx][line_idx]
                    if line_idx < len(wrapped[col_idx])
                    else ""
                )
                row += f"| {cell_line:<{w}} "
            print(row + "|")
        ChatSession._print_table_divider(col_widths)

    def handle_slash_command(self, command: str) -> bool:
        """
        Handle a slash command. Returns True if command was handled.

        Args:
            command: The slash command string (e.g. '/tools')
        """
        parts = command.strip().split()
        cmd = parts[0].lower()

        if cmd == "/exit":
            print("Goodbye!")
            sys.exit(0)

        if cmd == "/tools":
            if not self.tools:
                print("No tools loaded.")
            else:
                print(f"\n{len(self.tools)} tool(s) available:\n")
                term_width = shutil.get_terminal_size().columns
                # 4 borders (|) + 3×2 padding spaces = 10 overhead chars
                usable = max(term_width - 10, 30)
                # distribute: name 24%, description 38%, arguments 38%
                col_widths = (
                    max(6, int(usable * 0.24)),
                    max(10, int(usable * 0.38)),
                    max(10, usable - int(usable * 0.24) - int(usable * 0.38)),
                )
                self._print_table_row(
                    ("Name", "Description", "Arguments"), col_widths, header=True
                )
                for tool in self.tools:
                    fn = tool["function"]
                    name = fn.get("name", "")
                    desc = fn.get("description", "(no description)")
                    params = fn.get("parameters", {}).get("properties", {})
                    required = fn.get("parameters", {}).get("required", [])
                    args_parts = []
                    for arg_name, arg_info in params.items():
                        arg_type = arg_info.get("type", "any")
                        arg_desc = arg_info.get("description", "")
                        req = "*" if arg_name in required else ""
                        args_parts.append(
                            f"{arg_name}{req}:{arg_type} {arg_desc}".strip()
                        )
                    args_text = "  ".join(args_parts) if args_parts else "-"
                    self._print_table_row((name, desc, args_text), col_widths)
                self._print_table_divider(col_widths)
            print()
            return True

        print(f"Unknown command: {cmd}")
        print()
        return True

    async def run(self):
        """Run the interactive chat loop."""
        await self.initialize()

        print("Chat session started. Type '/exit' to end the session.")
        print("Type '/tools' to list available tools.")
        print("=" * 60)
        print()

        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    self.handle_slash_command(user_input)
                    continue

                # Send message and get response
                response = await self.send_message(user_input)

                print(f"\nAssistant: {response}")
                print()

            except (KeyboardInterrupt, EOFError):
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                print()


async def main():
    """Main entry point for the chat program."""
    if len(sys.argv) < 2:
        print("Usage: python chatwithtools.py <path_to_mcp.json> [model]")
        print("  model: Optional OpenAI model (default: gpt-4o-mini)")
        sys.exit(1)

    config_path = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "gpt-4o"

    try:
        chat = ChatSession(config_path, model)
        await chat.run()

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
