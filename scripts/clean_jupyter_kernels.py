#!/usr/bin/env python3
"""
Clean stale Jupyter kernel references.

This script helps resolve "Kernel does not exist" errors by:
1. Listing currently running Jupyter kernels
2. Optionally cleaning up stale kernel sessions

Usage:
    uv run python scripts/clean_jupyter_kernels.py
"""

import json
import shutil
from pathlib import Path


def find_jupyter_runtime_dir() -> Path | None:
    """Find Jupyter's runtime directory."""
    # Common locations
    candidates = [
        Path.home() / ".local/share/jupyter/runtime",
        Path.home() / "Library/Jupyter/runtime",  # macOS
        Path.home() / ".jupyter/runtime",
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def list_kernel_sessions(runtime_dir: Path) -> list[dict]:
    """List all kernel session files."""
    kernel_files = list(runtime_dir.glob("kernel-*.json"))
    sessions = []

    for kernel_file in kernel_files:
        try:
            with open(kernel_file) as f:
                data = json.load(f)
                sessions.append(
                    {
                        "file": kernel_file,
                        "kernel_id": kernel_file.stem.replace("kernel-", ""),
                        "data": data,
                    }
                )
        except Exception as e:
            print(f"⚠️  Could not read {kernel_file.name}: {e}")

    return sessions


def clean_jupyter_runtime() -> None:
    """Clean Jupyter runtime directory of stale kernel sessions."""
    runtime_dir = find_jupyter_runtime_dir()

    if not runtime_dir:
        print("❌ Could not find Jupyter runtime directory")
        print("\nTry manually clearing:")
        print("  macOS: ~/Library/Jupyter/runtime/")
        print("  Linux: ~/.local/share/jupyter/runtime/")
        return

    print(f"📁 Jupyter runtime directory: {runtime_dir}")
    print()

    # List current sessions
    sessions = list_kernel_sessions(runtime_dir)

    if not sessions:
        print("✅ No kernel session files found")
        return

    print(f"Found {len(sessions)} kernel session(s):")
    for session in sessions:
        print(f"  - {session['kernel_id']}")

    print()

    # Ask user if they want to clean
    response = input("🗑️  Remove all kernel session files? (y/N): ").strip().lower()

    if response == "y":
        for session in sessions:
            try:
                session["file"].unlink()
                print(f"  ✓ Removed {session['file'].name}")
            except Exception as e:
                print(f"  ✗ Could not remove {session['file'].name}: {e}")

        print()
        print("✅ Cleanup complete!")
        print()
        print("Next steps:")
        print("  1. Restart Jupyter: jupyter notebook")
        print("  2. Open notebooks/kepler.ipynb")
        print("  3. Kernel → Restart & Clear Output")
    else:
        print("Cleanup cancelled")
        print()
        print("Alternative: Restart Jupyter server completely:")
        print("  1. Stop current Jupyter process (Ctrl+C)")
        print("  2. Run: jupyter notebook stop")
        print("  3. Start fresh: jupyter notebook")


def main() -> None:
    """Main entry point."""
    print("=" * 60)
    print("Jupyter Kernel Cleanup Utility")
    print("=" * 60)
    print()

    clean_jupyter_runtime()


if __name__ == "__main__":
    main()
