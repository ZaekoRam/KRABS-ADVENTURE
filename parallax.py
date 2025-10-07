# --- Parallax 3 capas: far (lento), mid (medio), near (rápido) ---
import pygame
from pathlib import Path

try:
    import constantes  # usa tus constantes si existen
    SCREEN_W = constantes.ANCHO_VENTANA
    SCREEN_H = constantes.ALTO_VENTANA
except Exception:
    # fallback por si no están disponibles
    SCREEN_W, SCREEN_H = 1280, 720

BASE_DIR = Path(__file__).resolve().parent
IMG_DIR  = BASE_DIR / "assets" / "images"

def _load_image_rel(rel_path: Path, fit_height: int = None) -> pygame.Surface:
    """Carga PNG con alpha; si fit_height se da, escala manteniendo aspect ratio al alto."""
    surf = pygame.image.load(rel_path).convert_alpha()
    if fit_height:
        h = fit_height
        w = int(surf.get_width() * (h / surf.get_height()))
        surf = pygame.transform.scale(surf, (w, h))
    return surf

class ParallaxLayer:
    def __init__(self, image: pygame.Surface, speed_factor: float, y: int = 0):
        """
        image: superficie base de la capa (se asume "tileable" horizontalmente).
        speed_factor: 0.0 = fija (fondo muy lejano), 1.0 = igual a la cámara.
        y: posición vertical donde pintar la capa.
        """
        self.image = image
        self.speed = speed_factor
        self.y = y
        self.w = image.get_width()
        self.h = image.get_height()
        self.scroll = 0.0  # acumulado para el wrap

    def update_by_camera(self, camera_dx: float):
        """Desplaza la textura según el movimiento horizontal de la cámara."""
        self.scroll += camera_dx * self.speed
        # normaliza para evitar overflow muy grande
        if self.scroll > 1e6 or self.scroll < -1e6:
            self.scroll = self.scroll % self.w

    def draw(self, screen: pygame.Surface):
        """Pinta la capa repetida para cubrir todo el ancho de pantalla."""
        # desplazamiento entero para alinear píxeles (evita jitter en pixel-art)
        offset_x = int(self.scroll) % self.w
        # Dibuja 2-3 tiles para cubrir todo el ancho
        x0 = -offset_x
        for i in range(0, SCREEN_W // self.w + 3):
            screen.blit(self.image, (x0 + i * self.w, self.y))

class ParallaxBackground:
    def __init__(self, layers: list[ParallaxLayer]):
        self.layers = layers

    def update_by_camera(self, camera_dx: float):
        for layer in self.layers:
            layer.update_by_camera(camera_dx)

    def draw(self, screen: pygame.Surface):
        # Orden: far -> mid -> near
        for layer in self.layers:
            layer.draw(screen)

def create_parallax_nivel1() -> ParallaxBackground:
    """
    Crea un parallax con las imágenes:
    assets/images/parallax/nivel1/far.png
    assets/images/parallax/nivel1/mid.png
    assets/images/parallax/nivel1/near.png
    Ajusta alturas para que todas llenen la ventana (o la franja que quieras).
    """
    base = IMG_DIR / "parallax" / "nivel1"

    # Escalamos cada capa al alto de pantalla para que siempre cubra verticalmente.
    far_img  = _load_image_rel(base / "far.png",  fit_height=SCREEN_H)
    mid_img  = _load_image_rel(base / "mid.png",  fit_height=SCREEN_H)
    near_img = _load_image_rel(base / "near.png", fit_height=SCREEN_H)

    # Velocidades: far lento, mid medio, near rápido (ajusta a tu gusto)
    # Tip: si usas cámara que se mueve +X a la derecha, near tendrá mayor desplazamiento.
    far_layer  = ParallaxLayer(far_img,  speed_factor=0.10, y=0)  # 20% de la cámara
    mid_layer  = ParallaxLayer(mid_img,  speed_factor=0.35, y=0)  # 45%
    near_layer = ParallaxLayer(near_img, speed_factor=0.75, y=0)  # 80%

    return ParallaxBackground([far_layer, mid_layer, near_layer])
