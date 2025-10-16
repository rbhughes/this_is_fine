# Quick Start: Gradio Web Interface

Get up and running with the natural language wildfire monitoring interface in 5 minutes.

## Prerequisites

- macOS with Apple Silicon (M1/M2/M3) or Intel
- 24GB RAM recommended (16GB minimum)
- Python 3.12+ (managed by uv)

## Setup Steps

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
```

**Or download from:** https://ollama.ai

### 2. Start Ollama Service

```bash
ollama serve
```

Keep this running in a terminal window.

### 3. Pull the LLM Model

In a new terminal:

```bash
# Recommended: Qwen2.5:14b (best quality, ~10-12GB RAM)
ollama pull qwen2.5:14b

# Alternative: Llama3.2:11b (faster, ~8GB RAM)
# ollama pull llama3.2:11b
```

This downloads ~9GB of model weights. Be patient!

### 4. Verify Your Environment

```bash
cd /path/to/this_is_fine

# Check .env file has required keys
cat .env

# Should include:
# FIRMS_API_KEY=...
# AIRNOW_API_KEY=... (optional)
# PURPLEAIR_API_KEY=... (optional)
```

### 5. Launch the Web Interface

```bash
uv run python web/gradio_app.py
```

You should see:
```
✓ qwen2.5:14b model found
Running on local URL:  http://0.0.0.0:7860
```

### 6. Open Your Browser

Navigate to: **http://localhost:7860**

## First Steps

### Example 1: Fetch and Visualize Fires

**In the chat interface:**

1. **Fetch data:**
   ```
   Fetch fires in California from the last 2 days
   ```
   
   The assistant will execute the `fetch_fires` tool and report:
   ```
   Found 150 fires in California (23 industrial sources filtered)
   ```

2. **View the map:**
   - Look at the right panel - the basic fire map should now show California fires
   - Try switching map types using the radio buttons

### Example 2: Add Air Quality Data

**Chat command:**
```
Add PurpleAir air quality data to the fires
```

The assistant will:
1. Execute `enrich_purpleair` tool
2. Search for nearby sensors (50km radius)
3. Report: "Added PM2.5 data to 87 out of 150 fires"

**View the results:**
- Switch to the "purpleair" map type
- You'll see a PM2.5 density heatmap

### Example 3: Get Statistics

**Chat command:**
```
Show me the current fire statistics
```

The assistant will:
1. Execute `get_fire_stats` tool
2. Display breakdown by risk category
3. Show enrichment status (weather, AQI, PurpleAir)

## Common Chat Commands

### Fetching Data

```
Fetch fires in Colorado
Get fires for the Pacific Northwest
Fetch California fires from the last 5 days
Get fires for the entire US
```

### Enriching Data

```
Add weather data
Enrich with AirNow air quality
Add PurpleAir sensor data
Get PM2.5 data using a 30km radius
```

### Visualization

```
Generate a risk heatmap
Create all visualizations
Show me an AQI map
Make a PM2.5 heatmap
```

### Information

```
What's the current fire situation?
Show fire statistics
How many high-risk fires are there?
What data sources are available?
```

## Map Types

Switch between visualizations using the radio buttons:

1. **basic** - Fire points colored by risk (yellow/orange/red)
2. **risk_heatmap** - Density heatmap weighted by risk score
3. **aqi** - Air Quality Index heatmap (requires AQI enrichment)
4. **purpleair** - PM2.5 smoke density (requires PurpleAir enrichment)

## Troubleshooting

### "Could not connect to Ollama"

**Fix:**
```bash
# In a terminal window, start Ollama
ollama serve
```

### "qwen2.5:14b not found"

**Fix:**
```bash
ollama pull qwen2.5:14b
```

### LLM is too slow

**Try a smaller model:**
```bash
ollama pull llama3.2:11b
```

**Edit `web/gradio_app.py`:**
```python
# Line ~206
assistant = WildfireAssistant(model="llama3.2:11b")
```

### Out of memory

**Options:**
1. Close other applications
2. Use a smaller model (7b instead of 14b)
3. Reduce the number of fires (fetch smaller regions)

### Map not showing

**Fix:**
```bash
# Make sure you've fetched data first
uv run wildfire fetch --region california

# Then refresh the map in the web interface
```

## Performance Tips

### Speed up enrichment

For faster testing, fetch smaller regions:
```
Fetch fires in Nevada  (smaller state)
```

Instead of:
```
Fetch fires for the entire US  (1000+ fires)
```

### Weather enrichment is slow

Weather data takes ~1-2 seconds per fire. For large datasets:

**Option 1:** Don't use weather in the web interface
```
# Instead of: "Add weather data"
# Just use: "Fetch fires in California"
```

**Option 2:** Use the CLI for weather (faster for batch):
```bash
uv run wildfire fetch --region california --weather
```

Then load in web interface:
```
Show me fire statistics
```

## Advanced Usage

### Chain Multiple Operations

```
Fetch fires in Oregon, then add PurpleAir data, then show me statistics
```

The LLM will execute all operations in sequence.

### Ask Questions

```
How does the risk score calculation work?
What's the difference between AirNow and PurpleAir?
Why are some fires filtered out?
```

The LLM will answer directly without calling tools.

### Generate Multiple Visualizations

```
Generate all available visualizations
```

This creates HTML files in `data/processed/` that you can open in any browser.

## Next Steps

1. **Try different regions:** Explore fires across different states
2. **Compare air quality sources:** Enrich with both AirNow and PurpleAir
3. **Export visualizations:** HTML maps are saved to `data/processed/`
4. **Customize the LLM:** Edit the system prompt in `web/gradio_app.py`

## Full Documentation

- **Web interface details:** `docs/gradio_web_interface.md`
- **MCP server tools:** `mcp_server/server.py` and `mcp_server/tools.py`
- **Plotly visualizations:** `notebooks/plotly_visualization.ipynb`
- **Overall project:** `CLAUDE.md`

## Support

If you encounter issues:

1. Check the terminal output for error messages
2. Verify Ollama is running: `ollama list`
3. Check environment variables: `cat .env`
4. Try fetching data via CLI first: `uv run wildfire fetch --region california`

Happy wildfire monitoring! 🔥🗺️
