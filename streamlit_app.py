"""
Single-file Streamlit + Ursina launcher.

This file contains:
- A complete self-contained Ursina 3D car racing game embedded as a string.
- Streamlit UI to Install ursina (optional), Start/Stop the game, view the log, and download the game source.
- When starting, the game is written to a temporary file and launched as a detached subprocess; logs are written to a temp logfile.

Notes:
- The Ursina window opens on the machine running Streamlit (not inside the browser).
- This repo can contain only this one file; no other Python files are required.
"""
import streamlit as st
import subprocess
import sys
import os
import signal
import platform
import tempfile
import time
from pathlib import Path
from textwrap import dedent

# ---------- Embedded game code ----------
GAME_CODE = dedent(r'''
    """
    PyRacer — embedded single-file Ursina 3D arcade car demo

    Run: pip install ursina
         python single_file_game.py
    (This file is normally generated and executed by the Streamlit launcher.)
    """
    import math, time
    from ursina import Ursina, Entity, color, Text, camera, sky, Vec3, held_keys

    # Tunables
    TRACK_RADIUS = 18.0
    TRACK_WIDTH = 6.0
    SEGMENTS = 160

    CAR_LENGTH = 1.8
    CAR_WIDTH = 0.9
    MAX_SPEED = 14.0
    ACCELERATION = 35.0
    BRAKE_DECEL = 60.0
    FRICTION = 6.0
    TURN_SPEED = 3.2

    class Track(Entity):
        def __init__(self, radius=TRACK_RADIUS, width=TRACK_WIDTH, segments=SEGMENTS):
            super().__init__(name='track')
            self.radius = radius
            self.width = width
            self.segments = segments
            self.start_angle = 0.0
            self._build_road()

        def _build_road(self):
            seg_len = (2 * math.pi * self.radius) / self.segments
            road_color = color.rgb(40, 40, 40)
            mark_color = color.rgb(230, 230, 230)

            for i in range(self.segments):
                ang = (i / self.segments) * (2 * math.pi)
                cx = math.cos(ang) * self.radius
                cz = math.sin(ang) * self.radius
                Entity(
                    model='cube',
                    scale=(seg_len * 1.02, 0.05, self.width),
                    position=(cx, 0.02, cz),
                    rotation=(0, -math.degrees(ang), 0),
                    color=road_color,
                    double_sided=True,
                    parent=self
                )

            # dashed centerline
            for i in range(0, self.segments, 8):
                ang = (i / self.segments) * (2 * math.pi)
                cx = math.cos(ang) * self.radius
                cz = math.sin(ang) * self.radius
                Entity(
                    model='cube',
                    scale=(seg_len * 0.9, 0.02, 0.25),
                    position=(cx, 0.03, cz),
                    rotation=(0, -math.degrees(ang), 0),
                    color=mark_color,
                    parent=self
                )

            # finish line indicator
            ang = self.start_angle
            inner = self.radius - (self.width / 2)
            mx = math.cos(ang) * (inner + (self.width))
            mz = math.sin(ang) * (inner + (self.width))
            Entity(
                model='cube',
                scale=(0.2, 0.06, self.width + 1.2),
                position=(mx, 0.04, mz),
                rotation=(0, -math.degrees(ang), 0),
                color=color.white,
                parent=self
            )

        def is_on_track(self, pos: Vec3) -> bool:
            r = math.sqrt(pos.x * pos.x + pos.z * pos.z)
            inner = self.radius - (self.width / 2 + 0.5)
            outer = self.radius + (self.width / 2 + 0.5)
            return inner <= r <= outer

    class Car(Entity):
        def __init__(self, x=0, z=0, clr=color.azure):
            super().__init__(model='cube', scale=(CAR_LENGTH, 0.5, CAR_WIDTH), color=clr, position=(x, 0.25, z))
            self.speed = 0.0
            self.heading = 0.0  # radians, 0 along +X
            self.steer = 0.0
            self.accel = 0.0
            self.previous_pos = self.position

        def apply_physics(self, dt):
            # integrate acceleration & braking
            if self.accel > 0:
                self.speed += self.accel * ACCELERATION * dt
            elif self.accel < 0:
                if self.speed > 0:
                    self.speed += self.accel * BRAKE_DECEL * dt
                else:
                    self.speed += self.accel * (ACCELERATION * 0.6) * dt
            else:
                # friction
                if self.speed > 0:
                    self.speed -= FRICTION * dt
                    if self.speed < 0:
                        self.speed = 0
                elif self.speed < 0:
                    self.speed += FRICTION * dt
                    if self.speed > 0:
                        self.speed = 0

            # clamp speeds
            if self.speed > MAX_SPEED:
                self.speed = MAX_SPEED
            if self.speed < -4.0:
                self.speed = -4.0

            # steering
            speed_factor = min(abs(self.speed) / max(0.1, MAX_SPEED), 1.0)
            heading_change = self.steer * TURN_SPEED * (0.4 + speed_factor * 1.0) * dt
            if self.speed < 0:
                heading_change *= -1
            self.heading += heading_change
            self.rotation_y = -math.degrees(self.heading)

            # move
            dx = math.cos(self.heading) * self.speed * dt
            dz = math.sin(self.heading) * self.speed * dt
            self.previous_pos = self.position
            self.x += dx
            self.z += dz

        def set_player_input(self):
            accel = 0.0
            steer = 0.0
            if held_keys.get('w') or held_keys.get('up'):
                accel = 1.0
            if held_keys.get('s') or held_keys.get('down'):
                accel = -1.0
            if held_keys.get('a') or held_keys.get('left'):
                steer = -1.0
            if held_keys.get('d') or held_keys.get('right'):
                steer = 1.0
            self.accel = accel
            self.steer = steer

        def reset(self, x, z, heading=0.0):
            self.position = Vec3(x, 0.25, z)
            self.heading = heading
            self.rotation_y = -math.degrees(self.heading)
            self.speed = 0.0
            self.steer = 0.0
            self.accel = 0.0

    class Game:
        def __init__(self):
            self.app = Ursina()
            self.app.title = "PyRacer (single-file)"
            self.app.vsync = True

            # ground and environment
            Entity(model='plane', scale=200, color=color.rgb(28, 110, 30), y=0)
            self.track = Track()

            # player start
            start_angle = 0.0
            start_r = self.track.radius - (self.track.width / 2 - 0.5)
            sx = math.cos(start_angle) * start_r
            sz = math.sin(start_angle) * start_r
            self.player = Car(sx, sz, clr=color.rgb(200, 30, 30))
            self.player.reset(sx, sz, start_angle + math.pi / 2)

            # HUD
            self.speed_text = Text(text='Speed: 0', position=(-0.85, 0.42), scale=1.2, background=True)
            self.lap_text = Text(text='Laps: 0', position=(-0.85, 0.35), scale=1.0, background=True)

            # camera setup
            camera.fov = 70
            camera.y = 6
            camera.z = -12

            sky.color = color.rgb(140, 200, 255)

            # lap detection
            self.last_sign = 0
            self.laps = 0
            self.start_time = time.time()
            self.current_lap_start = time.time()
            self.best_lap = None

            self.app.update = self.update  # set update function

        def _check_lap(self):
            pos = self.player.position
            ang = math.atan2(pos.z, pos.x)
            n_ang = (ang + 2 * math.pi) % (2 * math.pi)
            s_ang = (self.track.start_angle + 2 * math.pi) % (2 * math.pi)
            diff = n_ang - s_ang
            sign = 1 if diff > 0 else -1
            r = math.sqrt(pos.x * pos.x + pos.z * pos.z)
            near = abs(r - self.track.radius) < (self.track.width / 2 + 1.5)
            if self.last_sign == -1 and sign == 1 and near:
                self.laps += 1
                lap_time = time.time() - self.current_lap_start
                if self.best_lap is None or lap_time < self.best_lap:
                    self.best_lap = lap_time
                self.current_lap_start = time.time()
            self.last_sign = sign

        def reset_player(self):
            start_angle = 0.0
            start_r = self.track.radius - (self.track.width / 2 - 0.5)
            sx = math.cos(start_angle) * start_r
            sz = math.sin(start_angle) * start_r
            self.player.reset(sx, sz, start_angle + math.pi / 2)
            self.laps = 0
            self.last_sign = 0
            self.start_time = time.time()
            self.current_lap_start = time.time()

        def update(self):
            dt = self.app.dt

            # input
            self.player.set_player_input()
            # physics
            self.player.apply_physics(dt)

            # enforce bounds
            v_x, v_z = self.player.x, self.player.z
            r = math.sqrt(v_x * v_x + v_z * v_z)
            outer = self.track.radius + (self.track.width / 2) + 2
            inner = max(0, self.track.radius - (self.track.width / 2) - 2)
            if r > outer or r < inner:
                dir_to_center_x = -v_x
                dir_to_center_z = -v_z
                length = math.sqrt(dir_to_center_x * dir_to_center_x + dir_to_center_z * dir_to_center_z)
                if length > 0:
                    dir_to_center_x /= length
                    dir_to_center_z /= length
                    self.player.x += dir_to_center_x * 5 * dt * 60
                    self.player.z += dir_to_center_z * 5 * dt * 60
                self.player.speed *= 0.7

            # lap detection
            self._check_lap()

            # camera chase
            desired = Vec3(self.player.x, 3.5, self.player.z) + Vec3(-math.cos(self.player.heading) * 6, 2.0,
                                                                        -math.sin(self.player.heading) * 6)
            camera.position = camera.position + (desired - camera.position) * min(1, 6 * dt)
            camera.look_at((self.player.x, 1.0, self.player.z))

            # HUD
            sp = int(max(0, self.player.speed) * 10)
            self.speed_text.text = f"Speed: {sp}"
            self.lap_text.text = f"Laps: {self.laps}"

            # reset / quit
            if held_keys.get('r'):
                self.reset_player()
            if held_keys.get('escape'):
                self.app.user_exit()

        def run(self):
            self.app.run()

    def main():
        g = Game()
        g.run()

    if __name__ == "__main__":
        main()
''')

