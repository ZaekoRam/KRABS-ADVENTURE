# fuentes.py
from pathlib import Path
import pygame

# Caché para que no se cargue la fuente cada vez
_FONT_CACHE = {}
# Detecta la fuente en assets/fonts/
def _find_font_file():
    base = Path(__file__).resolve().parent / "assets" / "fonts"
    for name in ("PressStart2P.ttf", "pressstart2p.ttf", "pixel.ttf"):
        p = base / name
        if p.exists():
            return str(p)
    return None  # fallback a default

_FONT_PATH = _find_font_file()

def get_font(size: int) -> pygame.font.Font:
    """Devuelve una pygame.font.Font con caché, usando la fuente pixel si está disponible."""
    k = int(size)
    if k not in _FONT_CACHE:
        if _FONT_PATH:
            _FONT_CACHE[k] = pygame.font.Font(_FONT_PATH, k)
        else:
            _FONT_CACHE[k] = pygame.font.Font(None, k)  # fallback
    return _FONT_CACHE[k]

def render_outline(text, size, color=(255,255,255), outline=(0,0,0)):
    """Renderiza texto con contorno de 1px (look retro). Devuelve Surface ya compuesta."""
    f = get_font(size)
    txt = f.render(text, True, color)
    sh  = f.render(text, True, outline)

    surf = pygame.Surface((txt.get_width()+2, txt.get_height()+2), pygame.SRCALPHA)
    # “contorno” 1px alrededor
    surf.blit(sh, (0,1)); surf.blit(sh, (2,1))
    surf.blit(sh, (1,0)); surf.blit(sh, (1,2))
    # texto principal centrado
    surf.blit(txt, (1,1))
    return surf
