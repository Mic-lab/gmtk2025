from copy import copy
import math
from random import uniform
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
        self.enemies = []
        self.dead = False

    @property
    def img(self):
        return self._img

class Bar:

    STYLES = {
        'hp': {
            'color': (255, 0, 68),
        },
        'enemy': {
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

        if self.style == 'hp':
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

        elif self.style == 'enemy':
            s.fill(COLORS['black'])
            fill_rect = self.rect.copy()
            fill_rect.topleft=(0,0)
            fill_rect.w *= self.value / self.max_val
            pygame.draw.rect(s, COLORS['red'], fill_rect)

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
        args[1] += f' <{round(self.duration/60, 2)}>'
        super().__init__(*args, **kwargs)

    @property
    def state(self):
        if self.locked:
            return 0
        else:
            return super().state

class Game(State):

    SHOP_SPEED = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.game_over = False

        bg_size = 176
        wall_width = 30

        self.walls = [pygame.Rect(bg_size-30, -wall_width, 30, config.SCREEN_SIZE[1]),
                      pygame.Rect(config.CANVAS_SIZE[0], 0, 30, config.SCREEN_SIZE[1]),
                      pygame.Rect(bg_size-wall_width, -wall_width, config.CANVAS_SIZE[0], 30),
                      pygame.Rect(0, config.CANVAS_SIZE[1], config.CANVAS_SIZE[0], 30)]


        y = 70
        # rects = [pygame.Rect(120, y+i*20, 120, 16) for i in range(20)]

        self.entity = PhysicsEntity(pos=(200, 50), name='side', action='idle', max_vel=1.5)
        self.player = self.entity

        self.entity.invincible = None
        self.e_speed = 1.5

        self.enemies = []
        enemy = PhysicsEntity(pos=(200, 200), name='enemy', action='run', max_vel=1)
        enemy.bar = Bar(pygame.Rect(0, 0, 15, 2), 10, 10, 'enemy')
        enemy.dmg = 10
        self.enemies.append(enemy)

        self.bars = {
            'hp': Bar(pygame.Rect(10, 10, 100, 15), 50, 100, 'hp', 'HP'),
        }
        self.gold = 999

        self.projectiles=[]
        self.slashes = []
        
        self.loop_duration = 60
        self.particle_gens = []
        # self.particle_gens = [ParticleGenerator.from_template((200, 200), 'angle test'),
        #                       ParticleGenerator.from_template((300, 200), 'color test')]

        self.loop_block = Entity((10, y), 'loop_block')

        rects = [pygame.Rect(10, y+120+i*20, 120, 16) for i in range(20)]
        locked_rects = [pygame.Rect(config.CANVAS_SIZE[0], y+120+i*20, 120, 16) for i in range(20)]

        self.snap_positions = [(30, y+19+i*15) for i in range(5)]
        self.slots = [None for i in range(len(self.snap_positions))]
        self.blocks = [
            Block(3, 'hp', rects[0], 'Get 1 HP', 'red', disabled=True),
            Block(3, 'slash', rects[1], 'Slash', 'purple', disabled=True),
            Block(3, 'gold', rects[2], 'Get 1 Gold', 'yellow', disabled=True),

        ]

        self.locked_blocks = [
            Block(3, 'gold', locked_rects[0], 'Get 1 gold', 'yellow', disabled=True),
            Block(3, 'gold', locked_rects[1], 'Get 1 gold', 'yellow', disabled=True),
            Block(3, 'hp', locked_rects[2], 'Get 1 HP', 'red', disabled=True),
            Block(3, 'projectile', locked_rects[3], 'Projectile', 'purple', disabled=True),
            Block(15, 'dash', locked_rects[4], 'Dash', 'blue', disabled=True),
        ]

        self.prices = [15,
                       20,
                       20,
                       20,
                       25]

        self.price_buttons = []
        for i, price in enumerate(self.prices):
            rect = locked_rects[i].copy()
            rect.x += 50
            rect.w = 60
            btn = Button(rect, f'Buy [{price}$]', preset='basic')
            btn.price = price
            self.price_buttons.append(btn)

        for block in self.locked_blocks:
            block.locked = True
            block.generate_surf()
        self.blocks += self.locked_blocks


        wait_block = Block(self.loop_duration, 'wait',
                  pygame.Rect(*self.snap_positions[-1],
                              *rects[0].size), 
                  'Wait 1 sec', preset='wait')

        wait_block.locked = True
        wait_block.generate_surf()

        self.blocks.append(wait_block)


        self.slots[-1] = wait_block
        self.block_i = 0
        self.just_switched = True
        # self.timer = Timer(1)


        for block in self.blocks:
            if block.id == 'slash':
                block.description = 'Horizontal melee attack at the\ndirection of your mouse'
            else:
                block.description = ''

        self.buttons = {

        }
        self.arrow = Animation.img_db['arrow']

        self.selected_block = None

        self.shop = Entity((333, 0), 'shop')

        # self.shop_entrance = (
        #     (280, 0),
        #     (290, 25),
        #     (315, 46),
        #     (350, 70),
        #     (390, 67),
        #     (422, 37),
        #     (432, 10),
        #     (438, 0),
        # )
        self.shop_entrance = []

        center = (364, 0)
        radius = 64
        detail = 16
        surround = 0.2
        for i in range(detail):
            angle = math.pi-surround + (i / (detail-1)) * (math.pi + 2*surround)
            point = radius * Vector2(math.cos(angle), -math.sin(angle))
            point += center
            self.shop_entrance.append(point)

        self.random_points = self.shop_entrance.copy()
        for i in range(len(self.random_points)):
            point = self.random_points[i].copy()

            random_angle = uniform(0, 2*math.pi)
            v = 2*Vector2(math.cos(random_angle), math.sin(random_angle))
            point += v
            v.scale_to_length(0.2)
            point = [point[0], point[1]] + [-v.y, v.x]
            self.random_points[i] = point

        self.mode = 'game'
        self.shop_timer = None
        self.block_hover_timer = 0

    def sub_update(self):

        # bg ------------
        self.handler.canvas.fill(COLORS['green3'])
        # pygame.draw.rect(self.handler.canvas, (80, 80, 80), (0, 0, 180, config.SCREEN_SIZE[1]))
        self.handler.canvas.blit(Animation.img_db['scratch_bg'], (0, 0))


        # self.particle_gens = ParticleGenerator.update_generators(self.particle_gens)

        new_projectiles = []
        for projectile in self.projectiles:
            if projectile.dead:
                particle = ParticleGenerator.TEMPLATES['smoke']['base_particle'].copy()
                particle.vel = projectile.vel * 0.3
                self.particle_gens.append(
                    ParticleGenerator.from_template(projectile.rect.center, 'smoke', base_particle=particle)
                )
                break

            if self.mode == 'game':
                projectile.update()

                for wall in self.walls:
                    if projectile.rect.colliderect(wall):
                        projectile.dead = True

            projectile.render(self.handler.canvas)
            new_projectiles.append(projectile)
        self.projectiles = new_projectiles

        new_slashes = []
        for slash in self.slashes:
            done = False
            if self.mode == 'game':
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
            elif block.id == 'dash':
                self.particle_gens.append(
                    ParticleGenerator.from_template(self.entity.rect.center, 'player')
                )
                self.entity._real_pos += self.entity.vel * 20

        if self.mode == 'game':
            self.timer.update()

        if self.shop_timer:
            if self.shop_timer.done:
                self.shop_timer = None
            else:
                self.shop_timer.update()

        if self.entity.invincible:
            if self.entity.invincible.done:
                self.entity.invincible = None
            else:
                self.entity.invincible.update()



        if self.timer.done:
            self.just_switched = True

            


        if self.handler.inputs['released'].get('mouse1'):
            self.selected_block = None




        # Update Buttons
        for key, btn in self.buttons.items():
            btn.update(self.handler.inputs)
            btn.render(self.handler.canvas)

        # Update bars
        for key, bar in self.bars.items():
            bar.render(self.handler.canvas)

        self.handler.canvas.blit(FONTS['basic'].get_surf(f'{self.gold}'), (10, 30))

        # shop
        # pygame.draw.polygon(self.handler.canvas, COLORS['black'], self.shop_entrance)
        pygame.draw.polygon(self.handler.canvas, COLORS['blue'], [(p[0], p[1]) for p in self.random_points ])
        pygame.draw.polygon(self.handler.canvas, COLORS['black'], [(p[0], p[1]) for p in self.random_points ], width=3)
        self.shop.render(self.handler.canvas)

        # update enemy
        new_enemies = []
        for enemy in self.enemies:
            if enemy.name == 'enemy':
                enemy.vel = -enemy.pos + self.entity.pos
                enemy.animation.flip[0] = enemy.vel[0] < 0

                if self.shop_timer:
                    ratio = self.shop_timer.ratio
                else:
                    ratio = 0
                # enemy._real_pos = Vector2(300+100*ratio, 100)

            done = False
            if self.mode == 'game':
                done = enemy.update(self.walls)

            if done and enemy.animation.action == 'hit':
                enemy.animation.set_action('run')

            for slash in self.slashes:
                if enemy not in slash.enemies and enemy.rect.colliderect(slash.rect):
                    slash.enemies.append(enemy)
                    enemy.animation.set_action('hit')
                    enemy.bar.change_val(-5)

            for projectile in self.projectiles:
                if enemy not in projectile.enemies and enemy.rect.colliderect(projectile.rect):
                    projectile.enemies.append(enemy)
                    enemy.animation.set_action('hit')
                    enemy.bar.change_val(-4)
                    projectile.dead = True

            if enemy.rect.colliderect(self.entity.rect) and not self.entity.invincible and not self.game_over:
                self.entity.invincible = Timer(60)
                self.bars['hp'].change_val(-enemy.dmg)

            enemy.render(self.handler.canvas)
            enemy.bar.rect.midbottom = enemy.rect.midtop
            enemy.bar.render(self.handler.canvas)
            
            if enemy.bar.value > 0:
                new_enemies.append(enemy)
            else:
                self.particle_gens.append(
                    ParticleGenerator.from_template(enemy.rect.center, 'big')
                )
                self.particle_gens.append(
                    ParticleGenerator.from_template(enemy.rect.center, 'smoke')
                )
                self.particle_gens.append(
                    ParticleGenerator.from_template(enemy.rect.center, 'shock')
                )
                # particle stuff here TODO

        self.enemies = new_enemies

        # pygame.draw.polygon(self.handler.canvas, COLORS['blue1'], self.shop_entrance)
        for i, point in enumerate(self.random_points):
            pos = point[0], point[1]
            vel = point[2], point[3]
            difference = self.shop_entrance[i] - Vector2(pos)
            if difference.length() == 0: difference = Vector2(1, 0)
            difference.scale_to_length(0.01)
            vel += difference
            pos = Vector2(pos) + vel
            self.random_points[i] = (*pos, *vel)


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

        if self.entity.rect.colliderect(self.shop.rect):
            # self.entity._real_pos = Vector2(340, 80)
            if self.mode == 'game':
                self.particle_gens.append(ParticleGenerator.from_template(self.entity.rect.center, 'shards'))
                if self.shop_timer:
                    offset = self.SHOP_SPEED - self.shop_timer.frame
                    self.shop_timer = Timer(self.SHOP_SPEED)
                    self.shop_timer.frame = offset
                else:
                    self.shop_timer = Timer(self.SHOP_SPEED)
            self.mode = 'shop'
        else:
            if self.mode == 'shop':
                if self.shop_timer:
                    offset = self.SHOP_SPEED - self.shop_timer.frame
                    self.shop_timer = Timer(self.SHOP_SPEED)
                    self.shop_timer.frame = offset
                else:
                    self.shop_timer = Timer(self.SHOP_SPEED)

            self.mode = 'game'

        # if self.handler.inputs['held'].get('mouse1'):
        #     for wall in self.walls:
        #         pygame.draw.rect(self.handler.canvas, (200, 200, 0), wall)

        self.particle_gens = ParticleGenerator.update_generators(self.particle_gens)
        for particle_gen in self.particle_gens:
            particle_gen.render(self.handler.canvas)

        # if self.mode == 'shop':
        self.render_shop()


        # block ---------------------------

        clicked_blocks = []
        hovered_block = None

        for block in self.blocks:
            if block == self.selected_block:
                block.update(self.handler.inputs, hovered=True)
            else:
                block.update(self.handler.inputs)

            if block.hovered:
                hovered_block = block
                self.unreset_hovered_block = block


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

        if hovered_block and hovered_block.description:
            self.block_hover_timer += 1
            if self.block_hover_timer > 20:
                self.block_hover_timer = 20
        else:
            self.block_hover_timer -= 1
            if self.block_hover_timer < 0:
                self.block_hover_timer = 0

        self.alpha = self.block_hover_timer/20*255

        print(f'{self.alpha=}')

        if self.alpha != 0:

            if self.unreset_hovered_block:
                description = self.unreset_hovered_block.description
                description = f'- {self.unreset_hovered_block.text} -\n' + description
            else:
                description=''
            # description = self.unreset_hovered_block.description

            if description:
                s = pygame.Surface((200, 80))
                s.fill((0, 0, 0, 100))
                s.set_alpha(self.alpha*0.7)
                p = Vector2(295, 15)
                self.handler.canvas.blit(s, p)

                text = FONTS['basic'].get_surf(description)
                text.set_alpha(self.alpha)
                self.handler.canvas.blit(text, p+(5, 5))


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
        # -----------------------------------







        # text ----------
        text = [f'{round(self.handler.clock.get_fps())} fps',
                f'mouse pos {self.handler.inputs["mouse pos"]}',
                f'{self.timer=}',
                f'{self.block_i=}',


                ]
        self.handler.canvas.blit(FONTS['basic'].get_surf('\n'.join(text)), (150, 200))


        self.loop_block.update()
        self.loop_block.render(self.handler.canvas)

        self.handler.canvas.blit(self.arrow, (14, self.snap_positions[self.block_i][1]+6))





        if self.bars['hp'].value == 0:
            self.game_over = True
            self.handler.transition_to(self.handler.states.Menu)
            self.entity.invincible = None

        # Shader -----
        shader_handler.vars['caTimer'] = 1 if self.mode == 'shop' else -1
        shader_handler.vars['shakeTimer'] = -1 if self.entity.invincible is None else self.entity.invincible.ratio

        self.first_loop = False

    def render_shop(self):
        x_displacement = Animation.img_db['shop_bg'].get_width()

        if self.shop_timer is None:
            if self.mode == 'game':
                return
            ratio = 1


        else:
            ratio = (self.shop_timer.ratio )

            if self.mode == 'game':
                ratio = 1-ratio

            ratio = ratio ** 0.4


        pos = (config.CANVAS_SIZE[0] - x_displacement*ratio, 100)



        for block in self.locked_blocks:
            if block is None: continue
            block.rect.x = pos[0] + 5


        

        shop_bg = Animation.img_db['shop_bg']
        # pos = (config.CANVAS_SIZE[0] - x_displacement*ratio, 0)
        self.handler.canvas.blit(shop_bg, pos)

        clicked_button = None

        for i, button in enumerate(self.price_buttons):
            
            if button.text != 'Sold!':
                button_disabled_old = button.disabled
                button.disabled = button.price > self.gold
                if button_disabled_old != button.disabled:
                    button.generate_surf()


            button.rect.x = pos[0] + 5 + 120 + 5
            button.update(self.handler.inputs)
            button.render(self.handler.canvas)

            if button.clicked:
                if not button.disabled:
                    clicked_button = button, i

        if clicked_button:
            # TODO: more feedback for purchase

            i = clicked_button[1]
            self.locked_blocks[i].locked = False
            self.locked_blocks[i].generate_surf()
            self.locked_blocks[i] = None

            clicked_button[0].disabled = True
            clicked_button[0].text = 'Sold!'
