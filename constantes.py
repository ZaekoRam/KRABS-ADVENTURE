ANCHO_VENTANA = 800
ALTO_VENTANA = 600
GRAVEDAD = 1400.0      # px/s^2
SALTO_VEL = -750.0     # px/s   (negativo = arriba)
ALTURA_SUELO = -70     # alto del suelo
ALTO_PERSONAJE = .5
ANCHO_PERSONAJE = .5
ALTO_IMAGEN = 2
ANCHO_IMAGEN = 2
COLOR_PERSONAJE = (255,255,0)
JUMP_REPEAT_EVERY = 0.25  # segundos entre saltos mientras se mantiene
FPS = 60
VELOCIDAD = 300
# --- Muerte / vidas / tiempo ---
VIDAS_INICIALES = 4              # cuántas vidas tiene el jugador
TIEMPO_NIVEL1    = 100             # segundos (si no quieres timer, comenta esta línea)

# Impulso hacia arriba al iniciar la animación de muerte (estilo Mario)
# Usa tu SALTO_VEL como base (negativo = hacia arriba)
DEATH_JUMP_VEL = max(-700, int(SALTO_VEL * 1.1))
