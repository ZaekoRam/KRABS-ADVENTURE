import pygame
from pygame.examples.cursors import image

import constantes

class Personaje():
    def __init__(self, x, y, image):
        self.image = image
        self.forma= pygame.Rect(0,0,constantes.ANCHO_PERSONAJE, constantes.ALTO_PERSONAJE)
        self.vel_y = 0.0
        self.en_piso = False
        self.forma.center=(x,y)

    def dibujar(self, interfaz):
        interfaz.blit(self.image, self.forma)
        pygame.draw.rect(interfaz, constantes.COLOR_PERSONAJE,self.forma)

    def movimiento(self, delta_x,  _delta_y_ignorado=0):
        self.forma.x += int(delta_x)

    def saltar(self, forzado=False):
        if self.en_piso or forzado:
            self.vel_y = constantes.SALTO_VEL
            self.en_piso = False

    def actualizar(self, dt):
        self.vel_y += constantes.GRAVEDAD * dt
        self.forma.y += int(self.vel_y * dt)

        suelo_top = constantes.ALTO_VENTANA - constantes.ALTURA_SUELO
        if self.forma.bottom >= suelo_top:
            self.forma.bottom = suelo_top
            self.vel_y = 0
            self.en_piso = True
