# MCP Tool Logging

All MCP tools now include detailed logging to show progress during execution.

## Logging Format

```
[HH:MM:SS] <emoji> <message>
```

- **Timestamp**: Shows when each step occurs
- **Emoji**: Visual indicator of the operation type
- **Message**: Detailed progress information

Logs are printed to **stderr** so they don't interfere with JSON responses.

## Example Logging Output

### fetch_fires Tool

```
[10:30:15] 🔥 Fetching fires for oregon (last 2 days)...
[10:30:18] ✓ Found 47 fires (3 industrial filtered)
```

### enrich_weather Tool

```
[10:31:00] 🌤️  Loading fire data for weather enrichment...
[10:31:00]    Processing 47 fires
[10:31:01]    Fetching weather data from NOAA NWS API...
[10:31:01]    ⚠️  This may take 1-2 seconds per fire
[10:32:45]    Saving enriched data...
[10:32:46] ✓ Added weather data to 42/47 fires
```

**Note:** Weather enrichment shows a warning about duration since it's ~1-2 seconds per fire.

### enrich_aqi Tool

```
[10:33:00] 💨 Loading fire data for AQI enrichment...
[10:33:00]    Processing 47 fires
[10:33:01]    Fetching AQI data from EPA AirNow API...
[10:33:05]    Saving enriched data...
[10:33:06] ✓ Added AQI data to 12/47 fires
```

### enrich_purpleair Tool

```
[10:34:00] 🟣 Loading fire data for PurpleAir enrichment (radius: 50km)...
[10:34:00]    Processing 47 fires
[10:34:01]    Fetching PM2.5 data from PurpleAir sensors...
[10:34:15]    Saving enriched data...
[10:34:16] ✓ Added PurpleAir data to 8/47 fires
```

### visualize_fires Tool

```
[10:35:00] 🗺️  Generating 2 map visualizations...
[10:35:00]    Loading fire data...
[10:35:01]    Creating basic fire map...
[10:35:03]    Creating risk heatmap...
[10:35:05] ✓ Generated 2 map visualizations
```

### get_fire_stats Tool

```
[10:36:00] 📊 Calculating fire statistics...
[10:36:01] ✓ Stats: 47 fires, 42 with weather, 12 with AQI, 8 with PM2.5
```

## Emoji Legend

- 🔥 **Fire data fetching** - Fetching from NASA FIRMS
- 🌤️ **Weather enrichment** - NOAA weather data
- 💨 **AQI enrichment** - EPA AirNow air quality
- 🟣 **PurpleAir enrichment** - PM2.5 sensor data
- 🗺️ **Visualization** - Generating maps
- 📊 **Statistics** - Calculating stats
- ✓ **Success** - Operation completed
- ❌ **Error** - Something went wrong
- ⚠️ **Warning** - Important notice

## Viewing Logs

### In Gradio Web Interface

When you run the Gradio web interface:

```bash
uv run python web/gradio_app.py
```

You'll see logs in the terminal where you launched it:

```
✓ Found 4 Ollama models: llama3.2:3b, llama3.2-vision:11b, qwen2.5:14b, llama3.1:8b
✓ qwen2.5:14b model found
Running on local URL:  http://0.0.0.0:7860

[10:30:15] 🔥 Fetching fires for oregon (last 2 days)...
[10:30:18] ✓ Found 47 fires (3 industrial filtered)
[10:31:00] 🌤️  Loading fire data for weather enrichment...
[10:31:01]    Processing 47 fires
[10:31:01]    Fetching weather data from NOAA NWS API...
[10:31:01]    ⚠️  This may take 1-2 seconds per fire
```

### In MCP Server Mode

When running the MCP server directly:

```bash
uv run python mcp_server/server.py
```

Logs appear on stderr, separate from the JSON-RPC communication on stdout.

## Error Handling

When API keys are missing or errors occur:

```
[10:37:00] 💨 Loading fire data for AQI enrichment...
[10:37:00]    Processing 47 fires
[10:37:00] ❌ AIRNOW_API_KEY not found in .env
```

```
[10:38:00] 🟣 Loading fire data for PurpleAir enrichment (radius: 50km)...
[10:38:00]    Processing 47 fires
[10:38:00] ❌ PURPLEAIR_API_KEY not found in .env
```

## Benefits

1. **Progress visibility** - See what's happening in real-time
2. **Time estimation** - Understand how long operations take
3. **Debugging** - Identify where slow operations or errors occur
4. **User feedback** - Know the system is working, not frozen
5. **Data coverage** - See how many fires got enriched with each data source

## Example: Full Workflow

```
User: "Fetch fires in oregon and include weather information"

[10:30:15] 🔥 Fetching fires for oregon (last 2 days)...
[10:30:18] ✓ Found 47 fires (3 industrial filtered)

[Tool returns JSON to LLM]

LLM: "I found 47 fires in Oregon. Now I'll add weather data..."

[10:31:00] 🌤️  Loading fire data for weather enrichment...
[10:31:00]    Processing 47 fires
[10:31:01]    Fetching weather data from NOAA NWS API...
[10:31:01]    ⚠️  This may take 1-2 seconds per fire
[10:32:45]    Saving enriched data...
[10:32:46] ✓ Added weather data to 42/47 fires

[Tool returns JSON to LLM]

LLM: "I've enriched 42 out of 47 fires with current weather data including 
      temperature, humidity, wind speed, and precipitation probability."
```

## Implementation

The logging is implemented using a simple helper function in `mcp_server/tools.py`:

```python
def log(message: str):
    """Print timestamped log message to stderr for visibility."""
    from datetime import datetime
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", file=sys.stderr, flush=True)
```

All tool functions call this helper at key points:
- Start of operation
- Progress updates
- Completion/success
- Errors or warnings
