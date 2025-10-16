"""
Gradio Web Interface for Wildfire Risk Monitoring System

Combines LLM chat interface with interactive map visualization.
Uses Qwen2.5:14b via Ollama for natural language interaction with MCP tools.
"""

import gradio as gr
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import geopandas as gpd
import pandas as pd
from pathlib import Path
import json
import os
from typing import List, Tuple, Optional
import asyncio
from datetime import datetime

# Ollama for LLM
try:
    import ollama
except ImportError:
    print("Installing ollama-python...")
    import subprocess

    subprocess.check_call(["pip", "install", "ollama"])
    import ollama

# Import MCP tools
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tools import (
    fetch_fires_tool,
    enrich_weather_tool,
    enrich_aqi_tool,
    enrich_purpleair_tool,
    visualize_fires_tool,
    get_fire_stats_tool,
)


class WildfireAssistant:
    """LLM-powered assistant with access to wildfire monitoring tools."""

    def __init__(self, model="qwen2.5:14b"):
        self.model = model
        self.conversation_history = []

        # Define available tools for the LLM
        self.tools = {
            "fetch_fires": {
                "description": "Fetch active fire data from NASA FIRMS for a region, with optional weather/AQI/PM2.5 enrichment",
                "parameters": {
                    "region": "Region name (e.g., 'california', 'colorado', 'conus')",
                    "days_back": "Number of days to look back (default: 2)",
                    "filter_industrial": "Filter industrial heat sources (default: true)",
                    "use_weather": "Include NOAA weather data (default: false, slow for >100 fires)",
                    "use_aqi": "Include EPA AirNow air quality data (default: false)",
                    "use_purpleair": "Include PurpleAir PM2.5 sensor data (default: false)",
                },
                "function": fetch_fires_tool,
            },
            "enrich_weather": {
                "description": "Enrich fire data with NOAA weather information",
                "parameters": {"limit": "Maximum fires to enrich (optional)"},
                "function": enrich_weather_tool,
            },
            "enrich_aqi": {
                "description": "Enrich fire data with EPA AirNow air quality data",
                "parameters": {"limit": "Maximum fires to enrich (optional)"},
                "function": enrich_aqi_tool,
            },
            "enrich_purpleair": {
                "description": "Enrich fire data with PurpleAir PM2.5 sensor data",
                "parameters": {
                    "limit": "Maximum fires to enrich (optional)",
                    "radius_km": "Search radius in km (default: 50)",
                },
                "function": enrich_purpleair_tool,
            },
            "visualize_fires": {
                "description": "Generate interactive map visualizations",
                "parameters": {
                    "map_types": "Types of maps: basic, risk_heatmap, aqi, purpleair"
                },
                "function": visualize_fires_tool,
            },
            "get_fire_stats": {
                "description": "Get summary statistics about current fire data",
                "parameters": {},
                "function": get_fire_stats_tool,
            },
        }

    def get_system_prompt(self) -> str:
        """Generate system prompt with tool descriptions."""
        tools_desc = "\n".join(
            [f"- {name}: {info['description']}" for name, info in self.tools.items()]
        )

        return f"""You are a wildfire monitoring assistant with access to the following tools:

{tools_desc}

TERMINOLOGY GUIDE:
- "particulates", "PM2.5", "smoke", "air quality sensors" → Use enrich_purpleair (real-time sensor data)
- "AQI", "air quality index", "EPA air quality" → Use enrich_aqi (official EPA data)
- "weather", "temperature", "wind", "humidity", "precipitation" → Use enrich_weather

IMPORTANT RULES:
1. Call ONE tool at a time. Wait for the result before calling another tool.
2. Use ONLY valid JSON format for tool calls.
3. After getting a tool result, explain it to the user in natural language.
4. For multi-step requests, tell the user you're doing the FIRST step and will do the rest after.

When a user asks to perform an action, respond with ONLY a JSON function call:
{{"tool": "tool_name", "arguments": {{"param": "value"}}}}

Examples:
- "Fetch fires in California" → {{"tool": "fetch_fires", "arguments": {{"region": "california"}}}}
- "Fetch fires and weather in California" → {{"tool": "fetch_fires", "arguments": {{"region": "california", "use_weather": true}}}}
- "Fetch fires with AQI and PM2.5 in Georgia" → {{"tool": "fetch_fires", "arguments": {{"region": "georgia", "use_aqi": true, "use_purpleair": true}}}}
- "Show me fire statistics" → {{"tool": "get_fire_stats", "arguments": {{}}}}
- "Add weather data" → {{"tool": "enrich_weather", "arguments": {{}}}}
- "Include particulate data" → {{"tool": "enrich_purpleair", "arguments": {{}}}}
- "Add PM2.5" → {{"tool": "enrich_purpleair", "arguments": {{}}}}
- "Add AQI" → {{"tool": "enrich_aqi", "arguments": {{}}}}

IMPORTANT: The fetch_fires tool can optionally include weather/AQI/PM2.5 during the initial fetch using use_weather, use_aqi, use_purpleair parameters.
Alternatively, you can fetch fires first, then use the separate enrich_* tools to add data afterward.

If the user asks a general question, answer directly without using tools.
"""

    async def chat(self, user_message: str) -> Tuple[str, Optional[dict]]:
        """
        Process user message and execute tools if needed.

        Returns:
            (response_text, tool_result_dict)
        """
        import sys

        print(f"\n[LLM] User: {user_message}", file=sys.stderr, flush=True)

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})

        # Prepare messages for LLM
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            *self.conversation_history[-10:],  # Keep last 10 messages for context
        ]

        # Get LLM response
        try:
            print(f"[LLM] Querying {self.model}...", file=sys.stderr, flush=True)
            response = ollama.chat(
                model=self.model,
                messages=messages,
            )
            assistant_message = response["message"]["content"]
            print(
                f"[LLM] Response: {assistant_message[:200]}...",
                file=sys.stderr,
                flush=True,
            )
        except Exception as e:
            print(f"[LLM] Error: {e}", file=sys.stderr, flush=True)
            return f"Error communicating with LLM: {str(e)}", None

        # Check if response contains a tool call
        tool_result = None
        assistant_message_stripped = assistant_message.strip()

        # Handle multi-line responses - extract just the JSON if present
        if "{" in assistant_message_stripped and "tool" in assistant_message_stripped:
            print(
                f"[TOOL] Detected potential tool call in response",
                file=sys.stderr,
                flush=True,
            )

            # Try to extract JSON from the response
            start = assistant_message_stripped.find("{")
            end = assistant_message_stripped.rfind("}") + 1

            if start != -1 and end > start:
                json_str = assistant_message_stripped[start:end]

                # Handle multiple JSONs on separate lines - take only the first
                if "\n{" in json_str:
                    json_str = json_str[: json_str.find("\n{")]
                    if not json_str.endswith("}"):
                        json_str += "}"

                try:
                    print(
                        f"[TOOL] Parsing tool call: {json_str}",
                        file=sys.stderr,
                        flush=True,
                    )
                    tool_call = json.loads(json_str)
                    tool_name = tool_call.get("tool")
                    tool_args = tool_call.get("arguments", {})

                    if tool_name in self.tools:
                        print(
                            f"[TOOL] Executing {tool_name} with args: {tool_args}",
                            file=sys.stderr,
                            flush=True,
                        )

                        # Execute tool
                        tool_fn = self.tools[tool_name]["function"]
                        result_json = await tool_fn(tool_args)
                        tool_result = json.loads(result_json)

                        print(
                            f"[TOOL] Result: {tool_result.get('message', 'Success')}",
                            file=sys.stderr,
                            flush=True,
                        )

                        # Generate natural language response about the result
                        print(
                            f"[LLM] Asking LLM to explain result...",
                            file=sys.stderr,
                            flush=True,
                        )
                        explain_messages = messages + [
                            {"role": "assistant", "content": json_str},
                            {
                                "role": "user",
                                "content": f"Tool result: {result_json}\n\nExplain this result to the user in 2-3 sentences. DO NOT include any new tool calls - just explain what happened.",
                            },
                        ]

                        try:
                            explain_response = ollama.chat(
                                model=self.model,
                                messages=explain_messages,
                            )
                            assistant_message = explain_response["message"]["content"]

                            print(
                                f"[LLM] Explanation: {assistant_message}",
                                file=sys.stderr,
                                flush=True,
                            )

                            # Check if the explanation contains a follow-up tool call
                            # (for multi-step requests like "fetch fires and add weather")
                            if "{" in assistant_message and "tool" in assistant_message:
                                print(
                                    f"[LLM] Follow-up tool call detected in explanation. User should send another message to continue.",
                                    file=sys.stderr,
                                    flush=True,
                                )
                                # Note: We don't execute it here - the user will see the explanation
                                # and the chat loop will pick up the tool call on the next interaction
                        except Exception as e:
                            print(
                                f"[LLM] Error generating explanation: {e}",
                                file=sys.stderr,
                                flush=True,
                            )
                            # Fallback to simple message from tool result
                            assistant_message = tool_result.get(
                                "message", "Tool executed successfully."
                            )
                    else:
                        print(
                            f"[TOOL] Unknown tool: {tool_name}",
                            file=sys.stderr,
                            flush=True,
                        )
                        assistant_message = f"I tried to use a tool '{tool_name}' but it's not available. Available tools: {', '.join(self.tools.keys())}"

                except json.JSONDecodeError as e:
                    print(f"[TOOL] JSON parse error: {e}", file=sys.stderr, flush=True)
                    print(
                        f"[TOOL] Attempted to parse: {json_str}",
                        file=sys.stderr,
                        flush=True,
                    )
                    # Not valid JSON, return the original message

        # Add assistant response to history
        self.conversation_history.append(
            {"role": "assistant", "content": assistant_message}
        )

        return assistant_message, tool_result


