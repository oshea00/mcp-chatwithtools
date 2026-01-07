# MCP Course

A learning project demonstrating how to integrate the Model Context Protocol (MCP) into chat applications. This repository shows practical patterns for connecting OpenAI's LLM with MCP servers to enable dynamic tool discovery and execution.

## Overview

This project demonstrates the "tools with chat" pattern using MCP, featuring:

- **ChatSession**: Orchestrates OpenAI chat completions with dynamic tool calling
- **MCPToolExecutor**: Acts as a translation layer between OpenAI function calling format and MCP protocol
- **get_tools()**: Utility for discovering and formatting tools from MCP servers

The architecture shows how to cleanly separate concerns when integrating MCP into LLM applications, making it easy to add new tools without modifying application code.

## Features

- **Dynamic Tool Discovery**: Automatically discovers all tools from configured MCP servers at runtime
- **Multi-Server Support**: Connect to multiple MCP servers simultaneously
- **Format Translation**: Seamlessly converts between MCP and OpenAI function calling formats
- **Interactive Chat**: Full conversation context with multi-turn tool usage
- **Gradio Integration**: Example of exposing Gradio functions as MCP tools

## Prerequisites

- Python 3.12 or higher
- OpenAI API key
- `uv` package manager (recommended) or `pip`

## Installation

### Using uv (recommended)

```bash
# Install dependencies
uv sync
```

### Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install "gradio[mcp]>=5.34.0" "openai>=2.14.0"
```

## Running the Examples

### 1. Interactive Chat with MCP Tools

The main example demonstrating the "tools with chat" pattern:

```bash
# Set your OpenAI API key (also supports .env)
export OPENAI_API_KEY="your-api-key-here"
# Optional set alternative API base URL
export OPENAI_BASE_URL="your-alt-url/v1 here"

# Run with default model (gpt-4o-mini)
python chatwithtools.py mcp.json

# Or specify a different model
python chatwithtools.py mcp.json gpt-4o
```

### Example Interaction

```
Initializing MCP tools...
[01/04/26 15:53:25] INFO     Processing request of type ListToolsRequest                                                                           server.py:558
Loaded 2 tools from MCP servers

Chat session started. Type 'exit' or 'quit' to end the session.
============================================================

You: what is the product of five and three?
Calling tool: calculate with args: {'operator': 'multiply', 'argument1': '5', 'argument2': '3'}
[01/04/26 15:53:36] INFO     Processing request of type CallToolRequest                                                                            server.py:558

Assistant: The product of five and three is fifteen (15).

You: what is the temperature in Paris right now?
Calling tool: get_weather with args: {'location': 'Paris'}
[01/04/26 15:54:01] INFO     Processing request of type CallToolRequest                                                                            server.py:558

Assistant: The current temperature in Paris is 72°F and it's sunny.

You: write a haiku about the weather in Paris

Assistant: Sunny skies above,  
Paris basking in warm light,  
Joyful hearts take flight.

You: quit
Goodbye!
```