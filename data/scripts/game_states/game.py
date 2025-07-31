from copy import copy
import pygame
from .state import State
from ..mgl import shader_handler
from ..button import Button
from ..entity import Entity, PhysicsEntity
from ..timer import Timer
from ..particle import Particle, ParticleGenerator
from ..font import FONTS
from .. import sfx
from ..config import COLORS
from ..animation import Animation
from data.scripts import config
from pygame import Vector2

# WAVES = (
#     ()
# )

class Projectile(PhysicsEntity):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_img = super().img
        angle = self.vel.angle_to(Vector2(1, 0))
        self._img = pygame.transform.rotate(base_img, angle)
        self._real_pos = self._real_pos - 0.5*Vector2(self._img.get_size())

    @property
    def img(self):
        return self._img

class Bar:

    STYLES = {
        'hp': {
            'color': (255, 0, 68),
        }
    }

    def __init__(self, rect: pygame.Rect, value, max_val, style, label='') -> None:
        self.rect = rect
        self.value = value
        self.max_val = max_val
        self.style = style
        self.label = label
        self.generate_surf()

    def generate_surf(self):
        s = pygame.Surface(self.rect.size)
        # s.fill(COLORS['black'])
        s.set_colorkey((0, 0, 0))

        r = self.rect.copy()
        r.topleft = (0, 0)
        pygame.draw.rect(s, COLORS['black'], r, border_radius=2)
        fill_rect = r.copy()
        fill_rect.x += 2
        fill_rect.w -= 4
        fill_rect.y += 2
        fill_rect.h -= 4

        fill_rect.w *= self.value / self.max_val

        pygame.draw.rect(s, COLORS['red'], fill_rect, border_radius=2)
        txt_img = FONTS['basic'].get_surf(f'{self.value}/{self.max_val} {self.label}')
        s.blit(txt_img, (r.centerx - txt_img.get_width()*0.5, r.centery - txt_img.get_height()*0.5))
        self.surf = s

    def change_val(self, change):
        self.value += change
        if self.value > self.max_val:
            self.value = self.max_val
        elif self.value < 0:
            self.value = 0
        self.generate_surf()

    def render(self, canvas):
        canvas.blit(self.surf, self.rect.topleft)

class Block(Button):
    def __init__(self, duration, id, *args, **kwargs):
        self.id=id
        self.locked = False
        self.duration = duration
        args=list(args)
        print(args)
        args[1] += f' <{round(self.duration/60, 2)}>'
        super().__init__(*args, **kwargs)

    @property
    def state(self):
        if self.locked:
            return 0
        else:
            return super().state