def load_current_map(map_type: str = "basic") -> go.Figure:
    """Load and display the current fire map."""
    try:
        data_dir = Path("data/processed")
        fires_file = data_dir / "active_fires.geojson"

        # Check if file exists before trying to read
        if not fires_file.exists():
            return create_empty_map("No fire data available. Fetch fires to begin.")

        fires_gdf = gpd.read_file(fires_file)

        fires_df = fires_gdf.copy()
        fires_df["lon"] = fires_df.geometry.x
        fires_df["lat"] = fires_df.geometry.y

        center_lat = fires_df["lat"].mean()
        center_lon = fires_df["lon"].mean()

        if map_type == "basic":
            fig = px.scatter_map(
                fires_df,
                lat="lat",
                lon="lon",
                color="risk_category",
                color_discrete_map={
                    "Low": "yellow",
                    "Moderate": "orange",
                    "High": "red",
                },
                hover_data=["risk_score", "confidence", "bright_ti4"],
                zoom=5,
                center={"lat": center_lat, "lon": center_lon},
                title=f"Active Fires ({len(fires_df)} detections)",
                map_style="carto-positron",
            )
        elif map_type == "risk_heatmap":
            fig = px.density_map(
                fires_df,
                lat="lat",
                lon="lon",
                z="risk_score",
                radius=15,
                zoom=5,
                center={"lat": center_lat, "lon": center_lon},
                color_continuous_scale="YlOrRd",
                title="Fire Risk Heatmap",
                map_style="carto-positron",
            )
            fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), autosize=True)
        elif map_type == "aqi":
            # Check if AQI column exists and has data
            if "aqi" in fires_df.columns:
                fires_aqi = fires_df[fires_df["aqi"].notna()]
                if len(fires_aqi) > 0:
                    fig = px.density_map(
                        fires_aqi,
                        lat="lat",
                        lon="lon",
                        z="aqi",
                        radius=15,
                        zoom=5,
                        center={"lat": center_lat, "lon": center_lon},
                        color_continuous_scale="YlOrRd",
                        title=f"AQI Heatmap ({len(fires_aqi)} fires with data)",
                        map_style="carto-positron",
                    )
                    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), autosize=True)
                else:
                    return create_empty_map(
                        "No AQI data available. Use 'Add AQI' to enrich fires."
                    )
            else:
                return create_empty_map(
                    "No AQI data available. Use 'Add AQI' to enrich fires."
                )
        elif map_type == "purpleair":
            # Check if PurpleAir column exists and has data
            if "pa_pm25" in fires_df.columns:
                fires_pa = fires_df[fires_df["pa_pm25"].notna()]
                if len(fires_pa) > 0:
                    fig = px.density_map(
                        fires_pa,
                        lat="lat",
                        lon="lon",
                        z="pa_pm25",
                        radius=15,
                        zoom=5,
                        center={"lat": center_lat, "lon": center_lon},
                        color_continuous_scale="YlOrRd",
                        title=f"PM2.5 Heatmap ({len(fires_pa)} fires with data)",
                        map_style="carto-positron",
                    )
                    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), autosize=True)
                else:
                    return create_empty_map(
                        "No PurpleAir data available. Use 'Add particulate data' to enrich fires."
                    )
            else:
                return create_empty_map(
                    "No PurpleAir data available. Use 'Add particulate data' to enrich fires."
                )
        else:
            fig = create_empty_map("Unknown map type")

        fig.update_layout(height=600)
        return fig

    except Exception as e:
        import sys

        print(f"[MAP] Error loading map: {e}", file=sys.stderr, flush=True)
        return create_empty_map("Error loading map. Check terminal for details.")


