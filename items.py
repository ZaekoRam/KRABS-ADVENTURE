import pygame
from pathlib import Path


# --- Clase para la Manzana ---
class botella(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        # Carga la imagen específica de la manzana
        try:
            ruta_imagen = Path(__file__).resolve().parent / "assets" / "images" / "items" / "botella.png"
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
            self.image = pygame.transform.scale2x(self.image)
            # ====== ESCALAR LA IMAGEN ======
            scale = 1  # <-- cambia este valor (1.0 = normal, 2.0 = doble)
            new_w = int(self.image.get_width() * scale)
            new_h = int(self.image.get_height() * scale)
            self.image = pygame.transform.smoothscale(self.image, (new_w, new_h))
        except pygame.error as e:
            print(f"Error al cargar la imagen 'bolsa_basura.png': {e}")
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 0, 0))  # Cuadrado rojo si falla

        # El rectángulo (hitbox) del ítem
        self.rect = self.image.get_rect(topleft=(x, y))

        # Puntos que da este ítem
        self.puntos = 300

    def tocar_jugador(self, jugador):
        return self.rect.colliderect(jugador.forma)


class lamina(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        # Carga la imagen específica de la manzana
        try:
            ruta_imagen = Path(__file__).resolve().parent / "assets" / "images" / "items" / "lamina.png"
            self.image = pygame.image.load(str(ruta_imagen)).convert_alpha()
        except pygame.error as e:
            print(f"Error al cargar la imagen 'manzana.png': {e}")
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 0, 0))  # Cuadrado rojo si falla

        # El rectángulo (hitbox) del ítem
        self.rect = self.image.get_rect(topleft=(x, y))

        # Puntos que da este ítem
        self.puntos = 250

    def tocar_jugador(self, jugador):
        return self.rect.colliderect(jugador.forma)

class llanta(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        # Carga la imagen específica de la manzana
        try:
            ruta_imagen = Path(__file__).resolve().parent / "assets" / "images" / "items" / "llanta.png"
            self.image = pygame.image.load(str(ruta_imagen)).convert_alpha()
            self.image = pygame.transform.scale(
                self.image,
                (int(self.image.get_width() * 1.5), int(self.image.get_height() * 1.5))
            )
        except pygame.error as e:
            print(f"Error al cargar la imagen 'manzana.png': {e}")
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 0, 0))  # Cuadrado rojo si falla

        # El rectángulo (hitbox) del ítem
        self.rect = self.image.get_rect(topleft=(x, y))

        # Puntos que da este ítem
        self.puntos = 200

    def tocar_jugador(self, jugador):
        return self.rect.colliderect(jugador.forma)

class gustambo(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()

        # Carga la imagen específica de la manzana
        try:
            ruta_imagen = Path(__file__).resolve().parent / "assets" / "images" / "items" / "tambo.png"
            self.image = pygame.image.load(str(ruta_imagen)).convert_alpha()
            self.image = pygame.transform.scale(
                self.image,
                (int(self.image.get_width() * 1.5), int(self.image.get_height() * 1.5))
            )
        except pygame.error as e:
            print(f"Error al cargar la imagen 'tambo.png': {e}")
            self.image = pygame.Surface((32, 32))
            self.image.fill((255, 0, 0))  # Cuadrado rojo si falla

        # El rectángulo (hitbox) del ítem
        self.rect = self.image.get_rect(topleft=(x, y))

        # Puntos que da este ítem
        self.puntos = 500

    def tocar_jugador(self, jugador):
        return self.rect.colliderect(jugador.forma)
