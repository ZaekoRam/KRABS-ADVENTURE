# nivel.py
from pathlib import Path
import pygame
from pytmx.util_pygame import load_pygame

class NivelTiled:
    def __init__(self, ruta_tmx: Path):
        self.tmx = load_pygame(str(ruta_tmx))     # carga imágenes del tileset
        self.tile_w = self.tmx.tilewidth
        self.tile_h = self.tmx.tileheight
        self.width_px  = self.tmx.width  * self.tile_w
        self.height_px = self.tmx.height * self.tile_h
        self.collision_rects = []

        # Leer la capa de objetos llamada "Collisions"
        try:
            # 1. Intenta obtener la capa de objetos por su nombre
            collision_layer = self.tmx.get_layer_by_name("collisions")
            # Si el nombre es en minúsculas en Tiled, usa "collisions"

            # 2. Verifica que sea una capa de objetos (clase TiledObjectGroup)
            import pytmx
            if isinstance(collision_layer, pytmx.TiledObjectGroup):
                for obj in collision_layer:
                    # 3. Solo añadimos objetos con tamaño real
                    if obj.width > 0 and obj.height > 0:
                        rect = pygame.Rect(
                            int(obj.x),
                            int(obj.y),
                            int(obj.width),
                            int(obj.height)
                        )
                        self.collision_rects.append(rect)
                print(f"DEBUG: Se cargaron {len(self.collision_rects)} rectángulos de colisión.")  # DEBUGGING
            else:
                print("ADVERTENCIA: La capa 'Collisions' existe pero no es una TiledObjectGroup.")

        except ValueError:
            print("ADVERTENCIA: Capa de colisiones 'Collisions' no encontrada en el archivo TMX.")

        # Spawn opcional desde "Spawns" → objeto con name="player"
            # En main.py, dentro de NivelTiled.__init__

        self.spawn = None
        if "Spawns" in self.tmx.objectgroups:
            for obj in self.tmx.objectgroups["Spawns"]:
                if getattr(obj, "name", "") == "player":
                    self.spawn = (int(obj.x), int(obj.y));
                    break

    def draw(self, surface: pygame.Surface, camera_offset):
        ox, oy = camera_offset
        sw, sh = surface.get_size()

        # Recorte simple por tiles visibles
        x0 = max(0, ox // self.tile_w)
        y0 = max(0, oy // self.tile_h)
        x1 = min(self.tmx.width,  (ox + sw) // self.tile_w + 2)
        y1 = min(self.tmx.height, (oy + sh) // self.tile_h + 2)

        for layer in self.tmx.visible_layers:
            if hasattr(layer, "tiles"):  # solo capas de tiles
                for x, y, image in layer.tiles():
                    if x0 <= x < x1 and y0 <= y < y1:
                        surface.blit(image, (x * self.tile_w - ox, y * self.tile_h - oy))

    def world_size(self):
        return self.width_px, self.height_px
