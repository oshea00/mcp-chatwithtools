# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Course - A learning project demonstrating Model Context Protocol (MCP) integration patterns. Contains examples of:
- MCP server implementation (FastMCP)
- MCP client integration with OpenAI LLM
- Gradio integration with MCP
- Tool discovery and execution across MCP servers

## Development Setup

This project uses `uv` for Python package management (Python 3.12+).

### Environment Setup
```bash
# Install dependencies
uv sync

# Set OpenAI API key (required for chatwithtools.py)
export OPENAI_API_KEY="your-api-key"
```

## Running Applications

### Interactive Chat with MCP Tools
```bash
# Run with default model (gpt-4o-mini)
python chatwithtools.py mcp.json

# Run with specific OpenAI model
python chatwithtools.py mcp.json gpt-4o
```

### MCP Server
```bash
# Run standalone MCP server (stdio transport)
python server.py
```

### Gradio Interface with MCP
```bash
# Launch Gradio web UI that also exposes MCP server
python gradiomcp.py
```

### Tool Discovery
```bash
# List all tools from configured MCP servers
python get_mcp_tools.py mcp.json
```

## Architecture

### Core Components

**chatwithtools.py** - OpenAI chat client with MCP tool integration
- `ChatSession`: Manages conversation with OpenAI, orchestrates tool calls
- `MCPToolExecutor`: Handles MCP server connections, tool discovery, and execution
- Flow: User message → OpenAI (with tools) → Tool calls (if needed) → MCP server execution → OpenAI (with results) → Response

**server.py** - MCP server using FastMCP framework
- Exposes tools: `get_weather()`, `calculate()`
- Exposes resource: `weather://{location}`
- Exposes prompt: `weather_report()`
- Runs on stdio transport for client connections

**get_mcp_tools.py** - Utility for MCP tool discovery
- Connects to all configured servers in mcp.json
- Lists available tools with schemas
- Used by `chatwithtools.py` during initialization

**gradiomcp.py** - Gradio UI example with MCP server capability
- Demonstrates Gradio's `mcp_server=True` feature
- Exposes `letter_counter()` as both web UI and MCP tool

### Configuration

**mcp.json** - Defines MCP servers for client applications
```json
{
  "mcpServers": {
    "server_name": {
      "command": "python3",
      "args": ["server.py"],
      "env": {}
    }
  }
}
```

Used by `chatwithtools.py` and `get_mcp_tools.py` to connect to servers.

### Key Integration Patterns

**Tool Execution Flow** (chatwithtools.py):
1. Initialize: Load mcp.json, connect to each server, fetch tool schemas
2. Map tool names to their hosting servers
3. Convert MCP tool schemas to OpenAI function format
4. On tool call: Look up server, connect via stdio, execute tool, return result
5. Each tool execution creates a fresh stdio connection to the MCP server

**MCP Client Session Lifecycle**:
- Uses `stdio_client()` context manager for server connection
- Each connection: initialize session → execute operation → cleanup
- Connections are ephemeral (not pooled)

**Gradio MCP Integration**:
- `demo.launch(mcp_server=True)` automatically exposes Gradio function as MCP tool
- Runs both HTTP server (web UI) and stdio MCP server simultaneously

## Dependencies

Core dependencies (from pyproject.toml):
- `gradio[mcp]>=5.34.0` - Web UI framework with MCP support
- `openai>=2.14.0` - OpenAI API client
- MCP SDK (via gradio[mcp]): `mcp`, `aiofiles` for async MCP operations

## Important Notes

- All MCP servers use **stdio transport** (stdin/stdout communication)
- `chatwithtools.py` creates new server connections per tool call (not persistent)
- Environment variables must be set before running (OPENAI_API_KEY)
- The project uses async/await throughout for MCP operations
- Tool schemas follow OpenAI function calling format after conversion
