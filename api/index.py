"""
Vercel entry point for Daur Awaz
Imports the Flask app from app.py
"""

from app import app

# Vercel needs 'app' variable exported
# This file is the entry point

if __name__ == "__main__":
    app.run()