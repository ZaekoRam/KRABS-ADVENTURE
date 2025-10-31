import pygame
import constantes
from pathlib import Path

class Enemigo(pygame.sprite.Sprite):
    def __init__(self, x, y, velocidad=2, escala=2):  # <-- Añade el parámetro escala
        super().__init__()
        self.puntos = 100
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

        self.render_offset_y = 1  # o el valor que se vea bien
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
        self.INTERVALO_SALTO = 2  # Un poco más corto para que no espere tanto
        self.salto_timer = self.INTERVALO_SALTO

        # --- ATRIBUTOS DE VIDA Y DAÑO ---
        self.vida = 3
        self.hit_flash_timer = 0
        self.HIT_FLASH_DURACION = 0.5  # Duración del destello rojo

    # --- METODO PARA RECIBIR DAÑO ---
    def hurt(self, damage):
        # Solo puede recibir daño si no está ya dañado y su vida es > 0
        if self.hit_flash_timer <= 0 and self.vida > 0:
            self.vida -= damage
            # Al recibir daño, se activa el temporizador. Mientras sea > 0,
            # la condición de arriba no se cumplirá y el enemigo será invencible.
            self.hit_flash_timer = self.HIT_FLASH_DURACION


            print(f"Enemigo golpeado, vida restante: {self.vida}")
            if self.vida <= 0:
                self.kill()

    def update(self, dt, plataformas):

        # --- MANEJO DEL DESTELLO ROJO ---
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt

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

        self.image = frames_actuales[self.frame_index]

        # --- APLICA EL EFECTO DE DESTELLO ROJO (NUEVO) ---
        if self.hit_flash_timer > 0:
            # Crea una copia para no modificar el frame original de la animación
            self.image = self.image.copy()
            # Rellena la imagen con rojo usando un modo de mezcla especial
            self.image.fill((150, 0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # Voltea la imagen si es necesario (después de aplicar el destello)
        if self.direccion == -1:
            self.image = pygame.transform.flip(self.image, True, False)

    def tocar_jugador(self, jugador):
        return self.rect.colliderect(jugador.forma)

class Enemigo_walk(pygame.sprite.Sprite):
    def __init__(self, x, y, velocidad=80, vida=3, dano=1):
        super().__init__()
        self.puntos = 200

        # --- Rutas y helpers ---
        base_dir = Path(__file__).resolve().parent
        enemy1_dir = base_dir / "assets" / "images" / "enemigos" / "enemigo2"

        def load(path: Path) -> pygame.Surface:
            return pygame.image.load(str(path)).convert_alpha()

        def scale(img: pygame.Surface) -> pygame.Surface:
            return pygame.transform.scale(
                img,
                (
                    int(img.get_width() * constantes.ANCHO_IMAGEN * 0.7),
                    int(img.get_height() * constantes.ALTO_IMAGEN * 0.7),
                ),
            )

        # --- Cargar 6 frames de caminar ---
        frames = []
        # patrón principal: enemy_walk1..6.png
        for i in range(1, 7):
            p = enemy1_dir / f"enemigo_walk{i}.png"
            if p.exists():
                frames.append(scale(load(p)))

        self.frames_walk = frames
        self.frame_index = 0
        self.anim_timer = 0.0
        self.ANIM_FRAME_TIME = 0.10  # ~10 fps
        self.render_offset_y = 9  # <- prueba 4–10 px hasta que te guste

        self.image = self.frames_walk[self.frame_index]
        self.desfase_baba = 10  # píxeles hacia abajo, ajusta a gusto (5–15 según el sprite)
        self.rect = self.image.get_rect(midbottom=(x, y ))



        # --- Movimiento horizontal ---
        self.velocidad_mov = velocidad  # px/seg
        self.direccion = -1  # 1 derecha, -1 izquierda

        # --- Físicas verticales (para pararse en plataformas) ---
        self.vel_y = 0.0

        # --- Vida / Daño (compatibles con tu bloque de dificultad) ---
        self.vida_maxima = vida
        self.vida = vida
        self.dano = dano

        # --- Golpe/flash rojo ---
        self.hit_flash_timer = 0.0
        self.HIT_FLASH_DURACION = 0.5

    def hurt(self, damage):
        if self.hit_flash_timer <= 0 and self.vida > 0:
            self.vida -= damage
            self.hit_flash_timer = self.HIT_FLASH_DURACION
            print(f"Enemigo golpeado, vida restante: {self.vida}")
            if self.vida <= 0:
                self.kill()

    def tocar_jugador(self, jugador):
        return self.rect.colliderect(jugador.forma)

    def update(self, dt, plataformas):
        # --- Flash ---
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt

        # --- Movimiento X ---
        self.rect.x += self.velocidad_mov * self.direccion * dt

        # Rebotar en paredes/plataformas
        for rect in plataformas:
            if self.rect.colliderect(rect):
                if self.direccion > 0:
                    self.rect.right = rect.left
                else:
                    self.rect.left = rect.right
                self.direccion *= -1
                break

        # --- Gravedad + soporte ---
        self.vel_y += constantes.GRAVEDAD * dt
        self.rect.y += self.vel_y * dt

        for rect in plataformas:
            if self.rect.colliderect(rect):
                if self.vel_y > 0:
                    self.rect.bottom = rect.top
                    self.vel_y = 0
                elif self.vel_y < 0:
                    self.rect.top = rect.bottom
                    self.vel_y = 0

        # --- Animación caminar (6 frames) ---
        self.anim_timer += dt
        if self.anim_timer >= self.ANIM_FRAME_TIME:
            self.anim_timer = 0.0
            self.frame_index = (self.frame_index + 1) % len(self.frames_walk)

        self.image = self.frames_walk[self.frame_index]

        # Destello rojo
        if self.hit_flash_timer > 0:
            self.image = self.image.copy()
            self.image.fill((150, 0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # Volteo según dirección
        if self.direccion == 1:
            self.image = pygame.transform.flip(self.image, True, False)



class EnemigoPezueso(pygame.sprite.Sprite):
    """
    Pez acuático tipo 'Fishbone':
    - Nada hacia la izquierda constantemente.
    - Cuando detecta al jugador, tiembla 1 segundo (advertencia).
    - Luego entra en modo furioso y lo persigue con leve imprecisión.
    """
    def __init__(self, x, y, jugador,
                 velocidad_patulla=120, velocidad_furia=260,
                 radio_det=220, duracion_furia_ms=2000,
                 dir_inicial=-1, mundo_bounds=None, escala_extra=1.0):
        super().__init__()
        self.puntos = 250
        self.jugador = jugador
        self.render_offset_y = 0  # compatibilidad con tu sistema de render

        # --- Rutas y helpers ---
        base_dir = Path(__file__).resolve().parent
        enemy_dir = base_dir / "assets" / "images" / "enemigos" / "enemigo3"  # asegúrate de que coincida con tu carpeta

        def load(path: Path) -> pygame.Surface:
            return pygame.image.load(str(path)).convert_alpha()

        def scale(img: pygame.Surface) -> pygame.Surface:
            w = int(img.get_width() * constantes.ANCHO_IMAGEN * escala_extra)
            h = int(img.get_height() * constantes.ALTO_IMAGEN * escala_extra)
            return pygame.transform.scale(img, (w, h))

        import re, os
        def sort_key(fn: str) -> int:
            m = re.search(r'(\d+)(?=\.[a-zA-Z]{3,4}$)', fn)
            return int(m.group(1)) if m else 0

        if not enemy_dir.exists():
            raise FileNotFoundError(f"No existe {enemy_dir}")

        exts = {".png", ".jpg", ".jpeg"}
        archivos = [f for f in os.listdir(enemy_dir) if Path(f).suffix.lower() in exts]
        nadar_files   = sorted([f for f in archivos if f.lower().startswith("nadar")],   key=sort_key)
        furioso_files = sorted([f for f in archivos if f.lower().startswith("furioso")], key=sort_key)
        if not nadar_files:
            raise RuntimeError("No encontré frames 'nadar*.png' en enemigo3")
        if not furioso_files:
            raise RuntimeError("No encontré frames 'furioso*.png' en enemigo3")

        self.frames_idle  = [scale(load(enemy_dir / f)) for f in nadar_files]
        self.frames_angry = [scale(load(enemy_dir / f)) for f in furioso_files]

        # --- Estado / animación ---
        self.estado = "patrulla"  # patrulla | detecta | furioso
        self.frame_index = 0
        self.ANIM_DT_IDLE  = 1 / 8
        self.ANIM_DT_ANGRY = 1 / 10
        self._anim_accum = 0.0
        self._anim_step = self.ANIM_DT_IDLE

        # --- Sprite base ---
        self.image = self.frames_idle[self.frame_index]
        self.rect = self.image.get_rect(center=(int(x), int(y)))

        # --- Movimiento ---
        self.dir = -1  # siempre inicia nadando hacia la izquierda
        self.v_pat = float(velocidad_patulla)
        self.v_fur = float(velocidad_furia)
        self.radio_det = float(radio_det)
        self.furia_ms = int(duracion_furia_ms)
        self._furia_desde = 0
        self._flip_h = False
        self.mundo_bounds = mundo_bounds

        # --- Nuevos atributos para temblor ---
        self.deteccion_duracion = 1000  # ms (1 segundo)
        self.deteccion_inicio = 0
        self.temblor_intensidad = 3  # px

        # --- Vida / daño ---
        self.vida = 3
        self.hit_flash_timer = 0.0
        self.HIT_FLASH_DURACION = 0.5

    # -------------------------
    # Métodos auxiliares
    # -------------------------
    def _player_rect(self):
        return getattr(self.jugador, "forma", getattr(self.jugador, "rect", None))

    def hurt(self, damage):
        if self.hit_flash_timer <= 0 and self.vida > 0:
            self.vida -= damage
            self.hit_flash_timer = self.HIT_FLASH_DURACION
            print(f"Pezueso golpeado, vida restante: {self.vida}")
            if self.vida <= 0:
                self.kill()

    def tocar_jugador(self, jugador):
        pj = getattr(jugador, "forma", getattr(jugador, "rect", None))
        if pj is None:
            return False
        bite = self.rect.inflate(-self.rect.w * 0.3, -self.rect.h * 0.3)
        return bite.colliderect(pj)

    # -------------------------
    # Comportamiento principal
    # -------------------------
    def update(self, dt, _plataformas_no_usadas):
        # --- Flash rojo ---
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt

        pj = self._player_rect()
        if pj is not None:
            dx = pj.centerx - self.rect.centerx
            dy = pj.centery - self.rect.centery
            dist = (dx * dx + dy * dy) ** 0.5
        else:
            dx = dy = 0
            dist = 99999

        now = pygame.time.get_ticks()

        # --- FSM (estados) ---
        if self.estado == "patrulla":
            if dist <= self.radio_det:
                self.estado = "detecta"
                self.deteccion_inicio = now
                self._anim_step = self.ANIM_DT_IDLE
        elif self.estado == "detecta":
            if now - self.deteccion_inicio > self.deteccion_duracion:
                self.estado = "furioso"
                self._furia_desde = now
                self._anim_step = self.ANIM_DT_ANGRY
        elif self.estado == "furioso":
            lejos = dist > self.radio_det * 1.8
            expiro = (now - self._furia_desde) > self.furia_ms
            if lejos or expiro:
                self.estado = "patrulla"
                self._anim_step = self.ANIM_DT_IDLE

        # --- Movimiento según estado ---
        if self.estado == "patrulla":
            # nada siempre hacia la izquierda
            self.rect.x -= int(self.v_pat * dt)

        elif self.estado == "detecta":
            # tiembla ligeramente
            import random
            shake_x = random.randint(-self.temblor_intensidad, self.temblor_intensidad)
            shake_y = random.randint(-self.temblor_intensidad, self.temblor_intensidad)
            self.rect.x += shake_x
            self.rect.y += shake_y

        elif self.estado == "furioso":
            # persecución con error
            import math, random
            ang = math.atan2(dy, dx)
            error = random.uniform(-0.17, 0.17)  # ±10° de error
            ang += error
            self.rect.x += int(math.cos(ang) * self.v_fur * dt)
            self.rect.y += int(math.sin(ang) * self.v_fur * dt)

        # --- Límites del mundo ---
        if self.mundo_bounds:
            L, T, R, B = self.mundo_bounds
            if self.rect.right < L:
                self.rect.left = R
            if self.rect.top < T:
                self.rect.top = T
            elif self.rect.bottom > B:
                self.rect.bottom = B

        # --- Animación ---
        self._anim_accum += dt
        frames = self.frames_angry if self.estado == "furioso" else self.frames_idle
        while self._anim_accum >= self._anim_step:
            self._anim_accum -= self._anim_step
            self.frame_index = (self.frame_index + 1) % len(frames)
            self.image = frames[self.frame_index]

        # --- Flip (siempre mirando a la izquierda) ---
        flip = True
        if flip != self._flip_h:
            self.image = pygame.transform.flip(self.image, True, False)
            self._flip_h = flip

        # --- Flash rojo (daño) ---
        if self.hit_flash_timer > 0:
            self.image = self.image.copy()
            self.image.fill((150, 0, 0), special_flags=pygame.BLEND_RGB_ADD)



