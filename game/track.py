from ursina import Entity, color, Vec3, Mesh, MeshRenderer, Quads, quad, Vec2
import math
from .constants import TRACK_RADIUS, TRACK_WIDTH, SEGMENTS

class Track(Entity):
    def __init__(self, **kwargs):
        super().__init__(name='track')
        self.center = Vec3(0, 0, 0)
        self.radius = TRACK_RADIUS
        self.width = TRACK_WIDTH
        self.segments = SEGMENTS
        self.start_angle = 0.0
        self._build_road()

    def _build_road(self):
        # Build the road as many thin quads (segments) placed along the circle.
        seg_len = (2 * math.pi * self.radius) / self.segments
        road_color = color.rgb(40, 40, 40)
        mark_color = color.rgb(230,230,230)
        for i in range(self.segments):
            ang = (i / self.segments) * (2 * math.pi)
            # position at ring centerline
            cx = math.cos(ang) * self.radius
            cz = math.sin(ang) * self.radius
            # create a green grass base slightly below road
            # create road segment
            seg = Entity(model='cube', scale=(seg_len*1.02, 0.05, self.width),
                         position=(cx, 0.02, cz), rotation=(0, -math.degrees(ang), 0),
                         color=road_color, double_sided=True, parent=self)
        # draw centerline (thin ring of quads with bright color every few segments)
        for i in range(0, self.segments, 8):
            ang = (i / self.segments) * (2 * math.pi)
            cx = math.cos(ang) * self.radius
            cz = math.sin(ang) * self.radius
            seg = Entity(model='cube', scale=(seg_len*0.9, 0.02, 0.25),
                         position=(cx, 0.03, cz), rotation=(0, -math.degrees(ang), 0),
                         color=mark_color, parent=self)

    def is_on_track(self, pos):
        # pos: Vec3
        v = pos - self.center
        r = math.sqrt(v.x * v.x + v.z * v.z)
        inner = self.radius - (self.width/2 + 0.5)
        outer = self.radius + (self.width/2 + 0.5)
        return inner <= r <= outer

    def angle_of(self, pos):
        v = pos - self.center
        return math.atan2(v.z, v.x)
