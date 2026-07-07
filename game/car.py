from ursina import Entity, color, Vec3, camera, held_keys
import math
from .constants import CAR_LENGTH, CAR_WIDTH, MAX_SPEED, ACCELERATION, BRAKE_DECEL, FRICTION, TURN_SPEED

class Car(Entity):
    def __init__(self, x=0, z=0, color_value=color.azure, **kwargs):
        super().__init__(model='cube', scale=(CAR_LENGTH, 0.5, CAR_WIDTH), color=color_value, position=(x, 0.25, z))
        self.speed = 0.0
        self.heading = 0.0  # radians, 0 along +X
        self.steer = 0.0
        self.accel = 0.0
        self.previous_pos = self.position

    def update(self, dt):
        # input handling for player car uses held_keys externally; AI will set self.steer/self.accel
        # integrate acceleration
        if self.accel > 0:
            self.speed += self.accel * ACCELERATION * dt
        elif self.accel < 0:
            # braking / reverse
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

        # clamp
        if self.speed > MAX_SPEED:
            self.speed = MAX_SPEED
        if self.speed < -4.0:
            self.speed = -4.0

        # apply steering
        speed_factor = min(abs(self.speed) / max(0.1, MAX_SPEED), 1.0)
        heading_change = self.steer * TURN_SPEED * (0.4 + speed_factor * 1.0) * dt
        if self.speed < 0:
            heading_change *= -1
        self.heading += heading_change
        self.rotation_y = -math.degrees(self.heading)

        # move forward
        dx = math.cos(self.heading) * self.speed * dt
        dz = math.sin(self.heading) * self.speed * dt
        self.previous_pos = self.position
        self.x += dx
        self.z += dz

    def set_player_input(self, keys):
        accel = 0.0
        steer = 0.0
        if keys.get('w') or keys.get('up'):
            accel = 1.0
        if keys.get('s') or keys.get('down'):
            accel = -1.0
        if keys.get('a') or keys.get('left'):
            steer = -1.0
        if keys.get('d') or keys.get('right'):
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
