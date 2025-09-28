import pygame
import constantes
from pathlib import Path

class Enemigo(pygame.sprite.Sprite):
    def __init__(self, x, y, velocidad=2, escala=2):  # <-- Añade el parámetro escala
        super().__init__()
        base_dir = Path(__file__).resolve().parent
        enemy1_dir = base_dir / "assets" / "images" / "enemigos" / "enemigo1"

        def load(name: str) -> pygame.Surface:
            return pygame.image.load(str(enemy1_dir / name)).convert_alpha()

        def scale(img: pygame.Surface) -> pygame.Surface:
            return pygame.transform.scale(
                img,
                (
                    int(img.get_width()  * constantes.ANCHO_IMAGEN),
                    int(img.get_height() * constantes.ALTO_IMAGEN),
                ),
            )
        # Calcula el nuevo tamaño
        self.frames_idle = [scale(load(f"enemy_idle{i}.png")) for i in range(1, 2)]
        self.frames_anticipate = [scale(load(f"enemy_anticipate{i}.png")) for i in range(1, 3)]  # <-- NUEVO
        self.frames_jump = [scale(load(f"enemy_jump{i}.png")) for i in range(2, 6)]
        self.frames_land = [scale(load(f"enemy_land{i}.png")) for i in range(1, 4)]

        self.estado = 'idle'  # <-- NUEVO: idle, jumping, falling, landing
        self.frame_index = 0
        self.anim_timer = 0
        self.ANIM_SPEED = 0.1
        self.aterrizando = False  # <-- NUEVO: Bandera para controlar la animación de aterrizaje

        # --- CONFIGURACIÓN INICIAL DEL SPRITE ---
        # La imagen inicial es el primer fotograma de la animación
        self.image = self.frames_idle[self.frame_index]
        self.rect = self.image.get_rect(midbottom=(x, y))


        # Escala la imagen y la asigna a self.image

        self.rect = self.image.get_rect(midbottom=(x, y))
        self.velocidad_movimiento = velocidad  # <-- RENOMBRADO: La velocidad que tendrá AL SALTAR
        self.vel_x = 0  # <-- NUEVO: Su velocidad horizontal actual. Empieza en 0.
        self.vel_y = 0
        self.direccion = 1

        # --- ATRIBUTOS PARA EL SALTO ---
        self.fuerza_salto = -500
        self.INTERVALO_SALTO = 1.5  # Un poco más corto para que no espere tanto
        self.salto_timer = self.INTERVALO_SALTO

    def update(self, dt, plataformas):
        # 1. LÓGICA DE DECISIÓN
        # ---------------------
        if self.salto_timer > 0:
            self.salto_timer -= dt

        # Si está quieto y el timer termina, NO salta, sino que INICIA LA ANTICIPACIÓN.
        if self.estado == 'idle' and self.salto_timer <= 0:
            self.estado = 'anticipating'
            self.frame_index = 0  # Reinicia la animación para el nuevo estado
            self.anim_timer = 0  # Reinicia el timer de la animación
            self.salto_timer = self.INTERVALO_SALTO  # Reinicia el timer principal

        # 2. MOVIMIENTO Y COLISIONES EN EJE X (Horizontal)
        # ------------------------------------------------
        self.rect.x += self.vel_x * self.direccion * dt

        # Revisa colisiones en el eje X
        for rect in plataformas:
            if self.rect.colliderect(rect):
                if self.vel_x * self.direccion > 0:  # Moviéndose a la derecha
                    self.rect.right = rect.left
                    self.direccion *= -1
                elif self.vel_x * self.direccion < 0:  # Moviéndose a la izquierda
                    self.rect.left = rect.right
                    self.direccion *= -1

        # 3. MOVIMIENTO Y COLISIONES EN EJE Y (Vertical)
        # ----------------------------------------------
        self.vel_y += constantes.GRAVEDAD * dt
        self.rect.y += self.vel_y * dt

        # Revisa colisiones en el eje Y
        for rect in plataformas:
            if self.rect.colliderect(rect):
                if self.vel_y > 0:  # Cayendo
                    self.rect.bottom = rect.top
                    self.vel_y = 0
                    self.vel_x = 0

                    if self.estado == 'falling':
                        self.estado = 'landing'
                        self.frame_index = 0
                        self.aterrizando = True
                elif self.vel_y < 0:  # Chocando con un techo
                    self.rect.top = rect.bottom
                    self.vel_y = 0

        # 4. TRANSICIÓN DE ESTADOS Y ANIMACIÓN
        # ------------------------------------
        # Solo puede empezar a caer si ya estaba saltando
        if self.estado == 'jumping' and self.vel_y > 0:
            self.estado = 'falling'

        self.animar(dt)


    def animar(self, dt):
        # Selecciona la lista de fotogramas correcta según el estado
        frames_actuales = []
        if self.estado == 'idle':
            frames_actuales = self.frames_idle
        elif self.estado == 'anticipating': # <-- NUEVO
            frames_actuales = self.frames_anticipate
        elif self.estado in ('jumping', 'falling'):
            frames_actuales = self.frames_jump
        elif self.estado == 'landing':
            frames_actuales = self.frames_land

        # Lógica para avanzar la animación
        self.anim_timer += dt
        if self.anim_timer >= self.ANIM_SPEED:
            self.anim_timer = 0
            self.frame_index += 1

            # Si la animación se acaba...
            if self.frame_index >= len(frames_actuales):
                if self.estado == 'anticipating':
                    # ¡ANIMACIÓN DE ANTICIPACIÓN TERMINADA! AHORA SALTA.
                    self.vel_y = self.fuerza_salto
                    self.vel_x = self.velocidad_movimiento
                    self.estado = 'jumping'
                    self.frame_index = 0 # Reinicia el índice para la animación de salto
                elif self.estado == 'idle':
                    self.frame_index = 0 # Bucle para la animación idle
                elif self.estado == 'landing':
                    self.frame_index = 0
                    self.estado = 'idle'
                    self.aterrizando = False
                elif self.estado in ('jumping', 'falling'):
                    self.frame_index = len(frames_actuales) - 1

        # Asigna la imagen correcta y la voltea si es necesario
        # (Control de error por si frames_actuales está vacío momentáneamente)
        if self.frame_index < len(frames_actuales):
            self.image = frames_actuales[self.frame_index]
            if self.direccion == -1:
                self.image = pygame.transform.flip(self.image, True, False)

    def tocar_jugador(self, jugador):
        return self.rect.colliderect(jugador.forma)