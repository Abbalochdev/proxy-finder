#!/usr/bin/env python
"""
Proxy Finder - Command-line tool for finding and validating proxies
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import the main CLI function
from proxy_finder.cli import main

if __name__ == "__main__":
    main()
