# parallax.py
import pygame
from pathlib import Path

# Intentar usar tus constantes si existen
try:
    import constantes
    SCREEN_W = constantes.ANCHO_VENTANA
    SCREEN_H = constantes.ALTO_VENTANA
except Exception:
    SCREEN_W, SCREEN_H = 1280, 720

BASE_DIR = Path(__file__).resolve().parent
IMG_ROOT = BASE_DIR / "assets" / "images" / "parallax"

# ==========================================================
#                    CLASES BASE
# ==========================================================

class ParallaxLayer:
    def __init__(self, image: pygame.Surface, speed_factor: float, y: int = 0):
        self.image = image.convert_alpha()
        self.speed = float(speed_factor)
        self.y = int(y)
        self.w = self.image.get_width()
        self.h = self.image.get_height()
        self.scroll = 0.0

    def update_by_camera(self, camera_dx: float):
        self.scroll += camera_dx * self.speed
        if abs(self.scroll) > 1e6:
            self.scroll %= self.w

    def draw(self, screen: pygame.Surface):
        offset_x = int(self.scroll) % self.w
        x0 = -offset_x
        for i in range(0, SCREEN_W // self.w + 3):
            screen.blit(self.image, (x0 + i * self.w, self.y))


class ParallaxBackground:
    def __init__(self, layers: list["ParallaxLayer"]):
        self.layers = layers or []

    def update_by_camera(self, camera_dx: float):
        for layer in self.layers:
            layer.update_by_camera(camera_dx)

    def draw(self, screen: pygame.Surface):
        for layer in self.layers:
            layer.draw(screen)


# ==========================================================
#                FUNCIONES INTERNAS
# ==========================================================

def _load_scaled(path: Path, fit_h: int) -> pygame.Surface:
    img = pygame.image.load(str(path)).convert_alpha()
    new_w = int(img.get_width() * (fit_h / img.get_height()))
    return pygame.transform.scale(img, (new_w, fit_h))

def _auto_speeds(num_layers: int) -> list[float]:
    """Genera velocidades crecientes automáticamente."""
    if num_layers <= 1:
        return [0.0]
    step = 0.9 / max(1, num_layers - 1)
    return [round(0.02 + i * step, 3) for i in range(num_layers)]

def _build_layers(folder: Path, speeds=None, y_offsets=None) -> list[ParallaxLayer]:
    """Carga imágenes numeradas (1.png, 2.png, ...)."""
    images = sorted([p for p in folder.glob("*.png") if p.stem.isdigit()],
                    key=lambda p: int(p.stem))
    n = len(images)
    if n == 0:
        return []
    speeds = speeds or _auto_speeds(n)
    y_offsets = y_offsets or [0] * n

    layers = []
    for i, path in enumerate(images):
        spd = speeds[i] if i < len(speeds) else speeds[-1]
        oy = y_offsets[i] if i < len(y_offsets) else 0
        try:
            img = _load_scaled(path, SCREEN_H)
            layers.append(ParallaxLayer(img, spd, oy))
        except Exception as e:
            print(f"[Parallax] No se pudo cargar {path.name}: {e}")
    return layers


# ==========================================================
#           VELOCIDADES PERSONALIZADAS POR NIVEL
# ==========================================================

LEVEL_SPEEDS = {

    # Movimiento equilibrado
    "nivel1": [0.02, 0.10, 0.28, 0.55, 0.90],


    # Barco lento (capa 2), cielo casi fijo
    "nivel2": [0.01, 0.05, 0.14, 0.30, 0.55, 0.90],


    # Más rápido y dinámico
    "nivel3": [0.02, 0.10, 0.28, 0.50, 0.80],
}


# ==========================================================
#                  FÁBRICA PRINCIPAL
# ==========================================================

def create_parallax(level_name: str = "nivel1",
                    speeds: list[float] | None = None,
                    y_offsets: list[int] | None = None) -> ParallaxBackground:
    """
    Carga imágenes numeradas (1.png, 2.png...) desde:
    assets/images/parallax/<level_name>/
    Aplica velocidades personalizadas según el nivel.
    """
    folder = IMG_ROOT / level_name

    # Si no se pasan velocidades, usa las personalizadas por nivel
    speeds = speeds or LEVEL_SPEEDS.get(level_name)

    layers = _build_layers(folder, speeds, y_offsets)

    if layers:
        return ParallaxBackground(layers)

    # Fondo plano por si no hay imágenes
    plano = pygame.Surface((SCREEN_W, SCREEN_H))
    plano.fill((8, 12, 28))
    return ParallaxBackground([ParallaxLayer(plano, 0.0, 0)])


# ==========================================================
#              ALIAS DE CREACIÓN POR NIVEL
# ==========================================================

def create_parallax_nivel1():
    return create_parallax("nivel1")

def create_parallax_nivel2():
    return create_parallax("nivel2")

def create_parallax_nivel3():
    return create_parallax("nivel3")
