import pygame
import sys
import os
import random
import math

# ── Constants ────────────────────────────────────────────────────────────────
NATIVE_W, NATIVE_H = 1920, 1080  # internal render resolution (matches bg art)
TILE_SIZE = 90
FPS = 60
GRAVITY = 0.7
JUMP_FORCE = -22
MOVE_SPEED = 9
CAMERA_LERP = 0.08  # lower = more lag bwteen input and camera movement

# Colours these are placeholders
SKY_COLOR = (30, 30, 46)
WALL_COLOR = (80, 80, 110)
WALL_EDGE_COLOR = (110, 110, 150)

# Mayank code constants
# Combat constants
DAMAGE_MULTIPLIER = 1
BASE_ATTACK_DAMAGE = 10
ATTACK_DAMAGE = BASE_ATTACK_DAMAGE * DAMAGE_MULTIPLIER
ATTACK_RANGE = 110  # reach of the sword hitbox, in px
ATTACK_HITBOX_HEIGHT = 100
ACTIVE_ATTACK_FRAMES = (1, 2)  # which attack frames actually deal damage

ENEMY_MAX_HEALTH = 30
GHOUL_MAX_HEALTH = 60

COIN_DROP_MIN, COIN_DROP_MAX = 1, 5
DROP_PICKUP_RANGE = 60
DROP_MAGNET_RANGE = 220

PLAYER_LEVEL = 1

# Player health contants
HEALTH_MULTIPLIER = 1
PLAYER_BASE_MAX_HEALTH = 100
PLAYER_MAX_HEALTH = PLAYER_BASE_MAX_HEALTH * HEALTH_MULTIPLIER
ENEMY_CONTACT_DAMAGE = 10
GHOUL_CONTACT_DAMAGE = 20
PLAYER_INVULN_TIME = 1.0  # seconds of invincibility after being hit

# Knockback
PLAYER_KNOCKBACK_X = 24
PLAYER_KNOCKBACK_Y = -8
PLAYER_KNOCKBACK_DURATION = 0.2

ENEMY_KNOCKBACK_SPEED = 14
ENEMY_KNOCKBACK_DURATION = 0.15

GHOUL_KNOCKBACK_SPEED = 16
GHOUL_KNOCKBACK_DURATION = 0.15

KNOCKBACK_FRICTION = 0.85   # how fast knockback velocity decays each frame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset(name):
    return os.path.join(BASE_DIR, name)


def crop_transparent(image):
    rect = image.get_bounding_rect()

    if rect.width == 0 or rect.height == 0:
        return image

    return image.subsurface(rect).copy()


# Global sound placeholders (using MockSound to prevent crashes if files are missing)
class MockSound:
    def play(self): pass

    def set_volume(self, v): pass

    def stop(self): pass


jump_sound = MockSound()
walk_sound = MockSound()
sword_sound = MockSound()
ghoul_sound = MockSound()
damage_sound = MockSound()
gameover_sound = MockSound()
levelup_sound = MockSound()

def load_sounds():
    global jump_sound, walk_sound, sword_sound, ghoul_sound, damage_sound,  gameover_sound, levelup_sound
    try:
        jump_sound = pygame.mixer.Sound(asset("assets/pragassets/Jump.wav"))
        walk_sound = pygame.mixer.Sound(asset("assets/pragassets/Walk.wav"))
        sword_sound = pygame.mixer.Sound(asset("assets/pragassets/Sword.wav"))
        ghoul_sound = pygame.mixer.Sound(asset("assets/pragassets/Ghoul.wav"))
        damage_sound = pygame.mixer.Sound(asset("assets/pragassets/Damage.wav"))
        gameover_sound = pygame.mixer.Sound(asset("assets/pragassets/GameOver.wav"))
        levelup_sound = pygame.mixer.Sound(asset("assets/pragassets/LevelUp.wav"))

        walk_sound.set_volume(0.3)
        ghoul_sound.set_volume(0.4)
    except Exception as e:
        print(f"Warning: Could not load some sound files: {e}")


# ── Level grid  (0 = empty, 1 = wall)
# 12 rows × 106 columns  →  world = 9600 × 1080 px

