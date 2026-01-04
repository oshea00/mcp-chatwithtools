"""
Interactive Chat with MCP Tools

This module provides an interactive chat session using OpenAI that can call MCP server tools.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from get_mcp_tools import get_tools


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

        try:
            command = server_config.get("command")
            args = server_config.get("args", [])
            env = server_config.get("env", None)

            # Create server parameters
            server_params = StdioServerParameters(command=command, args=args, env=env)

            # Connect to the server and execute the tool
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the session
                    await session.initialize()

                    # Call the tool
                    result = await session.call_tool(tool_name, arguments=arguments)

                    # Extract content from result
                    if hasattr(result, "content"):
                        content_items = []
                        for item in result.content:
                            if hasattr(item, "text"):
                                content_items.append(item.text)
                            else:
                                content_items.append(str(item))
                        return "\n".join(content_items)

                    return str(result)

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

    async def run(self):
        """Run the interactive chat loop."""
        await self.initialize()

        print("Chat session started. Type 'exit' or 'quit' to end the session.")
        print("=" * 60)
        print()

        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    print("Goodbye!")
                    break

                # Send message and get response
                response = await self.send_message(user_input)

                print(f"\nAssistant: {response}")
                print()

            except KeyboardInterrupt:
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
    model = sys.argv[2] if len(sys.argv) > 2 else "gpt-4o-mini"

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
