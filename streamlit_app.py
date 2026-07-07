import streamlit as st
import subprocess
import sys
import os
import signal
import platform

st.set_page_config(page_title="PyRacer — Ursina Launcher", layout="centered")
st.title("PyRacer — Ursina Launcher")

st.markdown(
    """
    This Streamlit page can start and stop the native Ursina window for the PyRacer demo.

    Important: The Ursina window will open on the machine that runs Streamlit (the server), not inside your browser.
    Use this when you run Streamlit locally and want a convenient button to launch the game.
    """
)

if 'proc_pid' not in st.session_state:
    st.session_state.proc_pid = None

col1, col2 = st.columns(2)

with col1:
    if st.button("Start PyRacer (Ursina)"):
        if st.session_state.proc_pid:
            st.warning(f"PyRacer already running (pid={st.session_state.proc_pid}).")
        else:
            # Start the main.py as a separate process so Streamlit doesn't block.
            python = sys.executable or 'python'
            try:
                if platform.system() == 'Windows':
                    # CREATE_NEW_PROCESS_GROUP to allow separate console on Windows
                    proc = subprocess.Popen([python, "main.py"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                else:
                    # start_new_session to detach from controlling terminal on Unix
                    proc = subprocess.Popen([python, "main.py"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                                             start_new_session=True)
                st.session_state.proc_pid = proc.pid
                st.success(f"Started PyRacer (pid={proc.pid}). Check the host machine for the game window.")
            except FileNotFoundError:
                st.error("main.py not found in the repository root. Make sure you're running Streamlit from the project directory.")
            except Exception as e:
                st.error(f"Failed to start PyRacer: {e}")

with col2:
    if st.button("Stop PyRacer"):
        pid = st.session_state.get('proc_pid')
        if not pid:
            st.info("PyRacer is not running (no PID stored).")
        else:
            try:
                if platform.system() == 'Windows':
                    subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False)
                else:
                    os.kill(pid, signal.SIGTERM)
                st.success(f"Stop signal sent to pid={pid}.")
            except ProcessLookupError:
                st.warning(f"No process with pid={pid} was found.")
            except Exception as e:
                st.error(f"Failed to stop process {pid}: {e}")
            finally:
                st.session_state.proc_pid = None

st.markdown("---")
st.markdown("**Notes**")
st.markdown("- The game window will appear on the machine where Streamlit runs (not inside the browser).")
st.markdown("- If you run Streamlit on a remote server, you typically won't see the Ursina window unless you are logged into the server's desktop session.")
st.markdown("- To run locally, open a terminal in the repository and run:\n\n```
streamlit run streamlit_app.py
```")