# ---------- Streamlit UI & launcher logic ----------
st.set_page_config(page_title="PyRacer — Single-file Launcher", layout="centered")
st.title("PyRacer — Single-file Ursina Launcher (single-file repo)")

st.markdown(
    "This page will run a self-contained Ursina 3D game from memory by writing a temporary script and launching it as a detached process. "
    "No permanent extra Python files are created in the repository."
)


def is_ursina_installed() -> bool:
    try:
        import ursina  # noqa: F401
        return True
    except Exception:
        return False


def install_ursina() -> bool:
    st.info("Installing ursina (may take a minute)...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ursina"])
        st.success("ursina installed.")
        return True
    except subprocess.CalledProcessError as e:
        st.error(f"Failed to install ursina: {e}")
        return False


def write_temp_game_file() -> Path:
    # create a temp file that we leave until the process ends (so Ursina can import it)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".py", prefix="pyracer_", mode="w", encoding="utf-8")
    tmp.write(GAME_CODE)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def start_game(temp_py_path: Path, log_path: Path) -> int:
    python = sys.executable or "python"
    logf = open(log_path, "a", encoding="utf-8")
    try:
        if platform.system() == "Windows":
            proc = subprocess.Popen([python, str(temp_py_path)], stdout=logf, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            proc = subprocess.Popen([python, str(temp_py_path)], stdout=logf, stderr=subprocess.STDOUT,
                                     start_new_session=True)
        time.sleep(0.2)
        return proc.pid
    except Exception as e:
        st.error(f"Failed to start process: {e}")
        return None
    finally:
        logf.close()


def stop_process(pid: int) -> bool:
    if not pid:
        return False
    try:
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=False)
        else:
            os.kill(pid, signal.SIGTERM)
        time.sleep(0.2)
        return True
    except ProcessLookupError:
        return False
    except Exception:
        return False

