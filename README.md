# CarGame — 3D Arcade Racing

This repository contains a simple arcade-style 3D car racing demo built with Three.js and embedded in a Streamlit app for easy sharing.

What’s included

- index.html — Three.js scene that renders the game.
- src/main.js — Arcade driving logic and scene setup.
- streamlit_app.py — Streamlit wrapper that inlines the game and serves it in an iframe.

How to run locally

1. Install dependencies:

   pip install -r requirements.txt

2. Run the Streamlit app:

   streamlit run streamlit_app.py

How to deploy to Streamlit Cloud

1. Push this repository to GitHub (branch is ready: threejs-arcade-streamlit).
2. Go to https://share.streamlit.io and connect your GitHub account.
3. Select this repository and the branch threejs-arcade-streamlit.
4. Set the main file to streamlit_app.py (the UI usually detects it automatically).

Notes

- Controls: WASD or arrow keys to drive, R to reset.
- The game uses Three.js from a CDN and inlines src/main.js into index.html at runtime via streamlit_app.py, so no extra static file routing is required.
- For mobile, the Streamlit iframe height may need adjusting; contact me if you want touch controls added.