class Game(State):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        bg_size = 176
        wall_width = 30

        self.walls = [pygame.Rect(bg_size-30, -wall_width, 30, config.SCREEN_SIZE[1]),
                      pygame.Rect(config.CANVAS_SIZE[0], 0, 30, config.SCREEN_SIZE[1]),
                      pygame.Rect(bg_size-wall_width, -wall_width, config.CANVAS_SIZE[0], 30),
                      pygame.Rect(0, config.CANVAS_SIZE[1], config.CANVAS_SIZE[0], 30)]


        y = 70
        # rects = [pygame.Rect(120, y+i*20, 120, 16) for i in range(20)]
        rects = [pygame.Rect(10, y+120+i*20, 120, 16) for i in range(20)]

        self.entity = PhysicsEntity(pos=(200, 50), name='side', action='idle', max_vel=1.5)
        self.e_speed = 1.5

        self.enemies = []
        self.enemies.append(
            PhysicsEntity(pos=(200, 200), name='enemy', action='run', max_vel=1)
        )

        self.bars = {
            'hp': Bar(pygame.Rect(10, 10, 100, 15), 50, 100, 'hp', 'HP'),
        }
        self.gold = 0

        self.projectiles=[]
        self.slashes = []
        
        self.loop_duration = 60
        self.particle_gens = [ParticleGenerator.from_template((200, 200), 'angle test'),
                              ParticleGenerator.from_template((300, 200), 'color test')]

        self.loop_block = Entity((10, y), 'loop_block')

        self.snap_positions = [(30, y+19+i*15) for i in range(5)]
        self.slots = [None for i in range(len(self.snap_positions))]
        self.blocks = [
            Block(3, 'hp', rects[0], 'Get 1 HP', 'red', disabled=True),
            Block(3, 'projectile', rects[1], 'Projectile', 'purple', disabled=True),
            Block(3, 'slash', rects[2], 'Slash', 'purple', disabled=True),
            Block(3, 'hp', rects[3], 'Get 1 HP', 'red', disabled=True),
            Block(3, 'gold', rects[4], 'Get 1 Gold', 'yellow', disabled=True),
            Block(self.loop_duration, 'wait',
                  pygame.Rect(*self.snap_positions[-1],
                              *rects[0].size), 
                  'Wait 1 sec', preset='wait'),
        ]
        self.block_i = 0
        self.just_switched = True
        # self.timer = Timer(1)

        self.blocks[-1].locked = True
        self.blocks[-1].generate_surf()
        self.slots[-1] = self.blocks[-1]

        self.buttons = {

        }
        self.arrow = Animation.img_db['arrow']

        self.selected_block = None

    def sub_update(self):

        # bg ------------
        self.handler.canvas.fill(COLORS['green3'])
        # pygame.draw.rect(self.handler.canvas, (80, 80, 80), (0, 0, 180, config.SCREEN_SIZE[1]))
        self.handler.canvas.blit(Animation.img_db['scratch_bg'], (0, 0))


        # self.particle_gens = ParticleGenerator.update_generators(self.particle_gens)
        # for particle_gen in self.particle_gens:
        #     particle_gen.render(self.handler.canvas)

        for projectile in self.projectiles:
            projectile.update()
            projectile.render(self.handler.canvas)

        new_slashes = []
        for slash in self.slashes:
            done = slash.update()
            if done:
                continue
            else:
                slash.render(self.handler.canvas)
                new_slashes.append(slash)
        self.slashes = new_slashes

        # Update blocks ------
        # NOTE: only skips 1 frame, not all Nones
        skip = False

        if self.just_switched:
            self.block_i = (self.block_i+1)%5

        block = self.slots[self.block_i]
        while block is None:
            self.block_i = (self.block_i+1)%5
            self.just_switched = True
            block = self.slots[self.block_i]

        if self.just_switched:
            self.just_switched = False
            self.timer = Timer(block.duration)
            if block.id == 'hp':
                self.bars['hp'].change_val(1)
            elif block.id == 'projectile':
                vel= -pygame.Vector2(self.entity.rect.center)+self.handler.inputs['mouse pos']
                vel.scale_to_length(6)
                self.projectiles.append(Projectile(vel=vel, pos=self.entity.rect.center, name='projectile'))
            elif block.id == 'slash':
                # slash_pos = Vector2(self.entity.rect.center) - self.handler.inputs['mouse pos']
                # mouse_dist.scale_to_length(8)
                slash = PhysicsEntity(vel=self.entity.vel.copy(), pos=(0,0), name='slash', action='idle')
                slash.enemies = []

                slash_pos = self.entity.rect.center
                if slash_pos[0] - self.handler.inputs['mouse pos'][0] > 0:
                    coef = -1
                    flip = True
                else:
                    coef = 1
                    flip = False
                slash_pos = (slash_pos[0] + coef*12 - slash.img.get_width()*0.5, slash_pos[1] - slash.img.get_height()*0.5)
                slash._real_pos = slash_pos
                slash.animation.flip = (flip, False)
                
                self.slashes.append(slash)
            elif block.id == 'gold':
                self.gold += 1

        self.timer.update()
        if self.timer.done:
            self.just_switched = True

            


        if self.handler.inputs['released'].get('mouse1'):
            self.selected_block = None

        clicked_blocks = []
        for block in self.blocks:
            if block == self.selected_block:
                block.update(self.handler.inputs, hovered=True)
            else:
                block.update(self.handler.inputs)

            block.render(self.handler.canvas)

            if block.clicked and not block.locked:
                clicked_blocks.append(block)

            old_disabled = block.disabled
            new_disabled = not (block in self.slots)
            block.disabled = new_disabled
            if old_disabled != new_disabled:
                block.generate_surf()


        if clicked_blocks:
            block = clicked_blocks[-1]
            self.selected_block = block
            if self.selected_block in self.slots:
                i = self.slots.index(self.selected_block)
                self.slots[i] = None
                    



        if self.selected_block:
            self.selected_block.rect.midleft = self.handler.inputs.get('mouse pos') - pygame.Vector2(1, 0)
            for i, pos in enumerate(self.snap_positions):
                if self.slots[i] is not None:
                    continue
                if (pygame.Vector2(self.selected_block.rect.topleft) - pos).length() <= 6:
                    self.slots[i] = self.selected_block
                    self.selected_block.rect.topleft = pos
                    self.selected_block = None
                    break



        # Update Buttons
        for key, btn in self.buttons.items():
            btn.update(self.handler.inputs)
            btn.render(self.handler.canvas)

        # Update bars
        for key, bar in self.bars.items():
            bar.render(self.handler.canvas)

        self.handler.canvas.blit(FONTS['basic'].get_surf(f'{self.gold}'), (10, 30))

        # update enemy
        for enemy in self.enemies:
            if enemy.name == 'enemy':
                enemy.vel = -enemy.pos + self.entity.pos
                enemy.animation.flip[0] = enemy.vel[0] < 0

            done = enemy.update(self.walls)
            if done and enemy.animation.action == 'hit':
                enemy.animation.set_action('run')

            for slash in self.slashes:
                if enemy not in slash.enemies and enemy.rect.colliderect(slash.rect):
                    slash.enemies.append(enemy)
                    enemy.animation.set_action('hit')
            enemy.render(self.handler.canvas)

        # Update player
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

        self.entity.update(self.walls)
        self.entity.render(self.handler.canvas)

        # if self.handler.inputs['held'].get('mouse1'):
        #     for wall in self.walls:
        #         pygame.draw.rect(self.handler.canvas, (200, 200, 0), wall)


        # text ----------
        text = [f'{round(self.handler.clock.get_fps())} fps',
                f'mouse pos {self.handler.inputs["mouse pos"]}',
                f'{self.timer=}',
                f'{self.block_i=}',


                ]
        self.handler.canvas.blit(FONTS['basic'].get_surf('\n'.join(text)), (300, 0))


        self.loop_block.update()
        self.loop_block.render(self.handler.canvas)

        self.handler.canvas.blit(self.arrow, (14, self.snap_positions[self.block_i][1]+6))

        # Shader -----
        # shader_handler.vars['caTimer'] = -1 if not self.timer else self.timer.ratio ** 2

        self.first_loop = False
