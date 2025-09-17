import pygame
import constantes
from personaje import Personaje

pygame.init()

ventana = pygame.display.set_mode((constantes.ANCHO_VENTANA, constantes.ALTO_VENTANA))
pygame.display.set_caption("Krab's adventure")

jugador = Personaje(250, 350)

mover_arriba = False
mover_abajo = False
mover_izquierda = False
mover_derecha = False

reloj = pygame.time.Clock()

run = True
while run:
    reloj.tick(constantes.FPS)
    delta_x = 0
    delta_y = 0

    if mover_derecha:
        delta_x = 5
    if mover_izquierda:
        delta_x = -5
    if mover_arriba:
        delta_y = -5
    if mover_abajo:
        delta_y = 5

    # Mover jugador
    jugador.movimiento(delta_x, delta_y)

    # Dibujar
    ventana.fill((0, 0, 0))  # limpiar la pantalla cada frame
    jugador.dibujar(ventana)
    pygame.display.update()

    # Manejo de eventos
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_a:
                mover_izquierda = True
            if event.key == pygame.K_d:
                mover_derecha = True
            if event.key == pygame.K_w:
                mover_arriba = True
            if event.key == pygame.K_s:
                mover_abajo = True

        if event.type == pygame.KEYUP:
            if event.key == pygame.K_a:
                mover_izquierda = False
            if event.key == pygame.K_d:
                mover_derecha = False
            if event.key == pygame.K_w:
                mover_arriba = False
            if event.key == pygame.K_s:
                mover_abajo = False

pygame.quit()
