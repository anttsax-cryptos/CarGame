from ursina import Vec3

# Game constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

TRACK_RADIUS = 18.0          # world units
TRACK_WIDTH = 6.0            # road width
SEGMENTS = 160               # number of segments used to build the ring

START_ANGLE = 0.0           # radians (pointing along +X)

# Car tuning
CAR_LENGTH = 1.8
CAR_WIDTH = 0.9
MAX_SPEED = 14.0            # world units / second
ACCELERATION = 35.0
BRAKE_DECEL = 60.0
FRICTION = 6.0
TURN_SPEED = 3.2
