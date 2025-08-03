from copy import copy
import math
from random import random, uniform, choice, randint
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
from time import time

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
    changes = []

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

        if self.style == 'hp':
            if change > 0:
                str_change = f'+{change}'
                color = (0, 255, 0)
            else:
                str_change = str(change)
                color = (255, 50, 50)


            s = FONTS['basic'].get_surf(str_change, color=color)
            self.changes.append([s, 255, self.rect.midright + pygame.Vector2(5, -5)])

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
        self.vel = Vector2(0,0)

    @property
    def state(self):
        if self.locked:
            return 0
        else:
            return super().state

class Game(State):

    FIRE_DURATION = 50*5

    ENEMY_STATS={
        'skeleton': {
            'speed': 1,
            'dmg': 15,
            'hp': 15
        },
        'wizard': {
            'speed': 1,
            'dmg': 15,
            'hp': 15
        },
        'slime': {
            'speed': 0.5,
            'dmg': 5,
            'hp': 25
        },
        'slime_3': {
            'speed': 1,
            'dmg': 8,
            'hp': 10
        },
        'slime_2': {
            'speed': 1.3,
            'dmg': 5,
            'hp': 10
        },
        'enemy': {
            'speed': 1,
            'dmg': 20,
            'hp': 15,
        },
    }

    SHOP_SPEED = 10

    def __init__(self, *args, **kwargs):
        pygame.mixer.music.set_volume(0.8)
        sfx.play_music('song.wav', -1)

        super().__init__(*args, **kwargs)

        self.tutorial = pygame.Surface(config.CANVAS_SIZE, pygame.SRCALPHA)
        # self.tutorial.set_colorkey((0, 0, 0))
        

        tut_txt = FONTS['basic'].get_surf('''Welcome to the block shop.
In here the game is paused.
Use WASD to move (to leave the shop) and SPACE to dash.
But before leaving, make sure to setup your blocks
by dragging them in the forever loop.''')
        p = (180, 20)
        pygame.draw.rect(self.tutorial, (0, 0, 0, 50), (*p, *tut_txt.get_size()))
        self.tutorial.blit(tut_txt, p)
        self.tutorial.blit(Animation.img_db['arrow_'], (160, 105))




        self.first_shop = True


        self.game_over = False

        bg_size = 176
        wall_width = 60

        self.walls = [pygame.Rect(bg_size-wall_width, -wall_width, wall_width, config.SCREEN_SIZE[1]),
                      pygame.Rect(config.CANVAS_SIZE[0], 0, wall_width, config.SCREEN_SIZE[1]),
                      pygame.Rect(bg_size-wall_width, -wall_width, config.CANVAS_SIZE[0], wall_width),
                      pygame.Rect(0, config.CANVAS_SIZE[1], config.CANVAS_SIZE[0], wall_width)]


        y = 70
        # rects = [pygame.Rect(120, y+i*20, 120, 16) for i in range(20)]

        self.entity = PhysicsEntity(pos=(350, 30), name='side', action='idle', max_vel=1.5)
        self.entity.dashing = None
        self.entity.cooldown = None
        self.entity.fire = None
        self.player = self.entity

        self.entity.invincible = None
        self.e_speed = 1.5

        self.enemies = []
        # enemy = PhysicsEntity(pos=(200, 200), name='enemy', action='run', max_vel=1)
        # enemy.bar = Bar(pygame.Rect(0, 0, 15, 2), 10, 10, 'enemy')
        # enemy.dmg = 10
        # self.enemies.append(enemy)
        #
        # enemy = PhysicsEntity(pos=(200, 200), name='slime', action='run', max_vel=0.5)
        # enemy.bar = Bar(pygame.Rect(0, 0, 15, 2), 20, 20, 'enemy')
        # enemy.dmg = 10
        # self.enemies.append(enemy)

        self.bars = {
            'hp': Bar(pygame.Rect(10, 10, 100, 15), 100, 100, 'hp', 'HP'),
        }
        # self.gold = 5
        self.gold = 999
        # self.gold = 0

        self.projectiles=[]
        self.slashes = []
        self.pits = []
        
        self.loop_duration = 60
        self.particle_gens = []
        # self.particle_gens = [ParticleGenerator.from_template((200, 200), 'angle test'),
        #                       ParticleGenerator.from_template((300, 200), 'color test')]

        self.loop_block = Entity((10, y), 'loop_block')

        rects = [pygame.Rect(10, y+120+i*20, 120, 16) for i in range(20)]
        locked_rects = [pygame.Rect(config.CANVAS_SIZE[0], y+70+i*18, 120, 16) for i in range(20)]

        self.snap_positions = [(31, y+19+i*15) for i in range(5)]
        self.slots = [None for i in range(len(self.snap_positions))]
        self.blocks = [
            Block(3, 'hp', rects[0], 'Get 1 HP', 'red', disabled=True),
            Block(3, 'slash', rects[1], 'Slash', 'purple', disabled=True),
            Block(3, 'gold', rects[2], 'Get 1 Gold', 'yellow', disabled=True),

        ]

        self.locked_blocks = [
            Block(3, 'gold', locked_rects[0], 'Get 1 gold', 'yellow', disabled=True),
            Block(3, 'hp', locked_rects[1], 'Get 1 HP', 'red', disabled=True),
            Block(3, 'hp', locked_rects[2], 'Get 1 HP', 'red', disabled=True),
            Block(3, 'slash', locked_rects[3], 'Slash', 'purple', disabled=True),
            Block(3, 'projectile', locked_rects[4], 'Projectile', 'purple', disabled=True),
            Block(3, 'projectile', locked_rects[5], 'Projectile', 'purple', disabled=True),
            Block(3, 'fire', locked_rects[6], 'Ignite', 'orange', disabled=True),
            Block(15, 'water', locked_rects[7], 'Water', 'blue', disabled=True),
        ]

        self.prices = [10,
                       20,
                       20,
                       20,
                       20,
                       20,
                       30,]

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
                block.description = 'Horizontal melee attack at the\ndirection of your mouse\nWhen combined with a dash,\ndamage is doubled.'
            elif block.id == 'dash':
                block.description = 'Teleports towards direction of\nplayer movement.\nDifficult to use.'
            elif block.id == 'projectile':
                block.description = 'Shoots an arrow at mouse position.'
            elif block.id == 'pit':
                block.description = 'Creates a pit on cursor that deals\ndamage proportionate to the\nnumber of enemies inside.'
            elif block.id == 'fire':
                block.description = 'Light yourself up on fire!\nYou\'ll deal fire damage at\nthe cost of taking fire damage.'
            elif block.id == 'water':
                block.description = 'Extinguish fire.'
            else:
                block.description = ''

        self.buttons = {

        }
        self.arrow = Animation.img_db['arrow']

        self.selected_block = None

        self.shop = Entity((333, 0), 'shop', action='idle')

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

        self.t0 = time()
        self.last_enemy = time()
        self.enemy_interval = 3
        self.time_passed = 0

    def sub_update(self):
        # bg ------------
        # self.handler.canvas.fill(COLORS['green3'])
        self.handler.canvas.blit(Animation.img_db['bg'], (0, 0))
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
                continue

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
                # if slash.gen in self.particle_gens: self.particle_gens.remove(slash.gen)
                continue
            else:
                slash.render(self.handler.canvas)
                new_slashes.append(slash)
        self.slashes = new_slashes



        new_pits = []
        for pit in self.pits:
            if pit.done:
                # particle = ParticleGenerator.TEMPLATES['smoke']['base_particle'].copy()
                # particle.vel = projectile.vel * 0.3
                # self.particle_gens.append(
                #     ParticleGenerator.from_template(projectile.rect.center, 'smoke', base_particle=particle)
                # )
                continue

            if self.mode == 'game': pit.update()
            projectile.render(self.handler.canvas)
            new_pits.append(projectile)
        self.pits = new_pits




        

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
            elif block.id == 'fire':
                if not self.entity.fire:  # to prevent fire from reseting right after taking dmg, so u get hit a lot
                    self.entity.fire = Timer(self.FIRE_DURATION)
            elif block.id == 'water':
                if self.entity.fire:
                    self.entity.fire = None
                    self.particle_gens.append(ParticleGenerator.from_template(self.entity.rect.center, 'water'))
                    self.particle_gens.append(ParticleGenerator.from_template(self.entity.rect.center, 'smoke'))
            elif block.id == 'projectile':
                vel= -pygame.Vector2(self.entity.rect.center)+self.handler.inputs['mouse pos']
                vel.scale_to_length(6)

                projectile = Projectile(vel=vel, pos=self.entity.rect.center, name='projectile')

                
                if self.entity.fire:
                    projectile.fire = Timer(self.FIRE_DURATION)
                else:
                    projectile.fire = None

                self.projectiles.append(projectile)
            elif block.id == 'pit':
                pit = Entity(pos=self.inputs['mouse pos'], name='pit', action='idle')
                pit.done = False

                
                # if self.entity.fire:
                #     projectile.fire = Timer(self.FIRE_DURATION)
                # else:
                #     projectile.fire = None

                self.pits.append(pit)
            elif block.id == 'slash':
                # slash_pos = Vector2(self.entity.rect.center) - self.handler.inputs['mouse pos']
                # mouse_dist.scale_to_length(8)
                slash_pos = self.entity.rect.center


                vel = self.entity.vel.copy()
                if vel.length() > 3:
                    slash = PhysicsEntity(vel=vel, pos=(0,0), name='super_slash', action='idle')
                    if vel.x < 0:
                        coef = -1
                        flip = True
                    else:
                        coef = 1
                        flip = False
                else:
                    slash = PhysicsEntity(vel=vel, pos=(0,0), name='slash', action='idle')
                    if slash_pos[0] - self.handler.inputs['mouse pos'][0] > 0:
                        coef = -1
                        flip = True
                    else:
                        coef = 1
                        flip = False

                slash_pos = (slash_pos[0] + coef*16 - slash.img.get_width()*0.5, slash_pos[1] - slash.img.get_height()*0.5)
                slash.enemies = []

                slash._real_pos = slash_pos
                slash.animation.flip = (flip, False)

                if self.entity.fire:
                    slash.fire = Timer(self.FIRE_DURATION)
                else:
                    slash.fire = None
                slash.gen = None
                
                self.slashes.append(slash)

            elif block.id == 'gold':
                # sfx.sounds['money.wav'].play()
                self.gold += 1
                Bar.changes.append([FONTS['basic'].get_surf('+1', (0, 255, 0)), 255,  (10, 25) +  uniform(0, 15)*Vector2(1, 0.3) ])
            elif block.id == 'dash':
                self.particle_gens.append(
                    ParticleGenerator.from_template(self.entity.rect.center, 'player')
                )
                self.entity._real_pos += self.entity.vel * 50

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
                if self.mode == 'game':
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

        self.handler.canvas.blit(FONTS['basic'].get_surf(f'{self.gold} $'), (10, 30))

        # shop
        # pygame.draw.polygon(self.handler.canvas, COLORS['black'], self.shop_entrance)
        pygame.draw.polygon(self.handler.canvas, COLORS['blue'], [(p[0], p[1]) for p in self.random_points ])
        pygame.draw.polygon(self.handler.canvas, COLORS['black'], [(p[0], p[1]) for p in self.random_points ], width=3)
        self.shop.update()
        self.shop.render(self.handler.canvas)

        # update enemy

        self.t1 = time()
        if self.mode == 'game':
            self.time_passed += (self.t1 - self.t0)*1
        
            self.enemy_interval = 3 * (1 / (0.01*self.time_passed + 1))
            # self.enemy_interval = 10 * (1 / (0.01*self.time_passed + 1))

            if self.t1 - self.last_enemy >= self.enemy_interval:

                choices = [ 'slime_2', 'slime_3' ]
                if self.time_passed > 20:
                    choices.append('slime')
                if self.time_passed > 40:
                    choices.append('skeleton')
                if self.time_passed > 60:
                    choices.append('enemy')
                if self.time_passed > 80:
                    choices.append('wizard')

                # choices = ['slime']

                # print(self.time_passed, choices)

                enemy_name = choice(choices)

                # enemy = PhysicsEntity(pos=(350, 150), name=enemy_name, action='run')
                # enemy.bar = Bar(pygame.Rect(0, 0, 15, 2), 20, 20, 'enemy')
                # enemy.dmg = 10

                stats = self.ENEMY_STATS[enemy_name]
                enemy = PhysicsEntity(pos=(200, 200), name=enemy_name, action='run', max_vel=stats['speed'])
                enemy.fire = None
                enemy.bar = Bar(pygame.Rect(0, 0, 15, 2), stats['hp'], stats['hp'], 'enemy')
                enemy.dmg = stats['dmg']




                self.enemies.append(enemy)
                self.last_enemy = self.t1

        self.t0 = time()


        # fire
        burn = False
        for entity in [self.entity] + self.enemies + self.slashes + self.projectiles:
            if entity.fire:
                if entity.fire.done:
                    entity.fire = None
                    continue
                if entity.fire.frame % 50 == 0:
                    if self.mode == 'shop':
                        entity.fire.frame += 1
                    burn = True

                    if entity is self.entity:
                        
                        fire_before = False
                        water = False  # cause water doesnt have enough time to take effect automatically
                        for slot in self.slots:
                            if slot:
                                if slot.id == 'fire':
                                    fire_before = True
                                if slot.id == 'water':
                                    water = fire_before
                                    break
                        if water:
                            continue

                    gen = ParticleGenerator.from_template(entity.rect.center, 'fire')

                    gen.entity = entity
                    self.particle_gens.append(
                        gen
                    )

                    if entity is self.entity:
                        self.bars['hp'].change_val(-2)
                    elif entity in self.slashes + self.projectiles:
                        pass

                    # enemy
                    else:
                        entity.take_dmg(2, sound='fire')
                        # entity.bar.change_val(-2)
                if self.mode == 'game':
                    entity.fire.update()
                
        if burn: sfx.sounds['burn.wav'].play()


        for enemy in self.enemies:


            # update 
            enemy.vel = -enemy.pos + self.entity.pos
            enemy.animation.flip[0] = enemy.vel[0] < 0
                # enemy._real_pos = Vector2(300+100*ratio, 100)

            done = False
            if self.mode == 'game':
                done = enemy.update(self.walls)
                


            # shadow

            center = list(enemy.rect.midbottom)
            center[1] -= 3

            w = enemy.rect.w + 5
            h = 10
            rect = pygame.Rect(
                center[0] - w*0.5, 
                center[1] - h*0.5,
                w,
                h
            )
            s = pygame.Surface(rect.size)

            r = rect.copy()
            r.topleft = (0, 0)
            pygame.draw.ellipse(s, (0, 0, 10), r)
            s.set_colorkey((0, 0, 0))
            s.set_alpha(100)
            self.handler.canvas.blit(s, rect.topleft)



        new_enemies = []
        for enemy in self.enemies:

            if done and enemy.animation.action == 'hit':
                enemy.animation.set_action('run')

            for slash in self.slashes:
                if enemy not in slash.enemies and enemy.rect.colliderect(slash.rect):
                    slash.enemies.append(enemy)
                    # enemy.animation.set_action('hit')
                    if slash.name == 'slash':
                        enemy.take_dmg(5)
                        # enemy.bar.change_val(-5)
                    else:
                        enemy.take_dmg(10)
                        # enemy.bar.change_val(-10)

                    if slash.fire:
                        enemy.fire = Timer(self.FIRE_DURATION)

                    gen = ParticleGenerator.from_template(enemy.rect.center, 'shock')
                    gen.entity = enemy
                    self.particle_gens.append(
                        gen
                                            )

            for projectile in self.projectiles:
                if enemy not in projectile.enemies and enemy.rect.colliderect(projectile.rect):
                    projectile.enemies.append(enemy)
                    # enemy.animation.set_action('hit')
                    # enemy.bar.change_val(-4)
                    enemy.take_dmg(5)
                    projectile.dead = True
                    if projectile.fire:
                        enemy.fire = Timer(self.FIRE_DURATION)

            if enemy.rect.colliderect(self.entity.rect) and not self.entity.invincible and not self.game_over:
                self.entity.invincible = Timer(60)
                self.bars['hp'].change_val(-enemy.dmg)
                sfx.sounds['hurt.wav'].play()

            enemy.render(self.handler.canvas)
            enemy.bar.rect.midbottom = enemy.rect.midtop + Vector2(0, -6)
            # print(f'{particle_gen.base_particle.animation.action=}')
            enemy.bar.render(self.handler.canvas)
            
            if enemy.bar.value > 0:
                new_enemies.append(enemy)
            else:
                # self.particle_gens.append(
                #     ParticleGenerator.from_template(enemy.rect.center, 'big')
                # )
                self.particle_gens.append(
                    ParticleGenerator.from_template(enemy.rect.center, 'smoke')
                )
                self.particle_gens.append(
                    ParticleGenerator.from_template(enemy.rect.center, 'death')
                )
                # particle stuff here TODO
                sfx.sounds['kill.wav'].play()

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

        if not self.entity.dashing:
            self.entity.max_vel = 1.5
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

            if self.handler.inputs['pressed'].get('space') and not self.entity.cooldown:
                sfx.sounds['dash.wav'].play()
                self.entity.cooldown = Timer(20)
                self.entity.dashing = Timer(10)
                self.entity.max_vel = 5
                self.entity.vel = pygame.Vector2(self.entity.vel) * 5

            if self.entity.cooldown:
                self.entity.cooldown.update()
                if self.entity.cooldown.done:
                    self.entity.cooldown = None
        else:
            self.particle_gens.append(
                ParticleGenerator.from_template(self.entity.rect.center, 'player')
            )
            self.entity.dashing.update()
            done = self.entity.dashing.done
            if done: self.entity.dashing = None
            print(self.entity.dashing, self.entity.max_vel, self.entity.vel)

        self.entity.update(self.walls)
        self.entity.render(self.handler.canvas)

        if self.entity.rect.colliderect(self.shop.rect):
            # self.entity._real_pos = Vector2(340, 80)
            if self.mode == 'game':
                pygame.mixer.music.set_volume(0.3)
                sfx.sounds['enter.wav'].play()
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
                pygame.mixer.music.set_volume(0.8)
                sfx.sounds['exit.wav'].play()
                self.first_shop = False
                if self.shop_timer:
                    
                    offset = self.SHOP_SPEED - self.shop_timer.frame
                    self.shop_timer = Timer(self.SHOP_SPEED)
                    self.shop_timer.frame = offset
                else:
                    self.shop_timer = Timer(self.SHOP_SPEED)

            self.mode = 'game'

        # if self.handler.inputs['held'].get('mouse1'):
            # for wall in self.walls:
            #     pygame.draw.rect(self.handler.canvas, (200, 200, 0), wall)

        self.particle_gens = ParticleGenerator.update_generators(self.particle_gens)
        for particle_gen in self.particle_gens:
            if particle_gen.base_particle.animation.action in ('group', 'loop'):
                # print(f'{particle_gen.base_particle.animation.action=}')
                particle_gen.pos = particle_gen.entity.rect.center
            particle_gen.render(self.handler.canvas)

        new_changes = []
        for change in Bar.changes:
            img, alpha, pos = change
            if alpha <= 0:
                continue

            img.set_alpha(alpha)
            self.handler.canvas.blit(img, pos)
            change[1] -= 15
            new_changes.append(change)
            change[2] += Vector2(uniform(-1, 1), uniform(-1, 1))
        Bar.changes = new_changes

        # if self.mode == 'shop':
        self.render_shop()


        # loop block --------------
        self.loop_block.update()
        self.loop_block.render(self.handler.canvas)

        self.handler.canvas.blit(self.arrow, (14, self.snap_positions[self.block_i][1]+6))


        # block ---------------------------

        clicked_blocks = []
        hovered_block = None

        for block in self.blocks:
            print(f'{block.vel=} {type(block.vel)}')
            block.rect.topleft += block.vel
            # block.vel *= 0.88
            block.vel *= 0.84

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
            block.vel = pygame.Vector2(0, 0)
            if self.selected_block in self.slots:
                i = self.slots.index(self.selected_block)
                self.slots[i] = None
                sfx.sounds['switch27.ogg'].play()

        if hovered_block and hovered_block.description:
            self.block_hover_timer += 1
            if self.block_hover_timer > 10:
                self.block_hover_timer = 10
        else:
            self.block_hover_timer -= 1
            if self.block_hover_timer < 0:
                self.block_hover_timer = 0

        self.alpha = self.block_hover_timer/10*255

        # print(f'{self.alpha=}')

        if self.alpha != 0:

            if self.unreset_hovered_block:
                description = self.unreset_hovered_block.description
                description = f'- {self.unreset_hovered_block.text} -\n' + description
            else:
                description=''
                description = f'- {self.unreset_hovered_block.text} -\n' + description
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
                    sfx.sounds['switch18.ogg'].play()
                    break
        # -----------------------------------







        # text ----------
        text = [f'{round(self.handler.clock.get_fps())} fps',
                f'mouse pos {self.handler.inputs["mouse pos"]}',
                f'{self.timer=}',
                f'{self.block_i=}',


                ]
        # self.handler.canvas.blit(FONTS['basic'].get_surf('\n'.join(text)), (150, 200))





        # Shader -----

        if self.bars['hp'].value == 0:
            self.game_over = True
            self.handler.transition_to(self.handler.states.Menu)
            self.entity.invincible = None

            shader_handler.vars['caTimer'] = -1
            shader_handler.vars['shakeTimer'] = -1 
        else:

            shader_handler.vars['caTimer'] = 1 if self.mode == 'shop' and not self.first_shop else -1
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


            self.gold -= clicked_button[0].price

            i = clicked_button[1]
            self.locked_blocks[i].vel = Vector2(-28, 0)
            self.locked_blocks[i].locked = False
            self.locked_blocks[i].generate_surf()
            self.locked_blocks[i] = None

            clicked_button[0].disabled = True
            clicked_button[0].text = 'Sold!'

        if self.first_shop:
            self.handler.canvas.blit(self.tutorial, (0, 0))
            # self.tutorial
