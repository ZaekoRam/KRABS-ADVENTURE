import pygame
from pathlib import Path

class manzana(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        base_dir = Path(__file__).resolve().parent
        botella_dir = base_dir / "assets" / "images" / "items" / "manzana"

    def tocar_jugador(self, jugador):
        return self.rect.colliderect(jugador.forma)