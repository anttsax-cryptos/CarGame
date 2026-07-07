# PyRacer — 3D Arcade Car Racing (Ursina)

A simple 3D arcade-style car racing demo written entirely in Python using the Ursina engine.

This repository contains a minimal but complete 3D driving experience: a procedurally generated circular track, a player car with arcade-style controls, chase camera, HUD, and lap counting. No external assets are required.

Requirements
- Python 3.8+
- OpenGL-compatible GPU / drivers
- Ursina (listed in requirements.txt)

Quick start
1. Create and activate a virtual environment (optional):
   python -m venv .venv
   # macOS / Linux
   source .venv/bin/activate
   # Windows
   .venv\Scripts\activate

2. Install dependencies:
   pip install -r requirements.txt

3. Run the game:
   python main.py

Controls
- W / Up: accelerate
- S / Down: brake / reverse
- A / Left: steer left
- D / Right: steer right
- R: reset to start
- Esc or window close: quit

Notes
- This is a native OpenGL application (Ursina). It is not embeddable inside Streamlit as an interactive 3D canvas.

License
MIT
