# Path: searcher/search.py
"""
Map Pro Searcher - Main Entry Point

Run this file to launch the interactive search CLI:
    python search.py
"""

import sys
from pathlib import Path

# Add parent directory to path so searcher package can be imported
searcher_dir = Path(__file__).parent
parent_dir = searcher_dir.parent
sys.path.insert(0, str(parent_dir))

import asyncio
from searcher.cli.search_cli import main

if __name__ == '__main__':
    print("Initializing Map Pro Searcher...")
    asyncio.run(main())