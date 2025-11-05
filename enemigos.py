import pygame
import constantes
from pathlib import Path
import random

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
        # Solo puede recibir daño si no está ya dañado y su vida es > 0
        if self.hit_flash_timer <= 0 and self.vida > 0:
            self.vida -= damage
            # Al recibir daño, se activa el temporizador. Mientras sea > 0,
            # la condición de arriba no se cumplirá y el enemigo será invencible.
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


# --- CLASE DEL PEZ HUESO ---
# Pega esto al FINAL de tu archivo enemigos.py

# --- CLASE DEL PEZ HUESO (AHORA "ENEMIGOPEZUCSO") ---
# REEMPLAZA la clase EnemigoPezueso vieja con esta

# --- CLASE DEL PEZ HUESO (AHORA "ENEMIGOPEZUCSO") ---
# PEGA ESTE CÓDIGO COMPLETO EN ENEMIGOS.PY

# --- CLASE DEL PEZ HUESO (AHORA "ENEMIGOPEZUCSO") ---
# PEGA ESTE CÓDIGO COMPLETO EN ENEMIGOS.PY

# --- CLASE DEL PEZ HUESO (AHORA "ENEMIGOPEZUCSO") ---
# PEGA ESTE CÓDIGO COMPLETO EN ENEMIGOS.PY

