# MCP Course

A learning project demonstrating how to integrate the Model Context Protocol (MCP) into chat applications. This repository shows practical patterns for connecting OpenAI's LLM with MCP servers to enable dynamic tool discovery and execution.

## Overview

This project demonstrates how to integrate MCP servers so they can be called as tools in an application using OpenAI-compatible API calls that take an array of tool definitions.

The architecture shows how to cleanly separate concerns when integrating MCP into LLM applications, making it easy to add new tools without modifying application code.

## Features

- **Dynamic Tool Discovery**: Automatically discovers all tools from configured MCP servers at runtime
- **Multi-Server Support**: Connect to multiple MCP servers simultaneously
- **Format Translation**: Seamlessly converts between MCP and OpenAI function calling formats
- **Interactive Chat**: Example application that implements conversation context with multi-turn tool usage

## Prerequisites

- Python 3.12 or higher
- OpenAI API key
- `uv` package manager (recommended) or `pip`

## Installation

### Using uv 

```bash
# Install dependencies
uv sync
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

# Architecture

## MCP Architecture Overview

![mcp architecture](images/mcparch.png)

## Course Application Architecture

`chatwithtools.py` demonstrates how to integrate MCP (Model Context Protocol) into a "tools with chat" application. It shows a clean architectural pattern with two key components:

1. **ChatSession** - Orchestrates the chat completions workflow, using the `get_tools()` function to format MCP tools for OpenAI's function calling API
2. **MCPToolExecutor** - Acts as a translation layer, converting OpenAI tool call responses into MCP server calls and completing the tool execution sequence

This pattern enables an OpenAI LLM to dynamically discover and call tools hosted on any MCP server without hardcoding tool definitions.
The system consists of four main participants:

1. **User** - Interacts via command-line interface
2. **ChatSession** - Orchestrates conversation flow and OpenAI API communication
3. **MCPToolExecutor** - Translates between OpenAI tool calls and MCP server protocol
4. **MCP Servers** - External processes providing tools via stdio (e.g., weather, calculator)

## Component Description

### ChatSession Class

The `ChatSession` class implements the "tools with chat" pattern, orchestrating the complete conversation flow with OpenAI:

**Responsibilities:**
- **Chat Orchestration**: Manages conversation history and sends requests to OpenAI with tools array
- **Tool Array Preparation**: Calls `MCPToolExecutor.initialize_tools()` to get MCP tools formatted for OpenAI
- **Tool Call Detection**: Monitors OpenAI responses for `tool_calls` array
- **Tool Execution Coordination**: Delegates tool execution to MCPToolExecutor and adds results to conversation
- **Response Synthesis**: Sends tool results back to OpenAI for final response generation

**Key Methods:**
- `initialize()` - Loads MCP tools via `tool_executor.initialize_tools()` for the tools array
- `send_message(user_message)` - Orchestrates the full chat completion cycle including tool calls
- `run()` - Interactive command-line loop

**Key Pattern:**
```python
# Phase 1: Chat with tools array
response = openai.chat.completions.create(
    model=self.model,
    messages=self.messages,
    tools=self.tools,  # Formatted by MCPToolExecutor
    tool_choice="auto"
)

# Phase 2: Execute tools if requested
if response.tool_calls:
    for tool_call in response.tool_calls:
        result = await tool_executor.execute_tool(...)
        # Add result to messages

    # Phase 3: Get final response with tool results
    response = openai.chat.completions.create(...)
```

### MCPToolExecutor Class

The `MCPToolExecutor` class acts as a **translation layer** between OpenAI's function calling format and MCP's protocol:

**Responsibilities:**
- **Tool Discovery**: Uses `get_tools()` from `get_mcp_tools.py` to fetch tools from all MCP servers
- **Format Translation**: Converts MCP tool schemas to OpenAI function calling format
- **Tool Routing**: Maps tool names to their source MCP servers
- **Call Translation**: Translates OpenAI tool call format into MCP `call_tool` requests
- **Connection Management**: Establishes stdio connections to MCP servers for each tool execution

**Key Methods:**
- `initialize_tools()` - Calls `get_tools(config_path)` and transforms schemas to OpenAI format
- `execute_tool(tool_name, arguments)` - Translates and executes tool call on appropriate MCP server

**Translation Process:**
```python
# MCP Format (from server)
{
    "name": "get_weather",
    "description": "Get weather for location",
    "inputSchema": { "type": "object", "properties": {...} }
}

