import os
import pygame

pygame.mixer.init()

SOUNDS_DIR = os.path.join('data/sfx/sounds')
MUSIC_DIR = os.path.join('data/sfx/music')

def play_music(file_name, *args, **kwargs):
    # Program freezes when there's music.fadeout
    # So for the music to forcefully play, the fadout must be stopped. 
    pygame.mixer.music.stop()
    pygame.mixer.music.load(os.path.join(MUSIC_DIR, file_name))
    pygame.mixer.music.play(*args, **kwargs)

def load_sounds():
    sounds = {}
    for file in os.listdir(SOUNDS_DIR):
        full_file = os.path.join(SOUNDS_DIR, file)
        sound = pygame.mixer.Sound(full_file)
        print(sound)
        sounds[file] = sound
    return sounds

sounds = load_sounds()