class EnemigoPezueso(Enemigo):
    """
    Enemigo estilo "Fishbone".
    Usa los assets de 'enemigo3' (nadar/furioso).
    Patrulla, detecta al jugador, tiembla (anim furioso) y se lanza (anim furioso).

    Versión con corrección de:
    - Dirección inicial (respeta 'dir_inicial').
    - "Teleport" (añade gracia de 0.5s en colisión de ataque).
    """

    def __init__(self, x, y, jugador,
                 velocidad_patrulla=45,
                 velocidad_furia=7,
                 radio_det=250,
                 punto_b_x=None,
                 dir_inicial=1,  # <-- AHORA SÍ LO USAMOS
                 **kwargs):

        pygame.sprite.Sprite.__init__(self)

        # --- Directorio de Sprites (enemigo3) ---
        base_dir = Path(__file__).resolve().parent
        sprite_dir = base_dir / "assets" / "images" / "enemigos" / "enemigo3"

        # --- Referencias e Imágenes ---
        self.jugador = jugador
        self.frames_patrulla = []  # Animación "nadar"
        self.frames_ataque = []  # Animación "furioso"

        try:
            # NOTA: Estas imágenes DEBEN estar mirando hacia la DERECHA por defecto
            for i in range(1, 4):
                ruta = sprite_dir / f"nadar{i}.png"
                self.frames_patrulla.append(pygame.image.load(str(ruta)).convert_alpha())
            for i in range(1, 3):
                ruta = sprite_dir / f"furioso{i}.png"
                self.frames_ataque.append(pygame.image.load(str(ruta)).convert_alpha())

        except FileNotFoundError as e:
            print(f"--- ERROR URGENTE ---")
            print(f"No se encontraron las imágenes en: {sprite_dir}")
            print(f"Asegúrate que 'nadar1.png', 'furioso1.png', etc., existan allí.")
            print(f"Error original: {e}")
            print(f"---------------------")
            # Fallback
            self.frames_patrulla = [pygame.Surface((30, 30), pygame.SRCALPHA)]
            self.frames_patrulla[0].fill((0, 255, 0))  # Verde
            self.frames_ataque = [pygame.Surface((30, 30), pygame.SRCALPHA)]
            self.frames_ataque[0].fill((255, 0, 0))  # Rojo

        # --- Variables de Animación ---
        self.anim_index = 0.0
        self.anim_velocidad = 0.2
        self.image = self.frames_patrulla[0]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.hit_flash_timer = 0.0
        self.vida = 2
        self.HIT_FLASH_DURACION = 0.5

        # --- Atributos de Patrulla ---
        self.punto_a_x = x
        self.punto_b_x = punto_b_x if punto_b_x is not None else x + 200
        self.pos_y_original = y
        self.velocidad_patrulla = velocidad_patrulla

        # --- Máquina de Estados ---
        self.estado = "PATRULLANDO"
        self.timer_estado = 0
        self.direccion_visual = dir_inicial  # <-- CORRECCIÓN DE DIRECCIÓN
        self.pos_tiemble_original = self.rect.topleft
        self.dt_actual = 0.0

        # --- Constantes de Comportamiento ---
        self.RANGO_VISION = radio_det
        self.TIEMPO_TEMBLOR = 60  # 1 segundo a 60 FPS
        self.velocidad_ataque = velocidad_furia

        # --- Vectores de Ataque ---
        self.direccion_ataque_vec = pygame.math.Vector2(0, 0)

        # --- Inicializar estado ---
        self.velocidad_x = self.velocidad_patrulla * self.direccion_visual  # <-- CORRECCIÓN DE DIRECCIÓN
        self.velocidad_y = 0
        self.puntos = 100
        self.render_offset_y = 0

    def hurt(self, damage):
        if self.hit_flash_timer <= 0 and self.vida > 0:
            self.vida -= damage
            self.hit_flash_timer = self.HIT_FLASH_DURACION
            print(f"Pezueso golpeado, vida restante: {self.vida}")
            if self.vida <= 0:
                self.kill()

    def update(self, dt, plataformas):
        self.dt_actual = dt

        if self.estado == "PATRULLANDO":
            self.patrullar()
            self.buscar_jugador()
            self.animar(self.frames_patrulla)

        elif self.estado == "DETECTANDO":
            self.temblar()
            self.animar(self.frames_ataque)

        elif self.estado == "ATACANDO":
            self.atacar(plataformas)
            self.animar(self.frames_ataque)
        # --- Flash rojo (daño) ---
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt
            if self.hit_flash_timer < 0:
                self.hit_flash_timer = 0

            if self.hit_flash_timer > 0:
                self.image = self.image.copy()
                self.image.fill((150, 0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def animar(self, frames_lista):
        """ Maneja el ciclo de animación """
        # La animación la basamos en 'dt' para que sea fluida
        self.anim_index += self.anim_velocidad * (self.dt_actual * 60)  # Asumiendo 60fps base
        if self.anim_index >= len(frames_lista):
            self.anim_index = 0.0

        self.image = frames_lista[int(self.anim_index)]

        # --- ¡CORRECCIÓN DE LÓGICA DE FLIP! ---
        # Si la dirección es 1 (DERECHA), volteamos la imagen (que mira a la IZQUIERDA)
        if self.direccion_visual == 1:  # <-- ESTE ES EL CAMBIO (1 en lugar de -1)
            self.image = pygame.transform.flip(self.image, True, False)
        # Si la dirección es -1 (IZQUIERDA), no hacemos nada (la imagen ya mira a la izquierda)

    def cambiar_estado(self, nuevo_estado):
        self.estado = nuevo_estado
        self.timer_estado = 0
        self.anim_index = 0.0

        if nuevo_estado == "PATRULLANDO":
            self.rect.x = self.punto_a_x
            self.rect.y = self.pos_y_original
            self.velocidad_x = self.velocidad_patrulla
            self.velocidad_y = 0
            # Al volver a patrullar, asegurarse que mira a la derecha
            if self.direccion_visual == -1:
                self.flip_sprite()
            self.velocidad_x = self.velocidad_patrulla * self.direccion_visual


        elif nuevo_estado == "DETECTANDO":
            self.velocidad_x = 0
            self.velocidad_y = 0
            self.pos_tiemble_original = self.rect.topleft

            try:
                dir_vec = pygame.math.Vector2(self.jugador.forma.center) - pygame.math.Vector2(self.rect.center)
                self.direccion_ataque_vec = dir_vec.normalize()
            except ValueError:
                self.direccion_ataque_vec = pygame.math.Vector2(1, 0)

            # Lógica para voltear
            if self.direccion_ataque_vec.x < 0 and self.direccion_visual == 1:
                self.flip_sprite()  # Si ataca a la izq. y miro a la der. -> voltear
            elif self.direccion_ataque_vec.x > 0 and self.direccion_visual == -1:
                self.flip_sprite()  # Si ataca a la der. y miro a la izq. -> voltear

        elif nuevo_estado == "ATACANDO":
            self.rect.topleft = self.pos_tiemble_original
            self.velocidad_x = self.direccion_ataque_vec.x * self.velocidad_ataque
            self.velocidad_y = self.direccion_ataque_vec.y * self.velocidad_ataque

    def patrullar(self):
        self.rect.x += self.velocidad_x * self.dt_actual

        if self.rect.right >= self.punto_b_x and self.velocidad_x > 0:
            self.rect.right = self.punto_b_x
            self.velocidad_x *= -1
            self.flip_sprite()
        elif self.rect.left <= self.punto_a_x and self.velocidad_x < 0:
            self.rect.left = self.punto_a_x
            self.velocidad_x *= -1
            self.flip_sprite()

    def buscar_jugador(self):
        dist = pygame.math.Vector2(self.jugador.forma.center).distance_to(self.rect.center)
        if dist < self.RANGO_VISION:
            self.cambiar_estado("DETECTANDO")

    def temblar(self):
        self.timer_estado += (self.dt_actual * 60)

        self.rect.x = self.pos_tiemble_original[0] + random.randint(-1, 1)
        self.rect.y = self.pos_tiemble_original[1] + random.randint(-1, 1)

        if self.timer_estado >= self.TIEMPO_TEMBLOR:
            self.cambiar_estado("ATACANDO")

    def atacar(self, plataformas):
        # Moverse
        self.rect.x += self.velocidad_x * self.dt_actual
        self.rect.y += self.velocidad_y * self.dt_actual

        # Aumentar el timer (contador de frames)
        self.timer_estado += (self.dt_actual * 60)

        # --- ¡¡AQUÍ ESTÁ LA CORRECCIÓN DEL TELEPORT!! ---
        # No comprobar colisiones durante los primeros 30 frames (0.5 seg)
        # Esto le da tiempo al pez de "salir" de la plataforma en la que está.
        if self.timer_estado > 30:
            indice_colision = self.rect.collidelist(plataformas)
            if indice_colision != -1:
                self.cambiar_estado("PATRULLANDO")

        # Si vuela por demasiado tiempo (5 seg) sin chocar, también se reinicia
        if self.timer_estado > (constantes.FPS * 5):
            self.cambiar_estado("PATRULLANDO")
            # --- FIN DE LA CORRECCIÓN ---

    def flip_sprite(self):
        """Invierte la dirección visual."""
        self.direccion_visual *= -1