# OpenAI Format (for chat completions)
{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get weather for location",
        "parameters": { "type": "object", "properties": {...} }
    }
}
```

### get_tools() Function (from get_mcp_tools.py)

Utility function used by MCPToolExecutor during initialization:

**Responsibilities:**
- Loads `mcp.json` configuration
- Connects to each MCP server via stdio
- Calls `session.list_tools()` to retrieve tool definitions
- Returns array of tools with their schemas in MCP format

**Returns:**
```python
[
    {
        "server": "utilities",
        "tools": [
            {
                "name": "get_weather",
                "description": "...",
                "inputSchema": {...}
            }
        ],
        "tool_count": 2
    }
]
```

### Configuration

The system uses an `mcp.json` configuration file that defines MCP servers:

```json
{
  "mcpServers": {
    "utilities": {
      "command": "python3",
      "args": ["server.py"],
      "env": {}
    }
  }
}
```

## Interaction Flow

### Initialization Sequence

This diagram shows how MCP tools are discovered and formatted for OpenAI during startup:
![intialization flow](images/initialize-flow.gif)

```mermaid
sequenceDiagram
    participant Main as main()
    participant Chat as ChatSession
    participant Executor as MCPToolExecutor
    participant GetTools as get_tools()
    participant MCP1 as MCP Server 1
    participant MCP2 as MCP Server 2

    Main->>Chat: ChatSession(config_path, model)
    Chat->>Executor: MCPToolExecutor(config_path)
    Executor->>Executor: Load mcp.json

    Main->>Chat: await chat.initialize()
    Chat->>Executor: await initialize_tools()

    Note over Executor,GetTools: Tool Discovery Phase
    Executor->>GetTools: await get_tools(config_path)
    GetTools->>GetTools: Load mcp.json

    par Connect to all servers
        GetTools->>MCP1: stdio_client() connection
        GetTools->>MCP1: session.initialize()
        GetTools->>MCP1: session.list_tools()
        MCP1->>GetTools: [tool1, tool2] (MCP format)
    and
        GetTools->>MCP2: stdio_client() connection
        GetTools->>MCP2: session.initialize()
        GetTools->>MCP2: session.list_tools()
        MCP2->>GetTools: [tool3] (MCP format)
    end

    GetTools->>Executor: [{server: "srv1", tools: [...]}, ...]

    Note over Executor: Translation Phase
    loop For each server's tools
        Executor->>Executor: Convert MCP schema → OpenAI format
        Executor->>Executor: Map tool_name → server_name
    end

    Executor->>Chat: [OpenAI formatted tools array]
    Chat->>Main: Ready with tools

    Note over Chat: Now ready to send chat.completions<br/>with tools parameter
```

### Standard Message Flow (No Tools)

![standard flow](images/standardflow.gif)

```mermaid
sequenceDiagram
    participant User
    participant Chat as ChatSession
    participant LLM as OpenAI LLM
    
    User->>Chat: Enter message
    Chat->>LLM: Send message + available tools
    LLM->>Chat: Response (no tool calls)
    Chat->>User: Display response
