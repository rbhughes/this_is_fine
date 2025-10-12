# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project named "this-is-fine" managed with uv (modern Python package manager). It's a minimal project with a single entry point in `main.py`.

## Development Commands

### Running the Application
```bash
uv run main.py
```

### Python Environment
- Python version: 3.12+ (specified in `.python-version` and `pyproject.toml`)
- Virtual environment is managed automatically by uv in `.venv/`

### Dependency Management
```bash
# Add a new dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>

# Sync dependencies
uv sync
```

## Project Structure

The project currently has a minimal structure:
- `main.py` - Entry point with a `main()` function
- `pyproject.toml` - Project configuration managed by uv
- `.python-version` - Python version pinning
