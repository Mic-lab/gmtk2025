import pygame
import colorsys
from copy import deepcopy
from .font import FONTS
from . import sfx
from .config import COLORS

class Button:

    presets = {
        'basic': {
            'colors': {'border': [91, 77, 76], 
                       'fill': [151, 134, 125], 
                       'text': [240, 240, 240] }
        },
        'red': {
            'colors': {'border': COLORS['black'], 
                       'fill': [162, 38, 61], 
                       'text': [240, 240, 240] }
        },
        'yellow': {
            'colors': {'border': COLORS['black'], 
                       'fill': COLORS['green2'], 
                       'text': [240, 240, 240] }
        },
        'purple': {
            'colors': {'fill': COLORS['purple'], 
                       'border': COLORS['black'], 
                       'text': [240, 240, 240] }
        },
        'wait': {
            'colors': {'fill': COLORS['blue'], 
                       'border': COLORS['black'], 
                       'text': [240, 240, 240] }
        },
    }
    
    def __init__(self, rect: pygame.Rect, text, preset, disabled=False):
        self.rect = rect
        self.text = text
        self.preset = preset
        self.hovered = False
        self.clicked = False
        self.released = False
        self.disabled = disabled
        self.generate_surf()

    @property
    def state(self):
        if self.clicked: s = 2
        elif self.hovered: s = 1
        else: s = 0
        return s
        
    @property
    def colors(self):
        base_colors = deepcopy(self.presets[self.preset]['colors'])
        if self.disabled:
            h, s, v = self.rgb_to_hsv(base_colors['fill'])
            # v *= 0.5
            s *= 0.5
            base_colors['fill'] = self.hsv_to_rgb((h, s, v))

        if not self.hovered:
            return base_colors
        else:
            if self.clicked:
                change = 2
            else:
                change = 1

            modes = base_colors

            for key, color in modes.items():    
                color = self.rgb_to_hsv(color)
                color[0] += change * 0.04
                color[1] += change * 0.06
                color[2] += change * 0.08

                if color[2] > 1:
                    color[2] = 1
                if color[1] > 1:
                    color[1] = 1
                color[0] = color[0] % 1
                color = self.hsv_to_rgb(color)
                modes[key] = color
            return modes

    def generate_surf(self):
        self.surf = pygame.Surface(self.rect.size)
        self.surf.set_colorkey((0, 0, 0))
        print(f'{self.rect=}')
        rect = pygame.Rect(0, 0, *self.rect.size)

        if self.preset in {'basic',}:
            pygame.draw.rect(self.surf, self.colors['border'], rect, border_radius=2)
            x, y, w, h = rect
            x += 1
            y += 1
            w -= 2
            h -= 3
            pygame.draw.rect(self.surf, self.colors['fill'], (x, y, w, h), border_radius=2)
            # pygame.draw.aaline(self.surf, self.colors['text'], (x, y), (x, y + h - 2))
            # pygame.draw.aaline(self.surf, self.colors['text'], (x, y), (x + w - 1, y))
            text_img = FONTS[self.presets[self.preset].get('font', 'basic')].get_surf(self.text, color=self.colors['text'])


        else:
            pygame.draw.rect(self.surf, self.colors['border'], rect)
            x, y, w, h = rect
            x += 1
            y += 1
            w -= 2
            # h -= 3
            h -= 2
            pygame.draw.rect(self.surf, self.colors['fill'], (x, y, w, h), border_radius=1)
            # pygame.draw.aaline(self.surf, self.colors['text'], (x, y), (x, y + h - 2))
            # pygame.draw.aaline(self.surf, self.colors['text'], (x, y), (x + w - 1, y))
            
            if not self.locked:
                for i in range(3):
                    pygame.draw.aaline(self.surf, COLORS['black'], (x+2+i*2, y+2), (x+2+i*2, h-2))
            text_img = FONTS[self.presets[self.preset].get('font', 'basic')].get_surf(self.text, color=self.colors['text'])


        self.surf.blit(text_img, (rect.centerx - text_img.get_width()*0.5,
                             rect.centery - text_img.get_height()*0.5 - 1))
        
    def update(self, inputs, select_sound='select.wav', click_sound='click.wav', hovered=None):
        old_state = self.state

        self.clicked = False
        if self.rect.collidepoint(inputs.get('mouse pos')):
            if not self.hovered:
                # sfx.sounds[select_sound].play()
                pass
            self.hovered = True
            if inputs['pressed'].get('mouse1'):
                self.clicked = True
                # sfx.sounds[click_sound].play()
        else:
            self.hovered = False

        if hovered is not None:
            self.hovered = hovered

        if self.state != old_state:
            self.generate_surf()
                
    def render(self, surf):
        surf.blit(self.surf, self.rect.topleft)
    
    @staticmethod
    def rgb_to_hsv(rgb):
        small_rgb = [i/255 for i in rgb]
        return list(colorsys.rgb_to_hsv(*small_rgb))
    
    @staticmethod
    def hsv_to_rgb(hsv):
        hsv = list(colorsys.hsv_to_rgb(*hsv))
        return [i*255 for i in hsv]
