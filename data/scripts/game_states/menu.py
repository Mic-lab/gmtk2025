from data.scripts import config
from data.scripts.config import CANVAS_SIZE
from .state import State
from .game import Game
from ..mgl import shader_handler
from ..import utils
from ..button import Button
from ..font import FONTS
from ..import animation
from ..entity import Entity, PhysicsEntity
from ..timer import Timer
from ..particle import Particle, ParticleGenerator
from .. import sfx
from ..animation import Animation
from ..sfx import sounds
import pygame
from data.scripts import mgl

class Menu(State):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)




        CANVAS_SIZE = config.CANVAS_SIZE
        w = 110
        h = 18
        rects = [pygame.Rect(CANVAS_SIZE[0]*0.5 - w*0.5, 150+i*20, w, h) for i in range(5)]
        s_i = 2
        r = rects[s_i].copy()
        r.x += 120
        r.w -= 50

        self.scale = config.scale


        # rects = [pygame.Rect(30, 30+i*30, 80, 20) for i in range(4)]
        self.buttons = {
            'play': Button(rects[0], f'Play', 'basic'),
            'scale': Button(rects[s_i], f'Game Scale ({self.scale}x)', 'basic'),
            'apply': Button(r, f'Apply', 'basic'),
            # 'fullscreen': Button(rects[1], f'Enable fullscreen', 'basic'),
            # 'crt': Button(rects[3], f'Toggle scanlines', 'basic'),
        }

    def sub_update(self):
        # self.handler.canvas.fill((20, 20, 20))
        self.handler.canvas.blit(Animation.img_db['menu'], (0, 0))

        # self.handler.canvas.set_at(self.handler.inputs['mouse pos'], (255, 0, 0))

        # Update Buttons
        for key, btn in self.buttons.items():
            btn.update(self.handler.inputs)
            btn.render(self.handler.canvas)

            if btn.clicked:
                if key == 'scale':

                    self.scale = (self.scale + 1) % 6
                    if self.scale == 0: self.scale = 1
                    btn.text = f'Game Scale ({self.scale}x)'

                elif key == 'apply':
                    config.scale = self.scale
                    SCREEN_SIZE = config.scale*CANVAS_SIZE[0], config.scale*CANVAS_SIZE[1]
                    mgl.screen = pygame.display.set_mode(SCREEN_SIZE,  pygame.OPENGL | pygame.DOUBLEBUF)
                    shader_handler.ctx.viewport = (0, 0, SCREEN_SIZE[0], SCREEN_SIZE[1])

                elif key == 'crt':
                    shader_handler.vars['crt'] = not shader_handler.vars['crt']

                elif key == 'play':
                    self.handler.transition_to(self.handler.states.Game)


        text = [f'{round(self.handler.clock.get_fps())} fps',
                # pprint.pformat(Particle.cache)
                ]
        self.handler.canvas.blit(FONTS['basic'].get_surf('\n'.join(text)), (0, 0))

