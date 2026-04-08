---
name: get-weather
description: Get current weather for a city using the MCP weather server via mcpi in batch mode. Usage: /get-weather <city> [state] [country]
tools: Bash
---

# Get Weather

Get current weather conditions using the local MCP weather server via `mcpi` in batch mode.

## Usage

`/get-weather <city> [state] [country]`

Examples:
- `/get-weather Seattle`
- `/get-weather Portland Oregon`
- `/get-weather London UK`

## Instructions

Parse the arguments provided after `/get-weather`:
- First word: city (required)
- Second word: state (optional)
- Third word: country (optional)

Build the JSON args object from the parsed arguments, then run this command:

```bash
MCPI=/home/oshea00/repos/mcpinspector/target/debug/mcpi
MCP_CONFIG=/home/oshea00/repos/mcp-chatwithtools/mcp.json
```

**City only:**
```bash
$MCPI --timeout 20 --mcp-config $MCP_CONFIG --server utilities --tool get_weather --args '{"city":"<city>"}'
```

**City + state:**
```bash
$MCPI --timeout 20 --mcp-config $MCP_CONFIG --server utilities --tool get_weather --args '{"city":"<city>","state":"<state>"}'
```

**City + state + country:**
```bash
$MCPI --timeout 20 --mcp-config $MCP_CONFIG --server utilities --tool get_weather --args '{"city":"<city>","state":"<state>","country":"<country>"}'
```

Display the tool output directly to the user. If the command fails, report the error and suggest checking that the weather server is running (`WEATHER_BASE_URL=http://localhost:8008`).
