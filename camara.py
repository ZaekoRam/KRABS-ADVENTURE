# camara.py
import pygame

class Camara:
    def __init__(self, viewport_size, world_size):
        self.vw, self.vh = viewport_size
        self.ww, self.wh = world_size
        self.ox = 0
        self.oy = 0

    def follow(self, target_rect: pygame.Rect, lerp=1.0):
        cx = target_rect.centerx - self.vw // 2
        cy = target_rect.centery - self.vh // 2
        cx = max(0, min(cx, self.ww - self.vw))
        cy = max(0, min(cy, self.wh - self.vh))
        self.ox += (cx - self.ox) * lerp
        self.oy += (cy - self.oy) * lerp

    def offset(self):
        return int(self.ox), int(self.oy)