# Each row = 90 px tall, each col = 90 px wide.
# Add/remove columns but every row must stay the same length.
GRID = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1.1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,1,1,0,0,0,0,0,1,1,1,1,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,0,0,0,0,1,1,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,2,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,1,1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,0,8,0,0,0,1,1,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,1,1,1,1,1,1,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,1,1,1,0,0,0,1,0,0,2,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,2,0,0,1,1,1,1,1,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,1,1,1,0,1,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,1,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,1,1,0,0,0,1,0,0,0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,1,1,1,1,1,1,0,0,0,0,0,1,1,1,0,0,0,0,0,0,1,0,0,1,1,0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,2,0,0,0,1,0,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,1,1,0,0,1,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,1,0,1,1,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,1,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,2,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,2,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,1,1,1,1,0,0,1,1,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,0,2,1,0,0,0,0,0,0,0,0,0,2,0,0,0,0,1,0,0,2,0,0,0,0,2,0,0,0,1,1,1,1,1,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
]

GRID_ROWS = len(GRID)
GRID_COLS = max(len(row) for row in GRID)
WORLD_W = GRID_COLS * TILE_SIZE  # 9600
WORLD_H = GRID_ROWS * TILE_SIZE  # 1080

# ── Background zones
# Each zone covers a horizontal slice of the world.
# Zones are checked left-to-right; first match wins.
# For now they all fall back to a solid colour placeholder
ZONES = [
    {"x_start": 0, "x_end": 3840, "bg": "bg_1.jpg", "fallback": (20, 40, 20)},
    {"x_start": 3840, "x_end": 6720, "bg": "bg_2.jpg", "fallback": (20, 20, 40)},
    {"x_start": 6720, "x_end": 9600, "bg": "bg_3.jpg", "fallback": (40, 20, 20)},
]


def load_bg_images():
    global background
    global stone_tiles
    global grass_tiles
    global coin_image

    background = pygame.image.load(
        asset("assets/pragassets/bgplagaa.jpg")
    ).convert()

    stone_tiles = []
    grass_tiles = []

    for i in range(1, 5):
        img = pygame.image.load(
            asset(f"assets/pragassets/walls{i}.jpg")
        ).convert_alpha()

        stone_tiles.append(crop_transparent(img))
        img = pygame.image.load(
            asset(f"assets/pragassets/floor{i}.jpg")
        ).convert_alpha()

        grass_tiles.append(crop_transparent(img))


def build_wall_rects():
    global tile_map

    rects = []
    tile_map = {}

    for r, row in enumerate(GRID):

        for c, cell in enumerate(row):

            if cell != 1:
                continue

            rects.append(
                pygame.Rect(
                    c * TILE_SIZE,
                    r * TILE_SIZE,
                    TILE_SIZE,
                    TILE_SIZE
                )
            )

            surface = (
                    r == 0 or
                    GRID[r - 1][c] == 0
            )

            if surface:

                tile_map[(r, c)] = random.choice(grass_tiles)

            else:

                tile_map[(r, c)] = random.choice(stone_tiles)

    return rects


def build_enemy_spawns():
    normal_spawns = []
    ghoul_spawns = []
    tonic_spawns = []

    for r, row in enumerate(GRID):

        for c, cell in enumerate(row):

            x = c * TILE_SIZE
            y = r * TILE_SIZE

            if cell == 2:
                normal_spawns.append((x, y))

            elif cell == 3:
                ghoul_spawns.append((x, y))

            elif cell == 8:
                tonic_spawns.append((x, y))

    return normal_spawns, ghoul_spawns, tonic_spawns


def lerp(a, b, t):
    return a + (b - a) * t


# Camera
class Camera:
    # Renders to a NATIVE_W *NATIVE_H surface; that surface is then scaled to the actual monitor resolution so the game always looks correct

    def __init__(self):
        self.x = 0.0
        self.y = 0.0

    def update(self, target_rect):
        tx = target_rect.centerx - NATIVE_W / 2
        ty = target_rect.centery - NATIVE_H / 2
        self.x = lerp(self.x, tx, CAMERA_LERP)
        self.y = lerp(self.y, ty, CAMERA_LERP)
        # Clamp to world edges
        self.x = max(0, min(self.x, WORLD_W - NATIVE_W))
        self.y = max(0, min(self.y, WORLD_H - NATIVE_H))

    def apply(self, rect):
        return rect.move(-int(self.x), -int(self.y))


