from .state import State
from ..mgl import shader_handler
from ..import utils
from ..button import Button
from ..font import FONTS
from ..import animation
from ..entity import Entity, PhysicsEntity
from ..timer import Timer
from ..particle import Particle, ParticleGenerator
from .. import sfx
import pygame

class Menu(State):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.surf = animation.Animation.img_db['test']

        rects = [pygame.Rect(30, 30+i*30, 80, 20) for i in range(4)]
        self.buttons = {
            'game': Button(rects[0], 'harloo', 'basic'),
            'music 1': Button(rects[1], 'music 1', 'basic'),
            'music 2': Button(rects[2], 'music 2', 'basic'),
            'stop': Button(rects[3], 'stop', 'basic'),
        }

        self.entity = PhysicsEntity(pos=(120, 30), name='side', action='idle')
        self.e_speed = 1.5
        self.timer = None
        self.particle_gens = [ParticleGenerator.from_template((200, 200), 'angle test'),
                              ParticleGenerator.from_template((300, 200), 'color test')]

    def sub_update(self):

        if self.timer:
            if self.timer.done:
                self.timer = None
            else:
                self.timer.update()

        if self.handler.inputs['pressed'].get('mouse3'):
            self.timer = Timer(60)

        self.handler.canvas.fill((20, 20, 20))
        self.handler.canvas.blit(self.surf, self.handler.inputs['mouse pos'])

        if self.handler.inputs['pressed'].get('mouse1'):
            self.particle_gens.append(ParticleGenerator.from_template(self.handler.inputs['mouse pos'], 'smoke'))

        self.particle_gens = ParticleGenerator.update_generators(self.particle_gens)
        for particle_gen in self.particle_gens:
            particle_gen.render(self.handler.canvas)

        self.handler.canvas.set_at(self.handler.inputs['mouse pos'], (255, 0, 0))

        # Update Buttons
        for key, btn in self.buttons.items():
            btn.update(self.handler.inputs)
            btn.render(self.handler.canvas)

            if btn.clicked:
                if key == 'game':
                    self.handler.transition_to(self.handler.states.Game)
                elif key == 'music 1':
                    sfx.play_music('song_1.wav', -1)
                elif key == 'music 2':
                    sfx.play_music('song_2.wav')
                elif key == 'stop':
                    pygame.mixer.music.fadeout(1000)

        self.entity.vel = [0, 0]
        if self.handler.inputs['held'].get('a'):
            self.entity.vel[0] -= self.e_speed
            self.entity.animation.flip[0] = True
        elif self.handler.inputs['held'].get('d'):
            self.entity.vel[0] += self.e_speed
            self.entity.animation.flip[0] = False
        if self.handler.inputs['held'].get('w'):
            self.entity.vel[1] -= self.e_speed
        elif self.handler.inputs['held'].get('s'):
            self.entity.vel[1] += self.e_speed

        if any(self.entity.vel):
            self.entity.animation.set_action('run')
        else:
            self.entity.animation.set_action('idle')

        self.entity.update([btn.rect for btn in self.buttons.values()])
        self.entity.render(self.handler.canvas)

        text = [f'{round(self.handler.clock.get_fps())} fps',
                f'vel = {self.entity.vel}',
                # pprint.pformat(Particle.cache)
                ]
        self.handler.canvas.blit(FONTS['basic'].get_surf('\n'.join(text)), (0, 0))

        # shader_handler.vars['shakeTimer'] = -1 if not self.timer else self.timer.ratio ** 2
        shader_handler.vars['caTimer'] = -1 if not self.timer else self.timer.ratio ** 2
