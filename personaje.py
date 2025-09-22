import pygame
import constantes
from pathlib import Path

class Personaje:
    def __init__(self, x, y):
        base_dir = Path(__file__).resolve().parent
        img_dir = base_dir / "assets" / "images" / "characters" / "krabby"

        # Cargar frames
        self.frames_idle = [pygame.image.load(str(img_dir / "krabby1.png")).convert_alpha()]
        self.frames_run = [
            pygame.image.load(str(img_dir / f"krabby{i}.png")).convert_alpha()
            for i in range(1, 5)  # krabby1..4
        ]

        # Escalar
        self.frames_idle = [pygame.transform.scale(img, (
            int(img.get_width() * constantes.ANCHO_IMAGEN),
            int(img.get_height() * constantes.ALTO_IMAGEN)
        )) for img in self.frames_idle]

        self.frames_run = [pygame.transform.scale(img, (
            int(img.get_width() * constantes.ANCHO_IMAGEN),
            int(img.get_height() * constantes.ALTO_IMAGEN)
        )) for img in self.frames_run]

        # Estado inicial
        self.state = "idle"
        self.image = self.frames_idle[0]
        self.forma = self.image.get_rect(center=(x, y))
        self.vel_y = 0.0
        self.en_piso = False

        # Animación
        self.anim_index = 0.0
        self.anim_speed = 8.0  # frames por segundo
        self.facing_right = True

    def dibujar(self, interfaz):
        interfaz.blit(self.image, self.forma)

    def movimiento(self, delta_x, _delta_y_ignorado=0):
        self.forma.x += int(delta_x)
        if delta_x > 0:
            self.facing_right = True
        elif delta_x < 0:
            self.facing_right = False
        # Cambiar estado según movimiento
        self.state = "run" if delta_x != 0 else "idle"

    def saltar(self, forzado=False):
        if self.en_piso or forzado:
            self.vel_y = constantes.SALTO_VEL
            self.en_piso = False

    def actualizar(self, dt):
        # Física Y
        self.vel_y += constantes.GRAVEDAD * dt
        self.forma.y += int(self.vel_y * dt)

        suelo_top = constantes.ALTO_VENTANA - constantes.ALTURA_SUELO
        if self.forma.bottom >= suelo_top:
            self.forma.bottom = suelo_top
            self.vel_y = 0
            self.en_piso = True

        # Animación
        if self.state == "idle":
            frame_list = self.frames_idle
            self.anim_index = 0
        else:  # "run"
            frame_list = self.frames_run
            self.anim_index += self.anim_speed * dt
            if self.anim_index >= len(frame_list):
                self.anim_index = 0

        frame = frame_list[int(self.anim_index)]

        # Flip según dirección
        if self.facing_right:
            self.image = frame
        else:
            self.image = pygame.transform.flip(frame, True, False)
