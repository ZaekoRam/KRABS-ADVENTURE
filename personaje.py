import pygame
import constantes
from pathlib import Path

class Personaje(pygame.sprite.Sprite):
    def __init__(self, spawn_x: int, spawn_y: int):
        super().__init__()

        base_dir = Path(__file__).resolve().parent
        krab_dir = base_dir / "assets" / "images" / "characters" / "krabby"

        # ---- helpers de carga/escala ----
        def load(name: str) -> pygame.Surface:
            return pygame.image.load(str(krab_dir / name)).convert_alpha()

        def scale(img: pygame.Surface) -> pygame.Surface:
            return pygame.transform.scale(
                img,
                (
                    int(img.get_width()  * constantes.ANCHO_IMAGEN),
                    int(img.get_height() * constantes.ALTO_IMAGEN),
                ),
            )

        # ---- FRAMES ----
        self.frames_idle = [scale(load(f"idle{i}.png")) for i in range(1, 3)]   # 2 frames
        self.frames_run  = [scale(load(f"krabby{i}.png")) for i in range(1, 5)]
        self.frames_jump = [scale(load(f"jump{i}.png"))   for i in range(1, 8)]  # 7 frames de salto

        # ---- estado y anim ----
        self.state        = "idle"
        self.facing_right = True
        self.anim_index   = 0.0
        self.run_fps      = 10.0   # velocidad al correr
        self.jump_fps     = 8.0    # salto
        self.idle_fps     = 2.0    # idle lento (2 frames por segundo)

        # ---- física ----
        self.vel_y   = 0.0
        self.en_piso = False

        # ---- render y rect ----
        self.image = self.frames_idle[0]
        self.forma = self.image.get_rect()
        self.forma.midbottom = (int(spawn_x), int(spawn_y))

        self._pos_x = float(self.forma.x)

    # ---------------- API ----------------
    def colocar_en_midbottom(self, x, y):
        self.forma.midbottom = (int(x), int(y))
        self._pos_x = float(self.forma.x)

    def movimiento(self, delta_x: float, _delta_y_ignorado: float = 0.0):
        self._pos_x += float(delta_x)
        self.forma.x = int(self._pos_x)

    def set_dx(self, dx_pixels_per_sec: float):
        if dx_pixels_per_sec > 0:
            self.facing_right = True
        elif dx_pixels_per_sec < 0:
            self.facing_right = False

        if self.en_piso:
            if dx_pixels_per_sec != 0:
                self.state = "run"
            else:
                self.state = "idle"

    def saltar(self, forzado: bool = False):
        if self.en_piso or forzado:
            self.vel_y = constantes.SALTO_VEL
            self.en_piso = False
            self.state = "jump"
            self.anim_index = 0.0

    def aplicar_gravedad(self, dt: float):
        self.vel_y += constantes.GRAVEDAD * dt

    def actualizar(self, dt: float):
        self.aplicar_gravedad(dt)

    def animar(self, dt: float):
        if self.state == "idle":
            self.anim_index += self.idle_fps * dt
            if self.anim_index >= len(self.frames_idle):
                self.anim_index = 0.0
            frame = self.frames_idle[int(self.anim_index)]

        elif self.state == "run":
            self.anim_index += self.run_fps * dt
            if self.anim_index >= len(self.frames_run):
                self.anim_index = 0.0
            frame = self.frames_run[int(self.anim_index)]

        elif self.state == "jump":
            self.anim_index += self.jump_fps * dt
            idx = min(int(self.anim_index), len(self.frames_jump) - 1)
            frame = self.frames_jump[idx]

        elif self.state == "fall":
            frame = self.frames_jump[-1]

        else:
            frame = self.frames_idle[0]



        # flip según dirección
        self.image = frame if self.facing_right else pygame.transform.flip(frame, True, False)

    def verificar_caida(self, altura_mapa):
        if self.forma.top > altura_mapa:
            self.morir()  # o cualquier lógica de muerte/reinici