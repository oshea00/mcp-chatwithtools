"""
MCP Tools Retriever

This module provides functionality to connect to MCP servers and retrieve their tool lists.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import aiofiles
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def get_tools_from_server(
    server_name: str, server_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Connect to an MCP server and retrieve its tools.

    Args:
        server_name: Name of the server
        server_config: Server configuration containing command and args

    Returns:
        Dictionary with server name and list of tools
    """
    try:
        command = server_config.get("command")
        args = server_config.get("args", [])
        env = server_config.get("env", None)

        if not command:
            return {
                "server": server_name,
                "error": "No command specified in configuration",
            }

        # Create server parameters
        server_params = StdioServerParameters(command=command, args=args, env=env)

        # Connect to the server
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()

                # List available tools
                tools_list = await session.list_tools()

                # Extract tool information
                tools = []
                for tool in tools_list.tools:
                    tool_info = {
                        "name": tool.name,
                        "description": tool.description,
                    }
                    if hasattr(tool, "inputSchema"):
                        tool_info["inputSchema"] = tool.inputSchema
                    tools.append(tool_info)

                return {"server": server_name, "tools": tools, "tool_count": len(tools)}

    except Exception as e:
        return {"server": server_name, "error": str(e)}


async def get_tools(config_path: str) -> List[Dict[str, Any]]:
    """
    Load MCP configuration and retrieve tools from all configured servers.

    Args:
        config_path: Path to the mcp.json configuration file

    Returns:
        List of dictionaries containing server information and their tools
    """
    # Load configuration file
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    async with aiofiles.open(config_file, "r") as f:
        content = await f.read()
        config = json.loads(content)

    # Get mcpServers configuration
    mcp_servers = config.get("mcpServers", {})

    if not mcp_servers:
        return [{"error": "No mcpServers found in configuration"}]

    # Process each server
    tasks = []
    for server_name, server_config in mcp_servers.items():
        tasks.append(get_tools_from_server(server_name, server_config))

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks)

    return results


async def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python get_mcp_tools.py <path_to_mcp.json>")
        sys.exit(1)

    config_path = sys.argv[1]

    try:
        results = await get_tools(config_path)

        # Pretty print the results
        print(json.dumps(results, indent=2))

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON configuration: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