# session state keys: pid, tmp_game_path, log_path
if "pid" not in st.session_state:
    st.session_state.pid = None
if "tmp_game_path" not in st.session_state:
    st.session_state.tmp_game_path = None
if "log_path" not in st.session_state:
    st.session_state.log_path = None

col1, col2, col3 = st.columns([1,1,1])

with col1:
    if st.button("Install ursina"):
        if is_ursina_installed():
            st.info("ursina already installed.")
        else:
            install_ursina()

with col2:
    if st.button("Start game (temp)"):
        if st.session_state.pid:
            st.warning(f"Game appears to be running (pid={st.session_state.pid}). Stop it first.")
        else:
            if not is_ursina_installed():
                st.warning("ursina not installed. Click 'Install ursina' first (or install manually).")
            else:
                tmp_py = write_temp_game_file()
                tmp_log = Path(tempfile.gettempdir()) / f"pyracer_log_{int(time.time())}.log"
                pid = start_game(tmp_py, tmp_log)
                if pid:
                    st.session_state.pid = pid
                    st.session_state.tmp_game_path = str(tmp_py)
                    st.session_state.log_path = str(tmp_log)
                    st.success(f"Started game (pid={pid}). Temporary script: {tmp_py}")
                else:
                    # cleanup if failed
                    try:
                        tmp_py.unlink()
                    except Exception:
                        pass

with col3:
    if st.button("Stop game"):
        pid = st.session_state.get("pid")
        if not pid:
            st.info("No running game PID stored.")
        else:
            ok = stop_process(pid)
            if ok:
                st.success(f"Stop signal sent to pid={pid}.")
            else:
                st.warning(f"Could not stop pid={pid} (it may have already exited).")
            # attempt cleanup of temp game file
            tmp_path = st.session_state.get("tmp_game_path")
            try:
                if tmp_path:
                    Path(tmp_path).unlink(missing_ok=True)
            except Exception:
                pass
            st.session_state.pid = None
            st.session_state.tmp_game_path = None

st.markdown("---")

# Show status and controls for log / download
st.subheader("Status")
if st.session_state.pid:
    st.info(f"Game running (pid={st.session_state.pid}). Temp script: {st.session_state.tmp_game_path}")
else:
    st.info("Game not running.")

if st.session_state.tmp_game_path:
    tmp_p = Path(st.session_state.tmp_game_path)
    try:
        code_text = tmp_p.read_text(encoding="utf-8")
    except Exception:
        code_text = GAME_CODE
    st.download_button("Download the generated game script", code_text, file_name="single_file_game.py")

st.subheader("Log (tail)")
log_path = st.session_state.get("log_path")
if log_path and Path(log_path).exists():
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as lf:
            lines = lf.readlines()[-400:]
            st.code("".join(lines))
    except Exception as e:
        st.error(f"Failed to read log: {e}")
else:
    st.info("No log yet. Start the game to create a log file.")

st.markdown("---")
st.write("Notes:")
st.write("- The game window appears on the machine running Streamlit (not in your browser).")
st.write("- If you run Streamlit on a headless remote server you will not see the window unless you use a desktop session / X forwarding / RDP.")
st.write("- Temporary script files are created in the system temp directory and removed after stopping the game (or when the OS cleans temp files).")
