#!/usr/bin/env python3
"""
Bootstrap CLI entry point.

Usage:
    python run-bootstrap.py run --worker gmail_bill_intelligence --dry-run
    python run-bootstrap.py list
    python run-bootstrap.py info --worker gmail_bill_intelligence
"""

from runtime.cli import main

if __name__ == "__main__":
    exit(main())
