# from .screen import screen
import pygame
import json
from glob import glob

def load_img(path, colorkey=(0, 0, 0)):
    img = pygame.image.load(path).convert()
    img.set_colorkey(colorkey)
    return img
    # return pygame.transform.scale_by(img, SCALE)

def get_files(directory):
    return glob(directory)

def read_txt(path):
    with open(path) as f:
        content = f.read()
    return content

def read_json(path):
    data = read_txt(path)
    return json.loads(data)

def swap_colors(surface, old_color, new_color):
    surface_copy = surface.copy()
    output_surface = surface.copy()
    output_surface.fill(new_color)
    surface_copy.set_colorkey(old_color)
    output_surface.blit(surface_copy, (0, 0))
    return output_surface
