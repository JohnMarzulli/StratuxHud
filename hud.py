#!/usr/bin/env python

import math, os, sys, random
import argparse, pygame

class Vehicle(object):
    # pylint: disable=no-member
    def __init__(self, data_source="random", network_source=None):
        self.data_source = data_source
        self.network_source = network_source
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        self.alt = 0
        self.airspeed = 0

        if self.data_source == "network":
            if not self.network_source:
                raise TypeError

            import requests
            self.network_source['requests_session'] = requests.Session()

    def get_orientation(self):
        self.update_orientation()
        return {'roll':     self.roll,
                'pitch':    self.pitch,
                'yaw':      self.yaw,
                'alt':      self.alt,
                'airspeed': self.airspeed}

    def set_orientation(self, roll=None, pitch=None, yaw=None, alt=None, airspeed=None):
        if roll != None:
            self.roll = roll

        if pitch != None:
            self.pitch = pitch

        if yaw != None:
            self.yaw = yaw

        if alt != None:
            self.alt = alt

        if airspeed != None:
            self.airspeed = airspeed

    def update_orientation(self):
        if self.data_source == "random":
            r = self.roll + random.normalvariate(0, 0.5)
            p = self.pitch + random.normalvariate(0, 0.5)
            self.set_orientation(roll=r, pitch=p)

        elif self.data_source == "manual":
            r = 0 #float(raw_input('Roll? '))
            p = 0 #float(raw_input('Pitch? '))
            self.set_orientation(roll=r, pitch=p)

        elif self.data_source == "network":
            url = "http://{0}/getSituation".format(self.network_source['host'])
            r = self.network_source['requests_session'].get(url, timeout=2)
            self.set_orientation(roll=r.json()['AHRSRoll'], pitch=r.json()['AHRSPitch'])

        else:
            raise ValueError

def debug_print(debug, string, level=1):
    if not debug:
        return
    if debug >= level:
        print(string)

def display_init(debug):
    # pylint: disable=no-member
    pygame.init()
    disp_no = os.getenv('DISPLAY')
    if disp_no:
    #if False:
        debug_print(debug, "I'm running under X display = {0}".format(disp_no))
        size = 640, 480
        #size = 320, 240
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
                debug_print(debug, 'Driver: {0} failed.'.format(driver))
                continue

            found = True
            break

        if not found:
            raise Exception('No suitable video driver found!')

        size = pygame.display.Info().current_w, pygame.display.Info().current_h
        screen = pygame.display.set_mode(size, pygame.FULLSCREEN)

    return screen, size

def get_line_coords(screen_width, screen_height, ahrs_center, pitch=0, roll=0, deg_ref=0):
    if deg_ref == 0:
        length = screen_width*.6
    elif (deg_ref%10) == 0:
        length = screen_width*.4
    elif (deg_ref%5) == 0:
        length = screen_width*.2

    ahrs_center_x, ahrs_center_y = ahrs_center
    px_per_deg_y = screen_height / 60
    pitch_offset = px_per_deg_y * (-pitch + deg_ref)

    center_x = ahrs_center_x - (pitch_offset * math.cos(math.radians(90 - roll)))
    center_y = ahrs_center_y - (pitch_offset * math.sin(math.radians(90 - roll)))

    x_len = length * math.cos(math.radians(roll))
    y_len = length * math.sin(math.radians(roll))

    start_x = center_x - (x_len / 2)
    end_x = center_x + (x_len / 2)
    start_y = center_y + (y_len / 2)
    end_y = center_y - (y_len / 2)

    return [[start_x, start_y], [end_x, end_y]]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--datasource", help="Where the orientation information comes from (default: %(default)s)",
                        choices=["random", "network", "manual"], default="random")
    parser.add_argument("-n", "--networkhost", help="The name or IP address of the network host used as the data source")
    parser.add_argument("-f", "--maxframerate", help="The maximum number of frames per second attempted (default: %(default)s)", type=int, default=20)
    parser.add_argument("-D", "--debug", help="Enable verbose output for debugging purposes", action="count")
    args = parser.parse_args()

    if args.datasource == "network" and args.networkhost is None:
        parser.error("--networkhost is required when --datasource is set to 'network'")

    screen, screen_size = display_init(args.debug)
    width, height = screen_size
    pygame.mouse.set_visible(False)

    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)

    font = pygame.font.SysFont(None, int(height/20))

    v = Vehicle(data_source=args.datasource, network_source={'host': args.networkhost})
    # pylint: disable=too-many-function-args
    ahrs_bg = pygame.Surface((width*2, height*2))
    ahrs = ahrs_bg
    ahrs_bg_width = ahrs_bg.get_width()
    ahrs_bg_height = ahrs_bg.get_height()
    ahrs_bg_center = (ahrs_bg_width/2, ahrs_bg_height/2)

    done = False
    clock = pygame.time.Clock()

    while not done:
        # pylint: disable=no-member
        clock.tick(args.maxframerate)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True

        o = v.get_orientation()
        roll = o['roll']
        pitch = o['pitch']

        debug_print(args.debug, "Roll:  {:.1f}".format(roll))
        debug_print(args.debug, "Pitch: {:.1f}".format(pitch))
        debug_print(args.debug, "")

        ahrs.fill(BLACK)

        # range isn't inclusive of the stop value, so if stop is 60 then there's no line make
        # for 60
        for l in range(-60, 61, 5):
            line_coords = get_line_coords(width, height, ahrs_bg_center, pitch=pitch, roll=roll, deg_ref=l)

            if abs(l)>45:
                if l%5 == 0 and l%10 != 0:
                    continue

            debug_print(args.debug, "Deg: {0}".format(l), 2)
            debug_print(args.debug, "Line Coords: {0}".format(line_coords), 2)
            debug_print(args.debug, "", 2)
            pygame.draw.lines(ahrs_bg, WHITE, False, line_coords, 2)

            if l != 0 and l%10 == 0:
                text = font.render(str(l), False, WHITE)
                text_width, text_height = text.get_size()
                left = int(line_coords[0][0]) - (text_width + int(width/100))
                top = int(line_coords[0][1]) - text_height / 2
                ahrs_bg.blit(text, (left, top))

        top_left = (-(ahrs.get_width() - width)/2, -(ahrs.get_height() - height)/2)
        screen.blit(ahrs, top_left)

        pygame.draw.lines(screen, WHITE, False, [[0, height/2], [10, height/2]], 2)
        pygame.draw.lines(screen, WHITE, False, [[width-10, height/2], [width, height/2]], 2)
        pygame.display.flip()
    #pylint: disable=no-member
    pygame.quit()

if __name__ == '__main__':
    sys.exit(main())

# vi: modeline tabstop=8 expandtab shiftwidth=4 softtabstop=4 syntax=python