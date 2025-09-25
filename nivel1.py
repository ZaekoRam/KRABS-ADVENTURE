# nivel1.py
from pathlib import Path
import pygame
from pytmx.util_pygame import load_pygame

class NivelTiled:
    def __init__(self, ruta_tmx: Path):
        self.tmx = load_pygame(str(ruta_tmx))
        self.tile_w = self.tmx.tilewidth
        self.tile_h = self.tmx.tileheight
        self.width_px  = self.tmx.width  * self.tile_w
        self.height_px = self.tmx.height * self.tile_h

        # --------- construir colisiones desde capa con propiedad solid=true ---------
        self.collision_rects = []

        tw, th = self.tile_w, self.tile_h
        for layer in self.tmx.layers:
            if hasattr(layer, "data"):
                if bool(layer.properties.get("solid", False)):
                    data = getattr(layer, "data", None)
                    if not data:
                        continue
                    # compacta por filas
                    for y in range(self.tmx.height):
                        x = 0
                        row = data[y]
                        while x < self.tmx.width:
                            gid = row[x]
                            if gid:
                                x0 = x
                                while x < self.tmx.width and row[x]:
                                    x += 1
                                rect = pygame.Rect(x0 * tw, y * th, (x - x0) * tw, th)
                                self.collision_rects.append(rect)
                            else:
                                x += 1

        # --------- spawn opcional ---------
        self.spawn = None
        if "Spawns" in self.tmx.objectgroups:
            for obj in self.tmx.objectgroups["Spawns"]:
                if getattr(obj, "name", "") == "player":
                    # Si es un rectángulo en Tiled, x,y son la esquina sup-izq.
                    w = int(getattr(obj, "width", 0) or 0)
                    h = int(getattr(obj, "height", 0) or 0)
                    if w > 0 or h > 0:
                        # midbottom del rectángulo
                        sx = int(obj.x) + w // 2
                        sy = int(obj.y) + h
                    else:
                        # si es un punto/objeto sin tamaño, usa x,y tal cual
                        sx = int(obj.x)
                        sy = int(obj.y)
                    self.spawn = (sx, sy)
                    break

    def draw(self, surface: pygame.Surface, camera_offset):
        ox, oy = camera_offset
        sw, sh = surface.get_size()
        x0 = max(0, ox // self.tile_w)
        y0 = max(0, oy // self.tile_h)
        x1 = min(self.tmx.width, (ox + sw) // self.tile_w + 2)
        y1 = min(self.tmx.height, (oy + sh) // self.tile_h + 2)

        for layer in self.tmx.visible_layers:
            if hasattr(layer, "tiles"):  # dibuja solo capas de tiles
                for x, y, image in layer.tiles():
                    if x0 <= x < x1 and y0 <= y < y1:
                        surface.blit(image, (x * self.tile_w - ox, y * self.tile_h - oy))

    def world_size(self):
        return self.width_px, self.height_px