def create_empty_map(message: str) -> go.Figure:
    """Create an empty map with a message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=20),
    )
    fig.update_layout(
        height=600,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def clear_all_data() -> tuple[str, go.Figure]:
    """
    Clear all fire data from database and delete GeoJSON files.

    Returns:
        (status_message, empty_map)
    """
    import sys
    from src.database import init_database

    try:
        print("[CLEAR] Starting data cleanup...", file=sys.stderr, flush=True)

        # Clear database
        db_path = os.getenv("DATABASE_PATH", "data/wildfire.duckdb")
        conn = init_database(db_path)

        # Count records before deletion
        deleted_buffers = conn.execute("SELECT COUNT(*) FROM fire_buffers").fetchone()[
            0
        ]
        deleted_fires = conn.execute("SELECT COUNT(*) FROM fires").fetchone()[0]

        # Delete all records from tables
        conn.execute("DELETE FROM fire_buffers")
        conn.execute("DELETE FROM fires")

        conn.commit()
        print(
            f"[CLEAR] Deleted {deleted_fires} fires and {deleted_buffers} buffers from database",
            file=sys.stderr,
            flush=True,
        )

        # Delete GeoJSON files
        data_dir = Path("data/processed")
        deleted_files = []

        geojson_files = [
            "active_fires.geojson",
            "fire_buffers.geojson",
            "excluded_industrial_fires.geojson",
            "region_metadata.json",
        ]

        for filename in geojson_files:
            filepath = data_dir / filename
            if filepath.exists():
                filepath.unlink()
                deleted_files.append(filename)
                print(f"[CLEAR] Deleted {filename}", file=sys.stderr, flush=True)

        # Delete HTML visualization files
        html_files = list(data_dir.glob("fires_*.html"))
        for filepath in html_files:
            filepath.unlink()
            deleted_files.append(filepath.name)
            print(f"[CLEAR] Deleted {filepath.name}", file=sys.stderr, flush=True)

        print(f"[CLEAR] ✓ Data cleanup complete", file=sys.stderr, flush=True)

        status_msg = f"✓ Cleared all data:\n- Deleted {deleted_fires} fires from database\n- Deleted {deleted_buffers} buffers from database\n- Removed {len(deleted_files)} files from data/processed/"
        empty_map = create_empty_map("All data cleared. Fetch new fire data to begin.")

        return status_msg, empty_map

    except Exception as e:
        error_msg = f"❌ Error clearing data: {str(e)}"
        print(f"[CLEAR] {error_msg}", file=sys.stderr, flush=True)
        return error_msg, create_empty_map("Error clearing data")


def create_gradio_app():
    """Create and configure the Gradio interface."""

    # Initialize assistant
    assistant = WildfireAssistant(model="qwen2.5:14b")

    # Custom CSS for better styling
    custom_css = """
    .gradio-container {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    .chat-message {
        padding: 10px;
        margin: 5px 0;
    }
    """

    with gr.Blocks(css=custom_css, title="Wildfire Risk Monitor") as app:
        gr.Markdown("""
        # 🔥 Wildfire Risk Monitoring System

        **Powered by Qwen2.5:14b** | Natural language interface to NASA FIRMS fire data

        Ask questions or give commands like:
        - "Fetch fires in California"
        - "Enrich the data with weather information"
        - "Show me fire statistics"
        - "Add air quality data"
        - "Create a risk heatmap"
        """)

        with gr.Row():
            with gr.Column(scale=1):
                # Chat interface
                gr.Markdown("### 💬 Chat with Assistant")
                chatbot = gr.Chatbot(
                    height=400,
                    label="Conversation",
                    show_label=False,
                    type="messages",  # Use modern OpenAI-style format
                )

                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Ask about wildfires or request data...",
                        show_label=False,
                        scale=4,
                    )
                    submit_btn = gr.Button("Send", scale=1, variant="primary")

                gr.Markdown("""
                **Example commands:**
                - Fetch fires in Colorado from the last 3 days
                - Add PurpleAir air quality data
                - Show me the current fire statistics
                - Generate a risk heatmap visualization
                """)

                # Status display
                status_box = gr.JSON(label="Last Tool Result", visible=True)

                # Clear data button
                gr.Markdown("---")
                gr.Markdown("### 🗑️ Data Management")
                clear_status = gr.Textbox(label="Clear Status", visible=False)
                clear_btn = gr.Button("Clear All Data", variant="stop", size="sm")

            with gr.Column(scale=2):
                # Map display
                gr.Markdown("### 🗺️ Interactive Map")

                map_selector = gr.Radio(
                    choices=["basic", "risk_heatmap", "aqi", "purpleair"],
                    value="basic",
                    label="Map Type",
                    interactive=True,
                )

                map_plot = gr.Plot(label="Fire Map", show_label=False)

                refresh_btn = gr.Button("🔄 Refresh Map", size="sm")

        # Chat interaction
        async def respond(message, chat_history):
            """Process user message and update chat."""
            # Add user message to chat (using messages format)
            chat_history = chat_history or []
            chat_history.append({"role": "user", "content": message})

            # Get assistant response
            response, tool_result = await assistant.chat(message)

            # Add assistant response to chat
            chat_history.append({"role": "assistant", "content": response})

            return "", chat_history, tool_result if tool_result else gr.update()

        # Event handlers
        submit_btn.click(
            respond,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot, status_box],
        )

        msg.submit(
            respond,
            inputs=[msg, chatbot],
            outputs=[msg, chatbot, status_box],
        )

        def update_map(map_type):
            return load_current_map(map_type)

        map_selector.change(
            update_map,
            inputs=[map_selector],
            outputs=[map_plot],
        )

        refresh_btn.click(
            update_map,
            inputs=[map_selector],
            outputs=[map_plot],
        )

        # Clear data button
        def handle_clear_data():
            """Handle clear data button click."""
            status_msg, empty_map = clear_all_data()
            return (
                status_msg,
                gr.update(visible=True),
                empty_map,
                None,
            )  # Also clear status_box

        clear_btn.click(
            handle_clear_data,
            inputs=[],
            outputs=[clear_status, clear_status, map_plot, status_box],
        )

        # Load initial map
        app.load(
            lambda: load_current_map("basic"),
            outputs=[map_plot],
        )

    return app


if __name__ == "__main__":
    # Check if Ollama is running
    try:
        response = ollama.list()
        # Handle both dict response and ListResponse object
        if hasattr(response, "models"):
            available_models = [m.model for m in response.models]
        else:
            available_models = [m["name"] for m in response.get("models", [])]

        print(
            f"✓ Found {len(available_models)} Ollama models: {', '.join(available_models)}"
        )

        if "qwen2.5:14b" not in available_models:
            print("⚠️  qwen2.5:14b not found. Pulling model...")
            print("This may take a while (model is ~9GB)")
            ollama.pull("qwen2.5:14b")
            print("✓ Model pulled successfully!")
        else:
            print("✓ qwen2.5:14b model found")

    except Exception as e:
        print(f"❌ Error: Could not connect to Ollama. Is it running?")
        print(f"   Install: https://ollama.ai")
        print(f"   Error: {e}")
        import traceback

        traceback.print_exc()
        exit(1)

    # Launch app
    app = create_gradio_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )
