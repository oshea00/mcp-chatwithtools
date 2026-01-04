from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Weather Service")


# Tool implementation
@mcp.tool()
def get_weather(location: str) -> str:
    """Get the current weather for a specified location."""
    return f"Weather in {location}: Sunny, 72°F"


@mcp.tool()
def calculate(operator: str, argument1: str, argument2: str) -> str:
    """Provide a basic four function calculator that can add, subtract, multiply or divide two numeric arguments"""
    try:
        arg1 = float(argument1)
        arg2 = float(argument2)
        if operator == "+":
            return str(arg1 + arg2)
        elif operator == "-":
            return str(arg1 - arg2)
        elif operator == "*":
            return str(arg1 * arg2)
        elif operator == "/":
            return str(arg1 / arg2)
    except Exception as err:
        return err


# Resource implementation
@mcp.resource("weather://{location}")
def weather_resource(location: str) -> str:
    """Provide weather data as a resource."""
    return f"Weather data for {location}: Sunny, 72°F"


# Prompt implementation
@mcp.prompt()
def weather_report(location: str) -> str:
    """Create a weather report prompt."""
    return f"""You are a weather reporter. Weather report for {location}?"""


# Run the server
if __name__ == "__main__":
    mcp.run()
