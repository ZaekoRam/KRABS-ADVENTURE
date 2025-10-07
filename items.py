import pygame
from pathlib import Path


# --- Clase para la Manzana ---
class Manzana(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        # Carga la imagen específica de la manzana
        try:
            ruta_imagen = Path(__file__).resolve().parent / "assets" / "images" / "items" / "manzana.png"
            self.image = pygame.image.load(str(ruta_imagen)).convert_alpha()
        except pygame.error as e:
            print(f"Error al cargar la imagen 'manzana.png': {e}")
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 0, 0))  # Cuadrado rojo si falla

        # El rectángulo (hitbox) del ítem
        self.rect = self.image.get_rect(topleft=(x, y))

        # Puntos que da este ítem
        self.puntos = 100

    def tocar_jugador(self, jugador):
        return self.rect.colliderect(jugador.forma)

class bolsa(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        # Carga la imagen específica de la manzana
        try:
            ruta_imagen = Path(__file__).resolve().parent / "assets" / "images" / "items" / "bolsa_basura.png"
            self.image = pygame.image.load(str(ruta_imagen)).convert_alpha()
        except pygame.error as e:
            print(f"Error al cargar la imagen 'bolsa_basura.png': {e}")
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 0, 0))  # Cuadrado rojo si falla

        # El rectángulo (hitbox) del ítem
        self.rect = self.image.get_rect(topleft=(x, y))

        # Puntos que da este ítem
        self.puntos = 500

    def tocar_jugador(self, jugador):
        return self.rect.colliderect(jugador.forma)