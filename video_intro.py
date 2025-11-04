# video_intro.py
import pygame
from pathlib import Path

def play_intro_or_skip(lang: str, screen, clock):
    """
    lang: "es" o "en"
    Si ffpyplayer no está o el archivo no existe, simplemente regresa (sin video).
    Permite saltar con tecla o clic.
    """
    try:
        from ffpyplayer.player import MediaPlayer
    except Exception:
        return  # ffpyplayer no instalado

    video_path = Path(__file__).resolve().parent / "assets" / "video" / ( "intro_es.mp4" if lang == "es" else "intro_en.mp4" )
    if not video_path.exists():
        return

    player = MediaPlayer(str(video_path), ff_opts={"paused": False, "out_fmt": "rgb24"})
    pygame.event.clear()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                try: player.close_player()
                except: pass
                pygame.quit()
                raise SystemExit
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                running = False

        frame, val = player.get_frame()
        if val == 'eof':
            break
        if frame is not None:
            img, t = frame
            w, h = img.get_size()
            surf = pygame.image.frombuffer(img.to_bytearray()[0], (w, h), "RGB")
            sw, sh = screen.get_size()
            screen.blit(pygame.transform.smoothscale(surf, (sw, sh)), (0, 0))
            pygame.display.flip()

        clock.tick(60)

    try: player.close_player()
    except: pass
