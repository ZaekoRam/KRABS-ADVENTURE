import pygame
import constantes
from pathlib import Path

class Personaje(pygame.sprite.Sprite):
    def __init__(self, spawn_x: int, spawn_y: int, gender = "M"):
        super().__init__()
        self.hit_sound_played = False  # 🔊 evita repetir sonido de golpe
        self.stun_sound_played = False

        self.gender = gender

        if self.gender == "M":
            sprite_folder = "assets/images/characters/krabby"  # Carpeta o sprites de Krabby
        else:
            sprite_folder = "assets/images/characters/karol"  # Carpeta o sprites de Karol

        base_dir = Path(__file__).resolve().parent

        # ---- helpers de carga/escala ----
        def load(name: str) -> pygame.Surface:
            return pygame.image.load(f"{sprite_folder}/{name}").convert_alpha()

        def scale(img: pygame.Surface) -> pygame.Surface:
            return pygame.transform.scale(
                img,
                (
                    int(img.get_width()  * constantes.ANCHO_IMAGEN),
                    int(img.get_height() * constantes.ALTO_IMAGEN),
                ),
            )

        # ---- FRAMES ---- (IGUAL QUE TENÍAS, PERO DEPENDIENDO DEL PERSONAJE)
        self.frames_idle = [scale(load(f"idle{i}.png")) for i in range(1, 3)]
        self.frames_run = [scale(load(f"run{i}.png")) for i in range(1, 5)]
        self.frames_jump = [scale(load(f"jump{i}.png")) for i in range(1, 8)]
        self.frames_attack = [scale(load(f"ataque{i}.png")) for i in range(1, 6)]

        # Estados de ataque
        self.attacking = False
        self.attack_timer = 0.0
        self.attack_duration = 0.25  # tiempo de ataque
        self.attack_cooldown = 0.4  # tiempo entre ataques
        self.attack_cooldown_timer = 0.0
        self.attack_damage = 1  # daño base del ataque


        # ---- estado y anim ----
        self.state        = "idle"
        self.facing_right = True
        self.anim_index   = 0.0
        self.run_fps      = 5.0   # velocidad al correr
        self.jump_fps     = 4.0    # salto
        self.idle_fps     = 1.0    # idle lento (2 frames por segundo)

        # ---- física ----
        self.vel_y   = 0.0
        self.en_piso = False

        # ---- render y rect ----
        self.image = self.frames_idle[0]
        self.forma = self.image.get_rect()
        self.forma.midbottom = (int(spawn_x), int(spawn_y))

        self._pos_x = float(self.forma.x)

        extra_x = 125 # píxeles adicionales a cada lado
        extra_y = 10  # píxeles adicionales arriba y abajo

        self.attack_w = self.image.get_width() + extra_x
        self.attack_h = self.image.get_height() + extra_y
        self.attack_offset_x = -extra_x // 2  # para centrar en X
        self.attack_offset_y = -extra_y // 2  # para centrar en Y

        # --- ATRIBUTOS DE VIDA Y DAÑO ---
        self.vida_maxima = 4
        self.vida_actual = self.vida_maxima
        self.invencible = False
        self.invencible_timer = 0
        self.INVENCIBLE_DURACION = .5  # 1.5 segundos de invencibilidad

        # --- ATRIBUTOS DE KNOCKBACK (NUEVO) ---
        self.knockback_speed_y = -400  # Impulso vertical (hacia arriba)
        self.knockback_speed_x = 200  # Impulso horizontal

    # ---------------- API ----------------

    # ---- METODO PARA REINICIAR AL JUGADOR (AÑADE ESTO) ----
    def reset(self, spawn_pos):
        # Resetea la posición y velocidad
        self.forma.x, self.forma.y = spawn_pos
        self.vel_y = 0

        # Resetea el estado de la animación
        self.state = "idle"
        self.attacking = False

        # ¡LA LÍNEA CLAVE! Resetea la vida
        self.vida_actual = self.vida_maxima

        # Resetea también la invencibilidad
        self.invencible = False
        self.invencible_timer = 0

    def recibir_dano(self, cantidad):
        # El jugador solo recibe daño si no es invencible
        if not self.invencible:
            self.vida_actual -= cantidad
            print(f"Vida restante: {self.vida_actual}")  # Mensaje para depurar
            self.vel_y = self.knockback_speed_y

            if self.vida_actual < 0:
                self.vida_actual = 0

            # Activa la invencibilidad para que no reciba daño múltiple
            self.invencible = True
            self.invencible_timer = self.INVENCIBLE_DURACION

    def start_attack(self):
        if not self.attacking and self.attack_cooldown_timer <= 0:
            self.attacking = True
            self.attack_timer = self.attack_duration
            self.attack_cooldown_timer = self.attack_cooldown
            self.state = "attack"
            self.anim_index = 0

    def get_attack_rect(self):
        """
        Rectángulo de ataque SOLO hacia el frente del jugador.
        Usa self.forma (tu rect) y self.facing_right (dirección).
        """
        # Evita crashear si aún no está inicializado
        if not hasattr(self, "forma") or self.forma is None:
            return pygame.Rect(0, 0, 0, 0)

        # Ajusta a tu gusto (alcance y grosor)
        ATTACK_RANGE = max(100, int(self.image.get_width() * 0.9))  # px hacia adelante
        ATTACK_THICK = max(16, int(self.image.get_height() * 0.55))  # altura del hitbox

        # Altura: centrado en el torso. Si quieres "barrida" al suelo, ver opción abajo.
        top = self.forma.centery - ATTACK_THICK // 2

        if getattr(self, "facing_right", True):
            left = self.forma.right  # hacia la derecha
        else:
            left = self.forma.left - ATTACK_RANGE  # hacia la izquierda

        return pygame.Rect(left, top, ATTACK_RANGE, ATTACK_THICK)

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

        if self.attacking:
            return

        if self.en_piso:
            self.state = "run" if dx_pixels_per_sec != 0 else "idle"

    def saltar(self, forzado: bool = False):
        if self.en_piso or forzado:
            self.vel_y = constantes.SALTO_VEL
            self.en_piso = False
            self.state = "jump"
            self.anim_index = 0.0

    def aplicar_gravedad(self, dt: float):
        self.vel_y += constantes.GRAVEDAD * dt

    def actualizar(self, dt):

        # ... tu gravedad/movimiento ...
        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer -= dt
        if self.attacking:
            self.attack_timer -= dt
            if self.attack_timer <= 0:
                self.attacking = False
                self.state = "idle"

    def animar(self, dt: float):
        if self.state == "idle":
            self.anim_index += self.idle_fps * dt
            if self.anim_index >= len(self.frames_idle):
                self.anim_index = 0.0
            frame = self.frames_idle[int(self.anim_index)]

        elif self.state == "attack":
            self.anim_index += 8 * dt
            idx = min(int(self.anim_index), len(self.frames_attack) - 1)
            frame = self.frames_attack[idx]

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
            self.morir()  # o cualquier lógica de muerte/reinicio