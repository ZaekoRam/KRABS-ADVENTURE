import pygame
import constantes

class Enemigo(pygame.sprite.Sprite):
    def __init__(self, x, y, velocidad=2, escala=2):  # <-- Añade el parámetro escala
        super().__init__()

        # Carga la imagen original
        original_image = pygame.image.load("assets/images/enemigos/enemigo1.png").convert_alpha()

        # Calcula el nuevo tamaño
        nuevo_ancho = original_image.get_width() * escala
        nuevo_alto = original_image.get_height() * escala

        # Escala la imagen y la asigna a self.image
        self.image = pygame.transform.scale(original_image, (nuevo_ancho, nuevo_alto))

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
        # 1. LÓGICA DE DECISIÓN: ¿Debería saltar?
        # -----------------------------------------
        # Primero, actualiza el temporizador.
        if self.salto_timer > 0:
            self.salto_timer -= dt

        # La condición `self.vel_y == 0` es una buena señal de que está en el suelo.
        # Si está en el suelo y el timer terminó, toma la decisión de saltar.
        if self.vel_y == 0 and self.salto_timer <= 0:  # Cambia la dirección para el próximo salto
            self.vel_y = self.fuerza_salto  # Aplica la fuerza de salto vertical
            self.vel_x = self.velocidad_movimiento  # ¡ACTIVA la velocidad horizontal!
            self.salto_timer = self.INTERVALO_SALTO  # Reinicia el temporizador

        # 2. MOVIMIENTO Y COLISIÓN EN EJE X (Horizontal)
        # ------------------------------------------------
        # Mueve al enemigo horizontalmente.
        self.rect.x += self.vel_x * self.direccion * dt

        # Revisa colisiones SOLO para el eje X.
        for rect in plataformas:
            if self.rect.colliderect(rect):
                # Si choca mientras se mueve a la derecha...
                if self.vel_x * self.direccion > 0:
                    self.rect.right = rect.left
                    self.direccion *= -1
                # Si choca mientras se mueve a la izquierda...
                elif self.vel_x * self.direccion < 0:
                    self.rect.left = rect.right
                    self.direccion *= -1  # <-- ¡CORREGIDO! Y también AQ

        # 3. MOVIMIENTO Y COLISIÓN EN EJE Y (Vertical)
        # ----------------------------------------------
        # Aplica la gravedad y mueve al enemigo verticalmente.
        self.vel_y += constantes.GRAVEDAD * dt
        self.rect.y += self.vel_y * dt

        for rect in plataformas:
            if self.rect.colliderect(rect):
                if self.vel_y > 0: # Cayendo
                    self.rect.bottom = rect.top
                    self.vel_y = 0
                    self.vel_x = 0 # Detenerse al aterrizar
                elif self.vel_y < 0: # Chocando con un techo
                    self.rect.top = rect.bottom
                    self.vel_y = 0


        # Animaciones, IA, etc. pueden ir aquí

    def tocar_jugador(self, jugador):
        return self.rect.colliderect(jugador.forma)