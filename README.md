# CarGame — 3D Arcade Racing (Clean rewrite)

This branch contains a cleaned, rewritten version of the Three.js arcade demo and a Streamlit wrapper that embeds it.

Files in this branch
- index.html — minimal HTML shell that loads Three.js and the game script.
- src/main.js — cleaned, tested arcade driving code (player car, simple oval track, HUD).
- streamlit_app.py — Streamlit wrapper that inlines the JS into the HTML and renders it via components.html.
- requirements.txt — dependencies for Streamlit Cloud.

How to run locally
1. Checkout the branch:
   git fetch && git checkout threejs-arcade-streamlit
2. (Optional) create a virtualenv and activate it.
3. Install dependencies:
   pip install -r requirements.txt
4. Run Streamlit:
   streamlit run streamlit_app.py

Deploy to Streamlit Cloud
1. Push the branch to GitHub (already pushed by the assistant).
2. Visit https://share.streamlit.io, connect your GitHub account, and select this repository and branch.
3. Set the main file to streamlit_app.py if required.

Notes
- The Streamlit wrapper inlines the JS at runtime so no static file serving is required.
- If keyboard input doesn't respond inside the iframe, click the canvas to focus it. I can add a "Click to focus" helper if you want.
