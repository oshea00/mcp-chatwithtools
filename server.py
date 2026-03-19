import os
from typing import Optional
import httpx
from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Weather Service")

# Get the weather API base URL from environment variable
WEATHER_BASE_URL = os.getenv("WEATHER_BASE_URL")


# Tool implementation
@mcp.tool()
def get_weather(
    city: str, state: Optional[str] = None, country: Optional[str] = "USA"
) -> str:
    """Get the current weather for a specified location.

    Args:
        city: The city name (required)
        state: The state name (optional)
        country: The country name (optional, defaults to USA)
    """
    # Build location string for display
    location_parts = [city]
    if state:
        location_parts.append(state)
    if country and country != "USA":
        location_parts.append(country)
    location_display = ", ".join(location_parts)

    if WEATHER_BASE_URL:
        try:
            # Build query parameters
            params = {"city": city}
            if state:
                params["state"] = state
            if country:
                params["country"] = country

            # Call the weather API
            response = httpx.get(
                f"{WEATHER_BASE_URL}/weather", params=params, timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            # Format the weather data
            if "weather" in data and data["weather"]:
                periods = data["weather"]
                # Get the first period (current forecast)
                current = periods[0]
                result = f"Weather in {location_display}:\n"
                result += f"{current.get('name', 'Current')}: {current.get('shortForecast', 'N/A')}\n"
                result += f"Temperature: {current.get('temperature', 'N/A')}°{current.get('temperatureUnit', 'F')}\n"
                result += f"Wind: {current.get('windSpeed', 'N/A')} {current.get('windDirection', '')}\n"
                if current.get("detailedForecast"):
                    result += f"\nDetails: {current['detailedForecast']}"
                return result
            else:
                return f"Weather data not available for {location_display}"

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"Weather forecast not available for {location_display}. The weather service could not find forecast data for the requested location."
            return f"Error fetching weather for {location_display}: {str(e)}"
        except Exception as e:
            return f"Error fetching weather for {location_display}: {str(e)}"

    # Fallback to mock data if WEATHER_BASE_URL is not set
    return f"Weather in {location_display}: Sunny, 72°F"


@mcp.tool()
def get_forecast(
    city: str, state: Optional[str] = None, country: Optional[str] = "USA"
) -> str:
    """Get the full weather forecast (all periods) for a specified location.

    Args:
        city: The city name (required)
        state: The state name (optional)
        country: The country name (optional, defaults to USA)
    """
    # Build location string for display
    location_parts = [city]
    if state:
        location_parts.append(state)
    if country and country != "USA":
        location_parts.append(country)
    location_display = ", ".join(location_parts)

    if WEATHER_BASE_URL:
        try:
            # Build query parameters
            params = {"city": city}
            if state:
                params["state"] = state
            if country:
                params["country"] = country

            # Call the weather API
            response = httpx.get(
                f"{WEATHER_BASE_URL}/weather", params=params, timeout=10.0
            )
            response.raise_for_status()
            data = response.json()

            # Format the weather data
            if "weather" in data and data["weather"]:
                periods = data["weather"]
                result = f"Weather Forecast for {location_display}:\n\n"

                for i, period in enumerate(periods, 1):
                    result += f"{period.get('name', f'Period {i}')}:\n"
                    result += f"  Temperature: {period.get('temperature', 'N/A')}°{period.get('temperatureUnit', 'F')}\n"
                    result += f"  Conditions: {period.get('shortForecast', 'N/A')}\n"
                    result += f"  Wind: {period.get('windSpeed', 'N/A')} {period.get('windDirection', '')}\n"
                    if period.get("detailedForecast"):
                        result += f"  Details: {period['detailedForecast']}\n"
                    result += "\n"

                return result.strip()
            else:
                return f"Weather forecast not available for {location_display}"

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"Weather forecast not available for {location_display}. The weather service could not find forecast data for the requested location."
            return f"Error fetching weather forecast for {location_display}: {str(e)}"
        except Exception as e:
            return f"Error fetching weather forecast for {location_display}: {str(e)}"

    # Fallback to mock data if WEATHER_BASE_URL is not set
    return f"Weather Forecast for {location_display}:\n\nToday: Sunny, 72°F\nTonight: Clear, 55°F"


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
    # Parse location - support "City", "City, State", or "City, State, Country" format
    parts = [part.strip() for part in location.split(",")]
    city = parts[0]
    state = parts[1] if len(parts) > 1 else None
    country = parts[2] if len(parts) > 2 else "USA"

    # Reuse the get_weather logic
    return get_weather(city=city, state=state, country=country)


# Prompt implementation
@mcp.prompt()
def weather_report(location: str) -> str:
    """Create a weather report prompt."""
    return f"""You are a weather reporter. Weather report for {location}?"""


# Run the server
if __name__ == "__main__":
    mcp.run()
