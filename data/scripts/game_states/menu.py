from .state import State
from ..mgl import shader_handler
from ..import utils
from ..button import Button
from ..font import FONTS
from ..import animation
from .. import sfx
from ..animation import Animation
import pygame

class Menu(State):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        rects = [pygame.Rect(30, 30+i*30, 80, 20) for i in range(4)]
        self.buttons = {
            'game': Button(rects[0], 'Play', 'basic'),
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
                if key == 'game':
                    self.handler.transition_to(self.handler.states.Game)


        text = [f'{round(self.handler.clock.get_fps())} fps',
                # pprint.pformat(Particle.cache)
                ]
        self.handler.canvas.blit(FONTS['basic'].get_surf('\n'.join(text)), (0, 0))

