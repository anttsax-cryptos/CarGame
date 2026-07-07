from ursina import Ursina, camera, color, Text, Entity, sky, vec3
from .track import Track
from .car import Car
from .constants import TRACK_RADIUS
import math, time

class Game:
    def __init__(self):
        self.app = Ursina()
        self.app.title = "PyRacer (Ursina)"
        self.app.vsync = True

        # environment
        self.ground = Entity(model='plane', scale=100, color=color.rgb(30,120,30), y=0)
        self.track = Track()

        # player car start position on inner side of track
        start_angle = 0.0
        start_r = self.track.radius - (self.track.width/2 - 0.5)
        sx = math.cos(start_angle) * start_r
        sz = math.sin(start_angle) * start_r
        self.player = Car(sx, sz, color_value=color.rgb(200,30,30))
        self.player.reset(sx, sz, start_angle + math.pi/2)

        # HUD
        self.speed_text = Text(text='Speed: 0', position=(-0.85, 0.42), scale=1.2, background=True)
        self.lap_text = Text(text='Laps: 0', position=(-0.85, 0.35), scale=1.0, background=True)

        # camera settings
        camera.fov = 70
        camera.y = 6
        camera.z = -12

        # lap detection
        self.last_sign = 0
        self.laps = 0
        self.start_time = time.time()
        self.current_lap_start = time.time()
        self.best_lap = None

        # sky
        sky.color = color.rgb(130,200,255)

        # bind update
        self.app.update = self.update

    def update(self):
        dt = self.app.dt
        # read input via ursina.held_keys convenience dict
        # keys use single-letter strings like 'w', 'a' or arrow names 'up'
        keys = {
            'w': held_keys['w'], 'a': held_keys['a'], 's': held_keys['s'], 'd': held_keys['d'],
            'up': held_keys['up arrow'] if 'up arrow' in held_keys else held_keys['up'],
            'down': held_keys['down arrow'] if 'down arrow' in held_keys else held_keys['down'],
            'left': held_keys['left arrow'] if 'left arrow' in held_keys else held_keys['left'],
            'right': held_keys['right arrow'] if 'right arrow' in held_keys else held_keys['right']
        }
        self.player.set_player_input(keys)
        self.player.update(dt)

        # enforce track bounds
        v = vec3(self.player.x, 0, self.player.z)
        r = math.sqrt(v.x*v.x + v.z*v.z)
        outer = self.track.radius + (self.track.width/2) + 2
        inner = max(0, self.track.radius - (self.track.width/2) - 2)
        if r > outer or r < inner:
            # push back toward center and slow
            dir_to_center_x = -v.x
            dir_to_center_z = -v.z
            length = math.sqrt(dir_to_center_x*dir_to_center_x + dir_to_center_z*dir_to_center_z)
            if length > 0:
                dir_to_center_x /= length
                dir_to_center_z /= length
                self.player.x += dir_to_center_x * 5 * dt * 60
                self.player.z += dir_to_center_z * 5 * dt * 60
            self.player.speed *= 0.7

        # lap detection
        self._check_lap()

        # update camera: chase behind the car
        desired = vec3(self.player.x, 3.5, self.player.z) + vec3(-math.cos(self.player.heading)*6, 2.0, -math.sin(self.player.heading)*6)
        camera.position = camera.position + (desired - camera.position) * min(1, 6 * dt)
        camera.look_at((self.player.x, 1.0, self.player.z))

        # HUD
        sp = int(max(0, self.player.speed) * 10)
        self.speed_text.text = f"Speed: {sp}"
        self.lap_text.text = f"Laps: {self.laps}"

        # reset / quit keys
        if held_keys['r']:
            self.reset_player()
        if held_keys['escape']:
            self.app.user_exit()

    def _check_lap(self):
        pos = self.player.position
        ang = math.atan2(pos.z, pos.x)
        n_ang = (ang + 2*math.pi) % (2*math.pi)
        s_ang = (self.track.start_angle + 2*math.pi) % (2*math.pi)
        diff = n_ang - s_ang
        sign = 1 if diff > 0 else -1
        r = math.sqrt(pos.x*pos.x + pos.z*pos.z)
        near = abs(r - self.track.radius) < (self.track.width/2 + 1.5)
        if self.last_sign == -1 and sign == 1 and near:
            self.laps += 1
            lap_time = time.time() - self.current_lap_start
            if self.best_lap is None or lap_time < self.best_lap:
                self.best_lap = lap_time
            self.current_lap_start = time.time()
        self.last_sign = sign

    def reset_player(self):
        start_angle = 0.0
        start_r = self.track.radius - (self.track.width/2 - 0.5)
        sx = math.cos(start_angle) * start_r
        sz = math.sin(start_angle) * start_r
        self.player.reset(sx, sz, start_angle + math.pi/2)
        self.laps = 0
        self.last_sign = 0
        self.start_time = time.time()
        self.current_lap_start = time.time()

    def run(self):
        self.app.run()