# Player
class Player:
    WALK_FRAME_TIME = 0.08
    ATTACK_FRAME_TIME = 0.045

    SPRITE_SCALE = 1

    def __init__(self, x, y,
                 idle,
                 walk_frames,
                 attack1,
                 attack2):

        # ---------------- Collision ----------------

        self.rect = pygame.Rect(
            x,
            y,
            TILE_SIZE - 60,
            TILE_SIZE + 25
        )

        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False

        # ---------------- Direction ----------------

        self.facing = "left"  # left/right
        self.flip = False

        # ---------------- Images ----------------

        self.idle = self.scale(idle)

        self.walk = [self.scale(img) for img in walk_frames]

        self.attack_left = [self.scale(img) for img in attack1]
        self.attack_right = [self.scale(img) for img in attack2]

        self.image = self.idle

        # ---------------- Animation ----------------

        self.walk_frame = 0
        self.walk_timer = 0

        self.attack_frame = 0
        self.attack_timer = 0

        self.attacking = False

        self.attack_combo = 0

        # Used later for drawing slash separately
        self.current_slash = None

        # Attacks and hitboxes
        self.hit_this_swing = set()

        # ---------------- Health ----------------
        self.max_health = PLAYER_MAX_HEALTH
        self.health = self.max_health
        self.invuln_timer = 0.0  # counts down; can't take damage while > 0
        self.is_dead = False

        self.knockback_timer = 0.0

    def scale(self, img):

        w = img.get_width()
        h = img.get_height()

        return pygame.transform.scale(
            img,
            (
                w * self.SPRITE_SCALE,
                h * self.SPRITE_SCALE
            )
        )

    def attack(self):

        if self.attacking:
            return

        self.attacking = True
        sword_sound.play()

        self.attack_frame = 0
        self.attack_timer = 0

        self.attack_combo = 1 - self.attack_combo

        self.hit_this_swing = set()  # set of IDs of enemies who were hit by this swing

    def get_attack_hitbox(self):
        if not self.attacking or self.attack_frame not in ACTIVE_ATTACK_FRAMES:
            return None
        if self.facing == "left":
            x = self.rect.left - ATTACK_RANGE
        else:
            x = self.rect.right
        y = self.rect.centery - ATTACK_HITBOX_HEIGHT // 2
        return pygame.Rect(x, y, ATTACK_RANGE, ATTACK_HITBOX_HEIGHT)

    def take_damage(self, amount):
        if self.is_dead or self.invuln_timer > 0:
            return False
        self.health -= amount
        self.invuln_timer = PLAYER_INVULN_TIME
        damage_sound.play() 
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            gameover_sound.play()
        return True

    def update_timers(self, dt):
        if self.invuln_timer > 0:
            self.invuln_timer -= dt

    def apply_knockback(self, direction):
        """direction: -1 (push left) or 1 (push right)"""
        self.vel_x = PLAYER_KNOCKBACK_X * direction
        self.vel_y = PLAYER_KNOCKBACK_Y
        self.knockback_timer = PLAYER_KNOCKBACK_DURATION

    def handle_input(self):

        if self.knockback_timer > 0:
            return  # NEW — let knockback velocity carry through, ignore keys

        keys = pygame.key.get_pressed()

        self.vel_x = 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -MOVE_SPEED
            self.flip = True  # or False depending on your final flip logic
            self.facing = "left"

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = MOVE_SPEED
            self.flip = False  # or True depending on your final flip logic
            self.facing = "right"

        if (keys[pygame.K_SPACE]
            or keys[pygame.K_UP]
            or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_FORCE
            self.on_ground = False
            walk_sound.stop()
            jump_sound.play()

    def apply_gravity(self):

        self.vel_y = min(self.vel_y + GRAVITY, 22)

    def move_and_collide(self, walls):

        self.rect.x += int(self.vel_x)

        for w in walls:

            if self.rect.colliderect(w):

                if self.vel_x > 0:

                    self.rect.right = w.left

                elif self.vel_x < 0:

                    self.rect.left = w.right

        self.rect.y += int(self.vel_y)

        self.on_ground = False

        for w in walls:

            if self.rect.colliderect(w):

                if self.vel_y > 0:

                    self.rect.bottom = w.top
                    self.vel_y = 0
                    self.on_ground = True

                else:

                    self.rect.top = w.bottom
                    self.vel_y = 0

        self.rect.clamp_ip(
            pygame.Rect(
                0,
                0,
                WORLD_W,
                WORLD_H
            )
        )

    def animate(self):

        dt = 1 / FPS

        # ---------------- Attack ----------------

        if self.attacking:

            self.attack_timer += dt

            if self.attack_timer >= self.ATTACK_FRAME_TIME:

                self.attack_timer = 0

                self.attack_frame += 1

                if self.attack_frame >= 4:
                    self.attacking = False

                    self.attack_frame = 0

            # ---------- Slash Animation ----------

            if self.attack_combo == 0:
                attack_frames = self.attack_left  # left-hand slash
            else:
                attack_frames = self.attack_right  # right-hand slash
            SLASH_SCALE = 1.6  # Increase this to make it bigger

            slash = attack_frames[self.attack_frame]

            w = slash.get_width()
            h = slash.get_height()

            self.current_slash = pygame.transform.scale(
                slash,
                (int(w * SLASH_SCALE), int(h * SLASH_SCALE))
            )

            return

        # ---------------- Walking ----------------

        self.current_slash = None

        if self.vel_x != 0:

            self.walk_timer += dt

            if self.walk_timer >= self.WALK_FRAME_TIME:

                self.walk_timer = 0

                self.walk_frame += 1

                self.walk_frame %= 7

                if self.on_ground and (self.walk_frame == 0 or self.walk_frame == 4):
                    walk_sound.stop()
                    walk_sound.play()

            self.image = self.walk[self.walk_frame]

        else:

            if self.image != self.idle:
                walk_sound.stop()

            self.walk_frame = 0
            self.walk_timer = 0

            self.image = self.idle

    def update(self, walls):

        dt = 1 / FPS
        if not self.is_dead:

            if self.knockback_timer > 0:
                self.knockback_timer -= dt
                self.vel_x *= KNOCKBACK_FRICTION  # NEW — bleed off horizontal speed

            self.handle_input()

            self.apply_gravity()

            self.move_and_collide(walls)

            self.animate()
        self.update_timers(dt)

    def draw(self, surface, camera):

        # ---------- Draw Ghost ----------

        sprite = self.image

        if self.flip:
            sprite = pygame.transform.flip(sprite, True, False)

        draw_rect = sprite.get_rect(
            midbottom=(
                self.rect.centerx,
                self.rect.bottom + 50  # Adjust if you want the ghost higher/lower
            )
        )

        # Flicker while invulnerable
        if self.invuln_timer > 0 and int(self.invuln_timer * 10) % 2 == 0:
            return  # skip drawing this frame → flicker effect

        surface.blit(
            sprite,
            camera.apply(draw_rect)
        )

        # ---------- Draw Slash ----------

        if self.current_slash:

            slash = self.current_slash

            if self.facing == "left":

                slash = pygame.transform.flip(slash, True, False)

                slash_rect = slash.get_rect(
                    midright=(
                        draw_rect.left + 250,
                        draw_rect.centery
                    )
                )

            else:  # facing right

                slash_rect = slash.get_rect(
                    midleft=(
                        draw_rect.right - 230,
                        draw_rect.centery
                    )
                )

            surface.blit(
                slash,
                camera.apply(slash_rect)
            )

        # ---------- Collision Box (Debug) ----------

        '''pygame.draw.rect(
            surface,
            (255, 0, 0),
            camera.apply(self.rect),
            2
        )'''


# Enemy
class Enemy:
    def __init__(self, x, y, image, speed=2):
        w, h = TILE_SIZE - 10, TILE_SIZE - 6
        # y passed in is the TOP of the spawn tile; snap rect bottom to the
        # bottom of that tile (= top of the platform tile below it)
        self.rect = pygame.Rect(x, y + (TILE_SIZE - h), w, h)
        self.speed = speed
        self.direction = 1  # 1 = right, -1 = left
        self.image = pygame.transform.scale(image, (w, h))

        # health mechanics
        self.max_health = ENEMY_MAX_HEALTH
        self.health = self.max_health
        self.alive = True

        self.knockback_timer = 0.0
        self.knockback_vel_x = 0.0

    def update(self, walls):
        dt = 1 / FPS
        if self.knockback_timer > 0:
            self.knockback_timer -= dt
            self.rect.x += int(self.knockback_vel_x)
            self.knockback_vel_x *= KNOCKBACK_FRICTION
            for w in walls:
                if self.rect.colliderect(w):
                    if self.knockback_vel_x > 0:
                        self.rect.right = w.left
                    elif self.knockback_vel_x < 0:
                        self.rect.left = w.right
            return  # skip normal patrol AI while being knocked back

        move_x = self.speed * self.direction
        next_rect = self.rect.move(move_x, 0)
        hit_wall = any(next_rect.colliderect(w) for w in walls)
        foot_x = next_rect.right - 1 if self.direction > 0 else next_rect.left
        probe = pygame.Rect(foot_x, self.rect.bottom + 2, 2, 4)
        ground_ahead = any(probe.colliderect(w) for w in walls)
        if hit_wall or not ground_ahead:
            self.direction *= -1
        else:
            self.rect.x += move_x

    def draw(self, surface, camera):
        img = pygame.transform.flip(self.image, self.direction < 0, False)
        surface.blit(img, camera.apply(self.rect))

    # Damage taking mechanics
    def take_damage(self, amount):
        """Returns True if enemy is dead, False if alive or if already dead"""
        if not self.alive:
            return False
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False
            return True  # died from this hit
        return False

    def apply_knockback(self, direction):
        self.knockback_vel_x = ENEMY_KNOCKBACK_SPEED * direction
        self.knockback_timer = ENEMY_KNOCKBACK_DURATION


# ---------------------------------------------------------
# Ghoul
# ---------------------------------------------------------

class Ghoul:
    DETECTION_RANGE = 500
    SPEED = 5
    SOUND_COOLDOWN = 3.0

    def __init__(self, x, y, image):

        w = TILE_SIZE + 100
        h = TILE_SIZE + 100

        self.rect = pygame.Rect(
            x,
            y,
            w,
            h
        )

        self.sound_timer = 0

        self.image = pygame.transform.scale(
            image,
            (w, h)
        )

        # health mechanics
        self.max_health = GHOUL_MAX_HEALTH
        self.health = self.max_health
        self.alive = True

        self.knockback_timer = 0.0
        self.knockback_vel_x = 0.0
        self.knockback_vel_y = 0.0

    def update(self, player):
        dt = 1 / FPS
        if self.knockback_timer > 0:
            self.knockback_timer -= dt
            self.rect.x += int(self.knockback_vel_x)
            self.rect.y += int(self.knockback_vel_y)
            self.knockback_vel_x *= KNOCKBACK_FRICTION
            self.knockback_vel_y *= KNOCKBACK_FRICTION
            return  # skip chase AI while being knocked back

        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        distance = math.hypot(dx, dy)

        if distance <= self.DETECTION_RANGE and distance > 0:
            self.rect.x += int((dx / distance) * self.SPEED)
            self.rect.y += int((dy / distance) * self.SPEED)

            if self.sound_timer <= 0:            # ← add this block
                ghoul_sound.play()
                self.sound_timer = self.SOUND_COOLDOWN

    def draw(self, surface, camera):

        surface.blit(
            self.image,
            camera.apply(self.rect)
        )

    # Damage taking mechanics
    def take_damage(self, amount):
        """Returns True if enemy is dead, False if alive or if already dead"""
        if not self.alive:
            return False
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False
            return True  # died from this hit
        return False

    def apply_knockback(self, dx, dy):
        length = math.hypot(dx, dy) or 1
        self.knockback_vel_x = (dx / length) * GHOUL_KNOCKBACK_SPEED
        self.knockback_vel_y = (dy / length) * GHOUL_KNOCKBACK_SPEED
        self.knockback_timer = GHOUL_KNOCKBACK_DURATION


class Tonic:
    PICKUP_RANGE = 80

    def __init__(self, x, y, image):

        self.rect = pygame.Rect(
            x,
            y,
            TILE_SIZE,
            TILE_SIZE
        )

        self.image = pygame.transform.scale(
            image,
            (int(1.5 * TILE_SIZE), int(1.5 * TILE_SIZE))
        )

        self.collected = False

    def near_player(self, player):

        dx = self.rect.centerx - player.rect.centerx
        dy = self.rect.centery - player.rect.centery

        return dx * dx + dy * dy <= self.PICKUP_RANGE ** 2

    def collect(self, player):

        if not self.collected and self.near_player(player):
            self.collected = True

            # Immediately attach to player
            self.rect.centerx = player.rect.centerx - 25
            self.rect.centery = player.rect.centery + 30

            return True

        return False

    def update(self, player):

        if self.collected:
            # Follow player exactly
            self.rect.centerx = player.rect.centerx - 20
            self.rect.centery = player.rect.centery + 30

    def draw(self, surface, camera):

        # Draw both before and after pickup.
        # After pickup, rect follows the player.
        image_rect = self.image.get_rect(
            center=self.rect.center
        )

        surface.blit(
            self.image,
            camera.apply(image_rect)
        )


class Drop:
    """number of things (coins/exp) spawned where an enemy died."""

    def __init__(self, x, y, value, image):
        self.rect = pygame.Rect(x - 14, y - 14, 28, 28)
        self.value = value
        self.collected = False
        self._t = random.uniform(0, math.pi * 2)
        self.image = pygame.transform.scale(image, (self.rect.width, self.rect.height))

    def update(self, player):
        self._t += 0.1
        self.rect.y += math.sin(self._t) * 0.3  # gentle bob

        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        dist = math.hypot(dx, dy)

        if dist < DROP_MAGNET_RANGE and dist > 0:
            pull = 6
            self.rect.x += int((dx / dist) * pull)
            self.rect.y += int((dy / dist) * pull)

        if dist <= DROP_PICKUP_RANGE:
            self.collected = True

    def draw(self, surface, camera):
        surface.blit(self.image, camera.apply(self.rect))
        # pygame.draw.circle(
        #     surface, (255, 215, 0),
        #     camera.apply(self.rect).center,
        #     self.rect.width // 2
        # )


def draw_background(surface, camera):
    bw = background.get_width()
    bh = background.get_height()

    start_x = -(camera.x % bw)
    start_y = -(camera.y % bh)

    for x in range(int(start_x) - bw, NATIVE_W + bw, bw):
        for y in range(int(start_y) - bh, NATIVE_H + bh, bh):
            surface.blit(background, (x, y))


def draw_world(surface, camera):
    visible = pygame.Rect(
        camera.x,
        camera.y,
        NATIVE_W,
        NATIVE_H
    )

    for (r, c), img in tile_map.items():

        world_rect = pygame.Rect(
            c * TILE_SIZE,
            r * TILE_SIZE,
            TILE_SIZE,
            TILE_SIZE
        )

        if not visible.colliderect(world_rect):
            continue

        img = pygame.transform.scale(
            img,
            (TILE_SIZE, TILE_SIZE)
        )

        surface.blit(
            img,
            camera.apply(world_rect)
        )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    # pygame.mixer.init()

    # Fullscreen at native monitor resolution
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    info = pygame.display.Info()
    MONITOR_W = info.current_w
    MONITOR_H = info.current_h
    pygame.display.set_caption("Platformer")

    # All game rendering happens on this fixed surface, then scaled to screen
    canvas = pygame.Surface((NATIVE_W, NATIVE_H))

    clock = pygame.time.Clock()

    # Load assets
    load_bg_images()
    load_sounds()
    try:

        idle = pygame.image.load(
            asset("assets/pragassets/plaga_standing.png")
        ).convert_alpha()

        coin_image = pygame.image.load(
            asset("assets/pragassets/drop.jpg")
        ).convert_alpha()

        walk_frames = []

        for i in range(1, 8):
            walk_frames.append(

                pygame.image.load(
                    asset(f"assets/pragassets/praga_moving_{i}.png")
                ).convert_alpha()

            )

        attack1 = []

        for i in range(1, 5):
            attack1.append(

                pygame.image.load(
                    asset(f"assets/pragassets/praga_attack_{i}.png")
                ).convert_alpha()

            )

        attack2 = []

        for i in range(1, 5):
            attack2.append(

                pygame.image.load(
                    asset(f"assets/pragassets/praga_attackr_{i}.png")
                ).convert_alpha()

            )
            ghoul_image = pygame.image.load(
                asset("assets/pragassets/ghoul.png")
            ).convert_alpha()
            tonic_image = pygame.image.load(
                asset("assets/pragassets/tonic.png")
            ).convert_alpha()

    except FileNotFoundError as e:

        print(e)

        pygame.quit()

        sys.exit()
        idle = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        idle.fill((220, 60, 220))
        print("test.png not found using placeholder sprite.")
    except Exception as e:
        print(e)
        pygame.quit()
        sys.exit()

    wall_rects = build_wall_rects()

    normal_spawns, ghoul_spawns, tonic_spawns = build_enemy_spawns()

    enemies = [
        Enemy(x, y, idle)
        for x, y in normal_spawns
    ]

    ghouls = [
        Ghoul(x, y, ghoul_image)
        for x, y in ghoul_spawns
    ]
    tonics = [
        Tonic(x, y, tonic_image)
        for x, y in tonic_spawns
    ]
    spawn_col = 1
    spawn_row = GRID_ROWS - 2
    player = Player(

        spawn_col * TILE_SIZE + 4,
        spawn_row * TILE_SIZE - TILE_SIZE,

        idle,
        walk_frames,
        attack1,
        attack2

    )

    camera = Camera()
    camera.x = player.rect.centerx - NATIVE_W / 2
    camera.y = player.rect.centery - NATIVE_H / 2

    font = pygame.font.SysFont("monospace", 20)
    tonic_message = ""
    tonic_message_timer = 0

    # enemy drops
    coins = 0
    drops = []
    xp_to_next_level = COIN_DROP_MAX * 5 - 2
    game_paused_for_levelup = False

    while True:
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:

                if game_paused_for_levelup:

                    if event.key == pygame.K_1:
                        global HEALTH_MULTIPLIER, PLAYER_BASE_MAX_HEALTH, PLAYER_LEVEL
                        HEALTH_MULTIPLIER += 0.2
                        player.max_health = int(PLAYER_BASE_MAX_HEALTH * HEALTH_MULTIPLIER)

                        PLAYER_LEVEL += 1
                        xp_to_next_level += COIN_DROP_MAX * 5 - 2
                        game_paused_for_levelup = False

                    elif event.key == pygame.K_2:
                        global DAMAGE_MULTIPLIER, ATTACK_DAMAGE, BASE_ATTACK_DAMAGE
                        DAMAGE_MULTIPLIER += 0.2

                        ATTACK_DAMAGE = BASE_ATTACK_DAMAGE * DAMAGE_MULTIPLIER

                        PLAYER_LEVEL += 1
                        xp_to_next_level += COIN_DROP_MAX * 5 - 2
                        game_paused_for_levelup = False
                    player.health += player.max_health/2
                    continue

                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if event.key == pygame.K_x:
                    player.attack()

                if event.key == pygame.K_u:

                    for tonic in tonics:

                        if tonic.collect(player):
                            tonic_message = "Tonic of Healing Acquired"
                            tonic_message_timer = 120

                if event.key == pygame.K_r and player.is_dead:
                    # ---------- Rebuild enemies / ghouls / tonics from original spawn points ----------
                    enemies = [Enemy(x, y, idle) for x, y in normal_spawns]
                    ghouls = [Ghoul(x, y, ghoul_image) for x, y in ghoul_spawns]
                    tonics = [Tonic(x, y, tonic_image) for x, y in tonic_spawns]

                    # ---------- Clear drops / coins ----------
                    drops = []
                    coins = 0

                    # ---------- Reset player ----------
                    player.max_health = PLAYER_BASE_MAX_HEALTH
                    player.health = player.max_health
                    PLAYER_LEVEL = 1
                    player.is_dead = False
                    player.invuln_timer = 0
                    player.rect.x = spawn_col * TILE_SIZE + 4
                    player.rect.y = spawn_row * TILE_SIZE - TILE_SIZE
                    player.vel_x = 0
                    player.vel_y = 0

                    # ---------- Reset any HUD messages ----------
                    tonic_message = ""
                    tonic_message_timer = 0

        if game_paused_for_levelup:
            continue

        if not game_paused_for_levelup:
            player.update(wall_rects)

            # ---------- Attack collisions ----------
            hitbox = player.get_attack_hitbox()
            if hitbox:
                for enemy in enemies:
                    if enemy.alive and id(enemy) not in player.hit_this_swing and hitbox.colliderect(enemy.rect):
                        player.hit_this_swing.add(id(enemy))
                        died = enemy.take_damage(ATTACK_DAMAGE)
                        direction = 1 if enemy.rect.centerx >= player.rect.centerx else -1
                        enemy.apply_knockback(direction)  # NEW
                        if died:
                            drops.append(Drop(enemy.rect.centerx, enemy.rect.centery,
                                              random.randint(COIN_DROP_MIN, COIN_DROP_MAX),
                                              coin_image))
                for ghoul in ghouls:
                    if ghoul.alive and id(ghoul) not in player.hit_this_swing and hitbox.colliderect(ghoul.rect):
                        player.hit_this_swing.add(id(ghoul))
                        died = ghoul.take_damage(ATTACK_DAMAGE)
                        dx = ghoul.rect.centerx - player.rect.centerx  # NEW
                        dy = ghoul.rect.centery - player.rect.centery  # NEW
                        ghoul.apply_knockback(dx, dy)  # NEW
                        if died:
                            drops.append(Drop(ghoul.rect.centerx, ghoul.rect.centery,
                                              random.randint(COIN_DROP_MIN + 2, COIN_DROP_MAX + 3),
                                              coin_image))

            # ---------- Clear the dead enemies ----------
            enemies = [e for e in enemies if e.alive]
            ghouls = [g for g in ghouls if g.alive]

            for enemy in enemies:
                enemy.update(wall_rects)

            for ghoul in ghouls:
                ghoul.update(player)
            for tonic in tonics:
                tonic.update(player)

            # ---------- Drops ----------
            for drop in drops:
                drop.update(player)
            coins += sum(d.value for d in drops if d.collected)
            if player.health >= player.max_health:
                player.health = player.max_health
            drops = [d for d in drops if not d.collected]

            # ---------- Deal damage to player ----------
            if not player.is_dead:
                for enemy in enemies:
                    if player.rect.colliderect(enemy.rect):
                        direction = 1 if player.rect.centerx >= enemy.rect.centerx else -1
                        if player.take_damage(ENEMY_CONTACT_DAMAGE):
                            player.apply_knockback(direction)  # NEW
                for ghoul in ghouls:
                    if player.rect.colliderect(ghoul.rect):
                        direction = 1 if player.rect.centerx >= ghoul.rect.centerx else -1
                        if player.take_damage(GHOUL_CONTACT_DAMAGE):
                            player.apply_knockback(direction)  # NEW

            camera.update(player.rect)

            # ---------- Check for level-up ----------
            if not player.is_dead and coins >= xp_to_next_level:
                game_paused_for_levelup = True
                levelup_sound.play() 
        # ── Render to canvas ─────────────────────────────────────────────────

        canvas.fill((0, 0, 0))

        draw_background(canvas, camera)

        for (r, c), img in tile_map.items():
            canvas.blit(
                pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)),
                camera.apply(
                    pygame.Rect(
                        c * TILE_SIZE,
                        r * TILE_SIZE,
                        TILE_SIZE,
                        TILE_SIZE
                    )
                )
            )

        for enemy in enemies:
            enemy.draw(canvas, camera)

        for ghoul in ghouls:
            ghoul.draw(canvas, camera)

        player.draw(canvas, camera)
        for tonic in tonics:
            tonic.draw(canvas, camera)

        for drop in drops:
            drop.draw(canvas, camera)

        coin_hud = font.render(f"Experience: {coins} \n Level: {PLAYER_LEVEL}", True, (255, 215, 0))
        canvas.blit(coin_hud, (12, 152))

        # ---------- Tonic Pickup Instruction ----------

        for tonic in tonics:
            if not tonic.collected and tonic.near_player(player):
                pickup_text = font.render(
                    "Press U to pick up",
                    True,
                    (255, 255, 255)
                )

                canvas.blit(pickup_text, (12, 40))

        # ---------- Tonic Acquisition Message ----------

        if tonic_message_timer > 0:
            tonic_message_timer -= 1

            message = font.render(
                tonic_message,
                True,
                (255, 255, 255)
            )

            canvas.blit(message, (12, 68))

        # ---------- Existing HUD ----------

        hud = font.render(
            f"pos: ({player.rect.x}, {player.rect.y})   zone x: {int(camera.x)}",
            True, (220, 220, 220)
        )

        canvas.blit(hud, (12, 12))

        # ---------- Player health bar ----------
        bar_x, bar_y = 12, 120
        bar_w, bar_h = 300, 26

        pygame.draw.rect(canvas, (60, 60, 60), (bar_x, bar_y, bar_w, bar_h))  # background

        health_ratio = player.health / player.max_health
        fill_w = int(bar_w * health_ratio)
        if health_ratio > 0.5:
            fill_color = (60, 200, 60)
        elif health_ratio > 0.25:
            fill_color = (230, 200, 40)
        else:
            fill_color = (200, 50, 50)

        pygame.draw.rect(canvas, fill_color, (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(canvas, (230, 230, 230), (bar_x, bar_y, bar_w, bar_h), 2)  # border

        hp_text = font.render(f"{player.health}/{player.max_health}", True, (255, 255, 255))
        canvas.blit(hp_text, (bar_x + bar_w + 10, bar_y + 3))

        # ---------- Level Up ----------
        if game_paused_for_levelup:
            overlay = pygame.Surface((NATIVE_W, NATIVE_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            canvas.blit(overlay, (0, 0))

            title_font = pygame.font.SysFont("monospace", 60, bold=True)
            title = title_font.render("LEVEL UP!", True, (255, 215, 0))
            canvas.blit(title, title.get_rect(center=(NATIVE_W // 2, NATIVE_H // 2 - 80)))

            opt_font = pygame.font.SysFont("monospace", 30)
            opt1 = opt_font.render("Press 1 - Increase Health", True, (255, 255, 255))
            opt2 = opt_font.render("Press 2 - Increase Damage", True, (255, 255, 255))
            canvas.blit(opt1, opt1.get_rect(center=(NATIVE_W // 2, NATIVE_H // 2)))
            canvas.blit(opt2, opt2.get_rect(center=(NATIVE_W // 2, NATIVE_H // 2 + 50)))

        # ---------- Game Over ----------
        if player.is_dead:
            game_over_font = pygame.font.SysFont("monospace", 80, bold=True)
            text = game_over_font.render("GAME OVER", True, (220, 30, 30))
            text_rect = text.get_rect(center=(NATIVE_W // 2, NATIVE_H // 2))
            canvas.blit(text, text_rect)

            sub_font = pygame.font.SysFont("monospace", 28)
            sub = sub_font.render("Press R to restart or ESC to quit", True, (230, 230, 230))
            sub_rect = sub.get_rect(center=(NATIVE_W // 2, NATIVE_H // 2 + 70))
            canvas.blit(sub, sub_rect)
        # ── Scale canvas → fullscreen monitor
        scaled = pygame.transform.scale(canvas, (MONITOR_W, MONITOR_H))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
