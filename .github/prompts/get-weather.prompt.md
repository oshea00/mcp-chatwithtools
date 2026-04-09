---
description: Use this agent to get the weather using mcpi cli
name: weather
argument-hint: /weather <city> [state] [country]
agent: agent
tools:
  - execute/runInTerminal
  - search/fileSearch
  - search/textSearch
  - read/readFile
  - edit/createFile
  - edit/editFiles
  - search/codebase
  - search/listDirectory
  - search/usages
  - read/problems
  - todo
  - execute/getTerminalOutput
  - execute/killTerminal
---


# Get Weather

Get current weather conditions using the local MCP weather server via `mcpi` in batch mode.

Examples:
- `/weather Seattle`
- `/weather Portland Oregon`
- `/weather London UK`

## Instructions

Parse the arguments provided after `/weather`:
- First word: city (required)
- Second word: state (optional)
- Third word: country (optional)

Build the JSON args object from the parsed arguments, then run this command:

**City only:**
```bash
mcpi --timeout 20 --mcp-config mcp.json --server utilities --tool get_weather --args '{"city":"<city>"}'
```

**City + state:**
```bash
mcpi --timeout 20 --mcp-config mcp.json --server utilities --tool get_weather --args '{"city":"<city>","state":"<state>"}'
```

**City + state + country:**
```bash
mcpi --timeout 20 --mcp-config mcp.json --server utilities --tool get_weather --args '{"city":"<city>","state":"<state>","country":"<country>"}'
```

If mcpi command is not available then suggest using cargo to install it. This will, of course require rust tooling. The crates url is [mcpi](https://crates.io/crates/mcpi)
```bash
cargo install mcpi
```

Display the tool output directly to the user. If the command fails, report the error and suggest checking that the weather server is running (`WEATHER_BASE_URL=http://localhost:8008`).



