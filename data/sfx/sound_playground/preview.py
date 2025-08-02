# chainmail2
# slime
import pygame
import sys
from os import listdir
from pathlib import Path
import glob

pygame.init()
screen = pygame.display.set_mode((800, 450))
clock = pygame.time.Clock()

def get_folder_files(directory, extension='png') -> list:
    """
    Output:
    
    [(WindowsPath('location/file.png'), 'file.png)]
    """
    
    paths = set()
    
    # for file in listdir(directory):
    #     if file.lower().endswith(extension):
    #         paths.add((Path(f'{directory}/{file}'), file))
    for file in glob.iglob(directory + '**/**', recursive=True):
        if file.lower().endswith(extension):
            paths.add((Path(f'{directory}/{file}'), file))
            
    return paths

def get_sfx(directory):
    output = {}
    wav_files = get_folder_files(directory, extension='wav')
    ogg_files = get_folder_files(directory, extension='ogg')
    files = wav_files.union(ogg_files)
    for location, file in files:
        output[file] = pygame.mixer.Sound(location)
        # output[file.split('.')[0]] = pygame.mixer.Sound(location)
        
    return output

font = pygame.font.SysFont('Courier New', 24)

sfx = [data for data in get_sfx('./').items()]
sfx = sorted(sfx, key=lambda i: i[0])

running = True
index = 0
while running:
    
    space_pressed = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RIGHT:
                index += 1
            if event.key == pygame.K_LEFT:
                index -= 1
            if event.key == pygame.K_SPACE:
                space_pressed = True
            
    if index >= len(sfx): index = 0
    elif index < 0: index = len(sfx) - 1
    current_sfx = sfx[index]
    
    if space_pressed:
        current_sfx[1].play()
    
    screen.fill((0, 0, 0))
    screen.blit(font.render(f'{index + 1} / {len(sfx)}\n{current_sfx[0]}', True, (240, 240, 240)), (0, 0))
    
    pygame.display.update()
    clock.tick(30)

pygame.quit()            
sys.exit()
