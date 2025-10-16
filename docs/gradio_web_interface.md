# Gradio Web Interface

## Overview

The Gradio web interface provides a natural language chat interface to the wildfire monitoring system, powered by a local LLM (Qwen2.5:14b) running via Ollama.

**Features:**
- 💬 Natural language chat interface for querying fire data
- 🗺️ Real-time interactive map visualization with Plotly
- 🤖 Local LLM (no API keys, runs on your machine)
- 🔧 Full access to all MCP tools via conversation

## Architecture

```
User (Browser)
    ↓
Gradio Web UI
    ↓
Qwen2.5:14b (via Ollama)
    ↓
MCP Server Tools
    ↓
Wildfire ETL Pipeline + Database
```

## Setup

### 1. Install Ollama

Download and install Ollama from https://ollama.ai

**macOS:**
```bash
brew install ollama
ollama serve  # Start the Ollama service
```

### 2. Pull Qwen2.5:14b Model

```bash
ollama pull qwen2.5:14b
```

**Model specs:**
- Size: ~9GB download
- RAM requirement: ~10-12GB during inference
- Perfect for 24GB MacBook Air

**Alternative models:**
- `llama3.2:11b` - Lighter weight (7GB RAM)
- `qwen2.5:7b` - Even lighter (5GB RAM)
- `mistral:7b` - Fast and efficient (5GB RAM)

### 3. Launch the Web Interface

```bash
uv run python web/gradio_app.py
```

The interface will be available at http://localhost:7860

## Usage

### Chat Commands

The LLM understands natural language commands like:

**Fetch fire data:**
- "Fetch fires in California"
- "Get fire data for Colorado from the last 3 days"
- "Fetch fires for the entire US without filtering industrial sources"

**Enrich with data sources:**
- "Add weather data to the fires"
- "Enrich with AirNow air quality data"
- "Add PurpleAir sensor data"
- "Get PM2.5 data for the fires using a 50km radius"

**Generate visualizations:**
- "Create a risk heatmap"
- "Show me an AQI visualization"
- "Generate all available maps"

**Get information:**
- "What's the current fire situation?"
- "Show me fire statistics"
- "How many high-risk fires do we have?"

### Map Types

Switch between different map visualizations:

1. **Basic** - Fire points colored by risk category
2. **Risk Heatmap** - Density heatmap weighted by risk score
3. **AQI** - Air Quality Index heatmap (requires AQI enrichment)
4. **PurpleAir** - PM2.5 density heatmap (requires PurpleAir enrichment)

### Example Workflow

1. **Fetch data:**
   ```
   User: "Fetch fires in California from the last 2 days"
   Assistant: "I'll fetch the fire data for California..."
   [Executes fetch_fires tool]
   Assistant: "Found 150 fires in California (23 industrial sources filtered)"
   ```

2. **Enrich with air quality:**
   ```
   User: "Add PurpleAir data"
   Assistant: "I'll enrich the fires with PurpleAir sensor data..."
   [Executes enrich_purpleair tool]
   Assistant: "Added PM2.5 data to 87 out of 150 fires"
   ```

3. **Visualize:**
   ```
   User: "Show me a PM2.5 heatmap"
   [Switch map type to "purpleair"]
   ```

## How It Works

### LLM Tool Integration

The assistant uses **function calling** to execute MCP tools:

1. User sends a natural language request
2. LLM determines which tool to use
3. LLM generates tool call in JSON format:
   ```json
   {
     "tool": "fetch_fires",
     "arguments": {
       "region": "california",
       "days_back": 2
     }
   }
   ```
4. Gradio app executes the tool asynchronously
5. LLM explains the results in natural language

### Available Tools

All MCP tools are accessible via chat:

- `fetch_fires` - Fetch fire data from NASA FIRMS
- `enrich_weather` - Add NOAA weather data
- `enrich_aqi` - Add EPA AirNow AQI data
- `enrich_purpleair` - Add PurpleAir PM2.5 data
- `visualize_fires` - Generate map visualizations
- `get_fire_stats` - Get summary statistics

### Real-time Map Updates

Maps are generated using Plotly and can be:
- Refreshed on demand with the 🔄 button
- Switched between types using the radio selector
- Automatically updated after tool execution

## Performance Considerations

### LLM Inference Speed

On M1/M2/M3 MacBook Air with 24GB RAM:
- **Qwen2.5:14b**: ~5-10 tokens/sec (good quality)
- **Llama3.2:11b**: ~8-15 tokens/sec (faster)
- **Qwen2.5:7b**: ~15-25 tokens/sec (fastest)

### Memory Usage

- Ollama + Qwen2.5:14b: ~10-12GB
- Gradio app: ~1-2GB
- Browser: ~1GB
- **Total**: ~13-15GB (comfortable on 24GB RAM)

### Data Processing

- FIRMS API: <1 sec per request
- Weather enrichment: ~1-2 sec per fire (slow)
- AQI enrichment: ~0.5 sec per fire
- PurpleAir enrichment: ~0.3 sec per fire
- Visualization: <1 sec for most maps

## Troubleshooting

### "Could not connect to Ollama"

Make sure Ollama is running:
```bash
ollama serve
```

### "Model not found"

Pull the model:
```bash
ollama pull qwen2.5:14b
```

### Slow LLM responses

Try a smaller model:
```bash
ollama pull llama3.2:11b
```

Update `web/gradio_app.py`:
```python
assistant = WildfireAssistant(model="llama3.2:11b")
```

### Map not updating

Click the 🔄 Refresh button or switch map types to force a reload.

### Out of memory

Close other applications or use a smaller model (7b instead of 14b).

## Advanced Usage

### Custom System Prompt

Edit the `get_system_prompt()` method in `web/gradio_app.py` to customize the assistant's behavior.

### Adding New Tools

1. Add tool function to `mcp_server/tools.py`
2. Register in `mcp_server/server.py`
3. Add to `self.tools` dict in `WildfireAssistant`

### Sharing the Interface

Enable public sharing (temporary URL):
```python
app.launch(share=True)
```

### Running on a Server

Deploy on a server with GPU:
```bash
uv run python web/gradio_app.py --server-name 0.0.0.0 --server-port 7860
```

Access from other devices on your network at `http://<your-ip>:7860`

## Why Gradio over Streamlit?

**Gradio advantages for this use case:**

1. **Better LLM integration** - Built-in chatbot component optimized for LLM interfaces
2. **Real-time updates** - Better async/await support for long-running operations
3. **Easier component composition** - More intuitive for mixing chat + visualizations
4. **Sharing built-in** - Can create public links with `share=True`
5. **HuggingFace ecosystem** - Easy deployment to HF Spaces if needed

**Streamlit is better for:**
- Multi-page dashboard apps
- More traditional data science reporting
- Apps with lots of widgets/forms