```

### Tool-Assisted Message Flow

This diagram shows the complete sequence when OpenAI requests tool execution:
![mcp tool flow](images/sequence-animation.gif)

```mermaid
sequenceDiagram
    participant User
    participant Chat as ChatSession
    participant OpenAI as OpenAI API
    participant Executor as MCPToolExecutor<br/>(Translation Layer)
    participant MCP as MCP Server

    User->>Chat: "What's the weather in Paris?"

    Note over Chat,OpenAI: Phase 1: Initial Chat Completion
    Chat->>Chat: Add user message to history
    Chat->>OpenAI: chat.completions.create(<br/>messages=[...],<br/>tools=[...],<br/>tool_choice="auto")
    OpenAI->>Chat: Response with tool_calls array:<br/>[{id: "call_123", function: {<br/>name: "get_weather",<br/>arguments: '{"location": "Paris"}'}}]

    Note over Chat,MCP: Phase 2: Tool Execution via Translation Layer
    Chat->>Chat: Detect tool_calls in response
    Chat->>Chat: Add assistant message with tool_calls to history

    loop For each tool_call
        Chat->>Executor: execute_tool(<br/>"get_weather",<br/>{"location": "Paris"})

        Note over Executor: Translate OpenAI → MCP
        Executor->>Executor: Lookup server for "get_weather"<br/>→ "utilities" server
        Executor->>MCP: stdio_client(command, args)
        Executor->>MCP: session.initialize()
        Executor->>MCP: session.call_tool(<br/>"get_weather",<br/>{"location": "Paris"})
        MCP->>Executor: CallToolResult:<br/>content: [TextContent(<br/>text="Weather in Paris: Sunny, 72°F")]

        Note over Executor: Extract result
        Executor->>Executor: Extract text from content array
        Executor->>Chat: "Weather in Paris: Sunny, 72°F"

        Chat->>Chat: Add tool result to history:<br/>{role: "tool",<br/>tool_call_id: "call_123",<br/>content: "..."}
    end

    Note over Chat,OpenAI: Phase 3: Final Response Synthesis
    Chat->>OpenAI: chat.completions.create(<br/>messages=[..., tool_results])
    OpenAI->>Chat: Final response synthesized<br/>from tool results
    Chat->>User: "The weather in Paris is<br/>sunny with 72°F"
```

### Multi-Tool Sequential Flow

This diagram shows how multiple tool calls are handled sequentially:

```mermaid
sequenceDiagram
    participant User
    participant Chat as ChatSession
    participant OpenAI as OpenAI API
    participant Executor as MCPToolExecutor
    participant MCP1 as MCP Server<br/>(utilities)

    User->>Chat: "What's the weather in Paris<br/>and calculate 25 + 17?"

    Note over Chat,OpenAI: Phase 1: Request with Multiple Tools
    Chat->>OpenAI: chat.completions.create(messages, tools)
    OpenAI->>Chat: tool_calls: [<br/>{name: "get_weather", args: {...}},<br/>{name: "calculate", args: {...}}<br/>]

    Chat->>Chat: Add assistant msg with tool_calls

    Note over Chat,MCP1: Phase 2: Execute Each Tool (Sequential)
    loop For each tool_call in tool_calls
        Chat->>Executor: execute_tool(name, args)

        Note over Executor: Translation Layer
        Executor->>Executor: Map tool → server
        Executor->>MCP1: stdio connection + initialize
        Executor->>MCP1: call_tool(name, args)
        MCP1->>Executor: Result
        Executor->>Chat: Formatted result string

        Chat->>Chat: Add to history:<br/>{role: "tool", tool_call_id, content}
    end

    Note over Chat,OpenAI: Phase 3: Synthesize Final Response
    Chat->>OpenAI: chat.completions.create(<br/>messages=[..., all tool results])
    OpenAI->>Chat: Synthesized answer using all results
    Chat->>User: "Weather: Sunny, 72°F<br/>Calculation: 25 + 17 = 42"
```

# Usage

### Basic Usage

```bash
export OPENAI_API_KEY="your-api-key"
python chatwithtools.py mcp.json
```

### With Custom Model

```bash
python chatwithtools.py mcp.json gpt-4o
```

### Example Interaction

```
Chat session started. Type 'exit' or 'quit' to end the session.
============================================================

You: help me find the product of 5 and 6
Calling tool: calculate with args: {'operator': 'multiply', 'argument1': '5', 'argument2': '6'}
[01/04/26 15:13:19] INFO     Processing request of type CallToolRequest                                                                            server.py:558

Assistant: The product of 5 and 6 is 30.

You: what is the weather in Paris
Calling tool: get_weather with args: {'location': 'Paris'}
[01/04/26 15:13:31] INFO     Processing request of type CallToolRequest                                                                            server.py:558

Assistant: The weather in Paris is sunny with a temperature of 72°F.

You: exit
Goodbye!
```