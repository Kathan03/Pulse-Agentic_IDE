"""
Pulse - Agentic AI IDE for PLC Coding
Main entry point for the application
"""
import flet as ft
import os
from dotenv import load_dotenv
from src.ui.app import main

# Load environment variables from .env file (for development)
load_dotenv()


if __name__ == "__main__":
    ft.app(target=main)
