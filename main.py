"""
Pulse - Agentic AI IDE for PLC Coding
Main entry point for the application
"""
import flet as ft
from src.ui.app import main


if __name__ == "__main__":
    ft.app(target=main)
