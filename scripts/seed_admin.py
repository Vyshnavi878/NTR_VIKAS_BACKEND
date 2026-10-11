"""
Wrapper script for initial admin seeding.
Allows invoking: python -m scripts.seed_admin
"""
import sys
import os

# Ensure project root is in sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.scripts.seed_admin import main

if __name__ == "__main__":
    sys.exit(main())
