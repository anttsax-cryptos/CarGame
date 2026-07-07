import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(page_title="CarGame — 3D Arcade Racing", layout="wide")
st.title("CarGame — 3D Arcade Racing (Streamlit)")
st.markdown("Use WASD or arrow keys to drive. Press R to reset.")

# Inline index.html and main.js so the component is self-contained
base = Path(__file__).parent
html_path = base / "index.html"
js_path = base / "src" / "main.js"

if not html_path.exists() or not js_path.exists():
    st.error("Required files (index.html or src/main.js) are missing from the repository.")
else:
    html = html_path.read_text(encoding='utf-8')
    main_js = js_path.read_text(encoding='utf-8')

    # Replace the script tag with inline JS
    html = html.replace('<script src="src/main.js"></script>', f"<script>{main_js}</script>")

    # Render the combined HTML as a component
    components.html(html, height=720, scrolling=False)
