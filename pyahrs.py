#!/usr/bin/env python

import os, sys, random
import pygame

def display_init():
    # pylint: disable=no-member
    disp_no = os.getenv('DISPLAY')
    if disp_no:
    #if False:
        #print "I'm running under X display = {0}".format(disp_no)
        size = 320, 240
        screen = pygame.display.set_mode(size)
    else:
        drivers = ['directfb', 'fbcon', 'svgalib']
        found = False
        for driver in drivers:
            if not os.getenv('SDL_VIDEODRIVER'):
                os.putenv('SDL_VIDEODRIVER', driver)

            try:
                pygame.display.init()
            except pygame.error:
                print(f"Driver: {driver} failed.")
                continue

            found = True
            break

        if not found:
            raise Exception('No suitable video driver found!')

        size = pygame.display.Info().current_w, pygame.display.Info().current_h
        screen = pygame.display.set_mode(size, pygame.FULLSCREEN)

    return screen, size

def main():
    screen, screen_size = display_init()
    width, height = screen_size

    _BLACK =   (  0,   0,   0)
    _WHITE =   (255, 255, 255)
    _BLUE =    (  0,   0, 255)
    _GREEN =   (  0, 255,   0)
    _RED =     (255,   0,   0)
    _GROUND =  ( 84,  53,  10)
    _SKY =     (  9,  79, 252)

    miniature_airplane = {'color': _WHITE,
                          'coords': [[width/6*2,  height/2],
                                     [width/2-10, height/2],
                                     [width / 2,  height/2+20],
                                     [width/2+10, height/2],
                                     [width/6*4,  height/2]],
                          'width': 2}

    static_ahrs_bkgnd = pygame.transform.smoothscale(pygame.image.load("ahrsbkgnd.png").convert(),
                                                     (width*3, height*3))

    roll = 0.0
    pitch = 0.0

    done = False
    clock = pygame.time.Clock()

    while not done:
        # pylint: disable=no-member
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True

        print(f"Roll:  {roll:.1f}")
        print(f"Pitch: {pitch:.1f}")
        print("")

        pitch_offset = height / 90 * pitch

        ahrs = static_ahrs_bkgnd.copy()

        ahrs.scroll(dy=int(pitch_offset))

        ahrs = pygame.transform.rotate(ahrs, roll)

        top_left = (-(ahrs.get_width() - width)/2, -(ahrs.get_height() - height)/2)
        screen.blit(ahrs, top_left)

        for l in [miniature_airplane]:
            pygame.draw.lines(screen, l['color'], False, l['coords'], l['width'])

        pygame.display.flip()

        roll = roll + random.normalvariate(0, 0.5)
        pitch = pitch + random.normalvariate(0, 0.1)
    # pylint: disable=no-member
    pygame.quit()

if __name__ == '__main__':
    sys.exit(main())

# vi: modeline tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python
