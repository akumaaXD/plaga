import pygame
import sys
import os
import random
import math
import json
import hashlib

try:
    import mysql.connector
except ImportError:
    mysql = None  

# ── Constants ────────────────────────────────────────────────────────────────
NATIVE_W, NATIVE_H = 1920, 1080  # internal render resolution (matches bg art)
TILE_SIZE = 90
FPS = 60
GRAVITY = 0.7
JUMP_FORCE = -22
MOVE_SPEED = 9
CAMERA_LERP = 0.08  # lower = more lag bwteen input and camera movement
ATTACK_COOLDOWN = 0.06
# Colours these are placeholders
SKY_COLOR = (30, 30, 46)
WALL_COLOR = (80, 80, 110)
WALL_EDGE_COLOR = (110, 110, 150)

# Mayank code constants
# Combat constants
DAMAGE_MULTIPLIER = 1
BASE_ATTACK_DAMAGE = 10
ATTACK_DAMAGE = BASE_ATTACK_DAMAGE * DAMAGE_MULTIPLIER
ATTACK_RANGE = 100  # reach of the sword hitbox, in px
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

# ── MySQL connection settings ─────────────────────────────────────────────────
# Fill these in for your own MySQL server. The database itself and its tables
# are created automatically the first time the game runs (see init_db()).
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",          # <-- put your MySQL password here
    "database": "plaga_game",
}

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
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1.1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,3,0,0,0,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,1,0,1,1,1,1,1,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,2,0,0,0,5,0,0,2,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,3,0,0,0,0,0,0,3,0,0,0,0,0,1],
    [1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,0,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,1,1,0,0,0,0,0,1,1,1,1,0,0,0,1,1,1,1,1,1,0,0,0,0,0,0,0,2,3,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,1,1],
    [1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,3,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,1,0,0,0,0,1,1,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,1,0,8,0,0,0,1,1,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,1,1,1,1,1,1,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,1,1,1,0,0,0,1,0,0,2,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,2,0,0,1,1,1,1,1,0,0,0,1,1,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,3,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,1,1,1,0,1,0,0,0,0,0,0,0,1,1,1,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,1],
    [1,1,1,1,1,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,1,1,0,0,0,1,0,0,0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,3,0,0,0,0,0,3,0,2,1,1,1,1,0,0,0,3,0,0,0,2,0,0,1,0,0,1,1],
    [1,1,1,1,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,0,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,0,0,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,1,1],
    [1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,1,1,1,1,1,1,0,0,0,0,0,1,1,1,0,0,0,0,0,0,1,0,0,1,1,0,0,0,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,2,0,0,0,1,0,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,1,1,1,0,0,1,0,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,1,1,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,1,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,1,1,1,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,1,0,1,1,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,1,1,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,1,0,0,0,0,0,3,0,0,0,3,0,0,0,3,0,0,0,1,1,1,1,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,1,0,0,0,2,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,2,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,2,0,0,0,2,0,0,0,2,0,0,0,0,1,1,0,0,3,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,1,1,1,1,0,0,1,1,0,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,1,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1],
    [1,0,0,0,0,0,1,0,0,1,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,0,2,1,0,0,0,0,0,0,0,0,0,2,0,0,0,0,1,0,0,2,0,0,0,0,2,0,0,0,1,1,0,0,0,0,2,0,0,0,3,0,2,0,0,3,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,0,0,0,1,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
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
                r == 0
                or GRID[r - 1][c] in (0, 2, 3, 5,8,9)
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
    wolf_spawns = []
    boss_spawns = []

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

            elif cell == 5:
                wolf_spawns.append((x, y))

            elif cell == 9:
                boss_spawns.append((x, y))

    return (
        normal_spawns,
        ghoul_spawns,
        tonic_spawns,
        wolf_spawns,
        boss_spawns
    )

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
        self.attack_cooldown_timer = 0

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

        if self.attack_cooldown_timer > 0:
            return

        self.attacking = True
        sword_sound.play()

        self.attack_frame = 0
        self.attack_timer = 0

        self.attack_combo = 1 - self.attack_combo

        self.hit_this_swing = set()
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

                if self.attack_frame >= 3:
                    self.attacking = False
                    self.attack_frame = 0
                    self.attack_cooldown_timer = ATTACK_COOLDOWN

            # ---------- Slash Animation ----------

            if self.attack_combo == 0:
                attack_frames = self.attack_left  # left-hand slash
            else:
                attack_frames = self.attack_right  # right-hand slash
            SLASH_SCALE = 1.7  # Increase this to make it bigger

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

        # ---------- Attack cooldown ----------
        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer -= dt

            if self.attack_cooldown_timer < 0:
                self.attack_cooldown_timer = 0

        if not self.is_dead:

            if self.knockback_timer > 0:
                self.knockback_timer -= dt
                self.vel_x *= KNOCKBACK_FRICTION

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
    def __init__(self, x, y, image, speed=2, spawn_id=None):
        w, h = TILE_SIZE - 10, TILE_SIZE - 6
        # y passed in is the TOP of the spawn tile; snap rect bottom to the
        # bottom of that tile (= top of the platform tile below it)
        self.rect = pygame.Rect(x, y + (TILE_SIZE - h), w, h)
        self.speed = speed
        self.direction = 1  # 1 = right, -1 = left
        self.image = pygame.transform.scale(image, (w, h))
        self.spawn_id = spawn_id  # index into normal_spawns, used for save/load

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
# ---------------------------------------------------------
# Boss
# ---------------------------------------------------------

BOSS_SPEED = 8
BOSS_SCALE = 3
BOSS_MAX_HEALTH = ENEMY_MAX_HEALTH * 15


class Boss:

    def __init__(self, x, y, image, spawn_id=None):

        self.spawn_id = spawn_id

        # -----------------------------------------
        # VISIBLE BOSS IMAGE SIZE
        # -----------------------------------------
        image_w = int((TILE_SIZE - 10) * BOSS_SCALE)
        image_h = int((TILE_SIZE - 20) * BOSS_SCALE)

        self.image = pygame.transform.scale(
            image,
            (image_w, image_h)
        )

        # -----------------------------------------
        # INVISIBLE COLLISION HITBOX
        # Shorter than the visible image
        # -----------------------------------------
        hitbox_w = image_w
        hitbox_h = int(image_h * 0.65)

        self.rect = pygame.Rect(
            x,
            y + (TILE_SIZE - hitbox_h),
            hitbox_w,
            hitbox_h
        )

        # -----------------------------------------
        # Keep the visible image at the SAME level
        # -----------------------------------------
        self.image_offset_y = image_h - hitbox_h

        self.speed = BOSS_SPEED
        self.direction = 1

        # Health
        self.max_health = BOSS_MAX_HEALTH
        self.health = self.max_health
        self.alive = True

        # Knockback
        self.knockback_timer = 0.0
        self.knockback_vel_x = 0.0

        self.is_boss = True
        self.ghoul_spawn_timer = random.uniform(3, 8)
    def update(self, walls):

        dt = 1 / FPS

        # Knockback
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

            return

        # Normal patrol movement
        move_x = self.speed * self.direction

        next_rect = self.rect.move(move_x, 0)

        hit_wall = any(
            next_rect.colliderect(w)
            for w in walls
        )

        foot_x = (
            next_rect.right - 1
            if self.direction > 0
            else next_rect.left
        )

        probe = pygame.Rect(
            foot_x,
            self.rect.bottom + 2,
            2,
            4
        )

        ground_ahead = any(
            probe.colliderect(w)
            for w in walls
        )

        if hit_wall or not ground_ahead:
            self.direction *= -1

        else:
            self.rect.x += move_x

    def draw(self, surface, camera):

        img = pygame.transform.flip(
            self.image,
            self.direction > 0,
            False
        )

        boss_rect = self.rect.copy()

        boss_rect.y -= self.image_offset_y

        # YOUR ORIGINAL OFFSET
        boss_rect.y += 15

        surface.blit(
            img,
            camera.apply(boss_rect)
        )
    def take_damage(self, amount):

        if not self.alive:
            return False

        self.health -= amount

        if self.health <= 0:
            self.health = 0
            self.alive = False
            return True

        return False

    def apply_knockback(self, direction):

        self.knockback_vel_x = (
            ENEMY_KNOCKBACK_SPEED * direction*0.7
        )

        self.knockback_timer = (
            ENEMY_KNOCKBACK_DURATION*0.7
        )
class Ghoul:
    DETECTION_RANGE = 700
    SPEED = 5
    SOUND_COOLDOWN = 3.0

    def __init__(self, x, y, image, spawn_id=None):

        w = TILE_SIZE + 100
        h = TILE_SIZE + 100

        self.rect = pygame.Rect(
            x,
            y,
            w,
            h
        )

        # index into ghoul_spawns; ghouls spawned mid-fight by the boss
        # keep this as None so they're just skipped when saving/loading
        self.spawn_id = spawn_id

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

# ---------------------------------------------------------
# Hurt Wolf
# ---------------------------------------------------------

class HurtWolf:

    WOLF_SCALE = 1.5

    def __init__(self, x, y, image):

        w = int(TILE_SIZE * self.WOLF_SCALE*2)
        h = int(TILE_SIZE * self.WOLF_SCALE)

        self.rect = pygame.Rect(
            x,
            y,
            w,
            h
        )

        self.image = pygame.transform.scale(
            image,
            (w, h)
        )

    def draw(self, surface, camera):

        surface.blit(
            self.image,
            camera.apply(self.rect)
        )
class Tonic:
    PICKUP_RANGE = 80

    def __init__(self, x, y, image, spawn_id=None):

        self.rect = pygame.Rect(
            x,
            y,
            TILE_SIZE,
            TILE_SIZE
        )

        self.image = pygame.transform.scale(
            image,
            (int(1 * TILE_SIZE), int(1 * TILE_SIZE))
        )

        self.spawn_id = spawn_id  # index into tonic_spawns, used for save/load
        self.collected = False
        self.used=False

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

        if self.used:
            return

        # Draw using the center of the tonic's rect
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
def show_cover_page(screen, canvas, MONITOR_W, MONITOR_H):
    
    cover = pygame.image.load(
        asset("assets/pragassets/coverpage.jpg")
    ).convert()

    # Canvas dimensions
    canvas_w = NATIVE_W
    canvas_h = NATIVE_H

    # Keep aspect ratio while making the image fill the canvas
    image_w, image_h = cover.get_size()

    scale = max(
        canvas_w / image_w,
        canvas_h / image_h
    )

    new_w = int(image_w * scale)
    new_h = int(image_h * scale)

    cover = pygame.transform.smoothscale(
        cover,
        (new_w, new_h)
    )

    # Center the image.
    # Anything extending past the canvas edges gets cropped.
    cover_x = (canvas_w - new_w) // 2
    cover_y = (canvas_h - new_h) // 2

    canvas.fill((0, 0, 0))
    canvas.blit(
        cover,
        (cover_x, cover_y)
    )

    # Show cover page
    while True:

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_RETURN:
                    return

                if event.key == pygame.K_KP_ENTER:
                    return

                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        # Scale canvas to fullscreen
        scaled = pygame.transform.scale(
            canvas,
            (MONITOR_W, MONITOR_H)
        )

        screen.blit(
            scaled,
            (0, 0)
        )

        pygame.display.flip()

def enemies_near_player(player, enemies, ghouls, radius=1000):

    radius_squared = radius * radius

    for enemy in enemies:

        dx = enemy.rect.centerx - player.rect.centerx
        dy = enemy.rect.centery - player.rect.centery

        if dx * dx + dy * dy <= radius_squared:
            return True

    for ghoul in ghouls:

        dx = ghoul.rect.centerx - player.rect.centerx
        dy = ghoul.rect.centery - player.rect.centery

        if dx * dx + dy * dy <= radius_squared:
            return True

    return False


# ── Accounts & save/load (MySQL) ───────────────────────────────────────────────

def _db_connect(with_database=True):
    if mysql is None:
        raise RuntimeError(
            "mysql-connector-python is not installed. "
            "Run: pip install mysql-connector-python"
        )

    config = dict(DB_CONFIG)

    if not with_database:
        config.pop("database", None)

    return mysql.connector.connect(**config)


def init_db():
    """Create the database/tables the first time the game is run. Safe to call every launch."""

    conn = _db_connect(with_database=False)
    cur = conn.cursor()

    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}`"
    )

    conn.commit()
    cur.close()
    conn.close()

    conn = _db_connect(with_database=True)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            salt VARCHAR(64) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # One save slot per account. state_json holds everything needed to
    # put the player back exactly where they rested.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS saves (
            user_id INT PRIMARY KEY,
            state_json LONGTEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cur.close()
    conn.close()


def hash_password(password, salt_hex=None):
    """PBKDF2-SHA256 password hashing. Returns (hash_hex, salt_hex)."""

    if salt_hex is None:
        salt_hex = os.urandom(16).hex()

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        100_000
    ).hex()

    return digest, salt_hex


def create_user(username, password):
    """Registers a new account. Returns the new user_id, or None if the name is taken."""

    conn = _db_connect()
    cur = conn.cursor()

    try:
        password_hash, salt = hash_password(password)

        cur.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (%s, %s, %s)",
            (username, password_hash, salt)
        )

        conn.commit()
        return cur.lastrowid

    except mysql.connector.IntegrityError:
        return None  # username already exists

    finally:
        cur.close()
        conn.close()


def authenticate_user(username, password):
    """Returns the user_id if the credentials are correct, otherwise None."""

    conn = _db_connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, password_hash, salt FROM users WHERE username = %s",
        (username,)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return None

    user_id, stored_hash, salt = row
    check_hash, _ = hash_password(password, salt)

    if check_hash == stored_hash:
        return user_id

    return None


def save_game_state(user_id, state):
    """Upserts the player's save slot with the current run state (called whenever they rest)."""

    conn = _db_connect()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO saves (user_id, state_json) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE state_json = VALUES(state_json)
        """,
        (user_id, json.dumps(state))
    )

    conn.commit()
    cur.close()
    conn.close()


def load_game_state(user_id):
    """Returns the saved state dict for this account, or None if they've never rested yet."""

    conn = _db_connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT state_json FROM saves WHERE user_id = %s",
        (user_id,)
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        return None

    return json.loads(row[0])


def build_save_state(player, enemies, ghouls, tonics, coins,
                      xp_to_next_level, has_rested_once, game_won,
                      normal_spawns, boss_spawns, ghoul_spawns):
    """Packs everything needed to resume the run into a JSON-able dict."""

    alive_normal_ids = {
        e.spawn_id for e in enemies
        if not getattr(e, "is_boss", False)
    }
    defeated_normal_ids = [
        i for i in range(len(normal_spawns))
        if i not in alive_normal_ids
    ]

    boss = next((e for e in enemies if getattr(e, "is_boss", False)), None)
    boss_defeated = boss is None and len(boss_spawns) > 0
    boss_health = boss.health if boss else None

    alive_ghoul_ids = {
        g.spawn_id for g in ghouls
        if getattr(g, "spawn_id", None) is not None
    }
    defeated_ghoul_ids = [
        i for i in range(len(ghoul_spawns))
        if i not in alive_ghoul_ids
    ]

    return {
        "pos_x": player.rect.x,
        "pos_y": player.rect.y,
        "facing": player.facing,
        "health": player.health,
        "max_health": player.max_health,
        "coins": coins,
        "player_level": PLAYER_LEVEL,
        "health_multiplier": HEALTH_MULTIPLIER,
        "damage_multiplier": DAMAGE_MULTIPLIER,
        "xp_to_next_level": xp_to_next_level,
        "has_rested_once": has_rested_once,
        "defeated_normal_ids": defeated_normal_ids,
        "boss_defeated": boss_defeated,
        "boss_health": boss_health,
        "defeated_ghoul_ids": defeated_ghoul_ids,
        "tonic_collected_ids": [t.spawn_id for t in tonics if t.collected],
        "tonic_used_ids": [t.spawn_id for t in tonics if t.used],
        "game_won": game_won,
    }


def apply_save_state(state, player, enemies, ghouls, tonics, wolves):
    """Restores a run from a previously saved state dict. Returns
    (coins, xp_to_next_level, has_rested_once, game_won)."""

    global PLAYER_LEVEL, HEALTH_MULTIPLIER, DAMAGE_MULTIPLIER, ATTACK_DAMAGE

    player.rect.x = state["pos_x"]
    player.rect.y = state["pos_y"]
    player.facing = state.get("facing", player.facing)
    player.flip = player.facing == "left"
    player.max_health = state["max_health"]
    player.health = state["health"]

    PLAYER_LEVEL = state["player_level"]
    HEALTH_MULTIPLIER = state["health_multiplier"]
    DAMAGE_MULTIPLIER = state["damage_multiplier"]
    ATTACK_DAMAGE = BASE_ATTACK_DAMAGE * DAMAGE_MULTIPLIER

    defeated_normal_ids = set(state.get("defeated_normal_ids", []))
    enemies[:] = [
        e for e in enemies
        if getattr(e, "is_boss", False) or e.spawn_id not in defeated_normal_ids
    ]

    if state.get("boss_defeated"):
        enemies[:] = [e for e in enemies if not getattr(e, "is_boss", False)]
    elif state.get("boss_health") is not None:
        for e in enemies:
            if getattr(e, "is_boss", False):
                e.health = state["boss_health"]

    defeated_ghoul_ids = set(state.get("defeated_ghoul_ids", []))
    ghouls[:] = [
        g for g in ghouls
        if getattr(g, "spawn_id", None) is None or g.spawn_id not in defeated_ghoul_ids
    ]

    collected_ids = set(state.get("tonic_collected_ids", []))
    used_ids = set(state.get("tonic_used_ids", []))

    for t in tonics:
        if t.spawn_id in used_ids:
            t.used = True
            t.collected = False
        elif t.spawn_id in collected_ids:
            t.collected = True

    if state.get("has_rested_once"):
        wolves.clear()

    return (
        state["coins"],
        state["xp_to_next_level"],
        state.get("has_rested_once", False),
        state.get("game_won", False),
    )


def show_login_page(screen, canvas, MONITOR_W, MONITOR_H):
    """Simple username/password screen with a Login/Sign Up toggle. Blocks until the
    player is authenticated, then returns (user_id, username)."""

    title_font = pygame.font.SysFont("monospace", 64, bold=True)
    label_font = pygame.font.SysFont("monospace", 28)
    input_font = pygame.font.SysFont("monospace", 30)
    small_font = pygame.font.SysFont("monospace", 22)

    mode = "login"  # or "signup"
    username_text = ""
    password_text = ""
    active_field = "username"
    error_message = ""

    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if event.key == pygame.K_TAB:
                    active_field = "password" if active_field == "username" else "username"
                    continue

                if event.key == pygame.K_s and (event.mod & pygame.KMOD_CTRL):
                    mode = "signup" if mode == "login" else "login"
                    error_message = ""
                    continue

                if event.key == pygame.K_BACKSPACE:
                    if active_field == "username":
                        username_text = username_text[:-1]
                    else:
                        password_text = password_text[:-1]
                    continue

                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):

                    clean_user = username_text.strip()

                    if not clean_user or not password_text:
                        error_message = "Enter both a username and password"
                        continue

                    try:
                        if mode == "login":
                            user_id = authenticate_user(clean_user, password_text)

                            if user_id is None:
                                error_message = "Wrong username or password"
                            else:
                                return user_id, clean_user

                        else:
                            user_id = create_user(clean_user, password_text)

                            if user_id is None:
                                error_message = "That username is already taken"
                            else:
                                return user_id, clean_user

                    except Exception as e:
                        error_message = f"Database error: {e}"

                    continue

                # Regular typing
                if active_field == "username":
                    if len(username_text) < 24 and event.unicode.isprintable():
                        username_text += event.unicode
                else:
                    if len(password_text) < 32 and event.unicode.isprintable():
                        password_text += event.unicode

        # ---------------- Draw ----------------
        canvas.fill((18, 18, 28))

        title = title_font.render("PLAGA", True, (230, 200, 60))
        canvas.blit(title, title.get_rect(center=(NATIVE_W // 2, 160)))

        mode_text = label_font.render(
            "SIGN UP" if mode == "signup" else "LOG IN",
            True, (200, 200, 220)
        )
        canvas.blit(mode_text, mode_text.get_rect(center=(NATIVE_W // 2, 240)))

        box_w, box_h = 520, 56
        box_x = NATIVE_W // 2 - box_w // 2

        # Username box
        user_box_y = 340
        user_active = active_field == "username"
        pygame.draw.rect(canvas, (40, 40, 60), (box_x, user_box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(
            canvas,
            (230, 200, 60) if user_active else (90, 90, 120),
            (box_x, user_box_y, box_w, box_h), 3, border_radius=8
        )
        canvas.blit(small_font.render("Username", True, (160, 160, 180)), (box_x, user_box_y - 28))
        canvas.blit(input_font.render(username_text, True, (240, 240, 240)), (box_x + 14, user_box_y + 13))

        # Password box
        pass_box_y = 430
        pass_active = active_field == "password"
        pygame.draw.rect(canvas, (40, 40, 60), (box_x, pass_box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(
            canvas,
            (230, 200, 60) if pass_active else (90, 90, 120),
            (box_x, pass_box_y, box_w, box_h), 3, border_radius=8
        )
        canvas.blit(small_font.render("Password", True, (160, 160, 180)), (box_x, pass_box_y - 28))
        canvas.blit(
            input_font.render("*" * len(password_text), True, (240, 240, 240)),
            (box_x + 14, pass_box_y + 13)
        )

        if error_message:
            err_surf = small_font.render(error_message, True, (230, 80, 80))
            canvas.blit(err_surf, err_surf.get_rect(center=(NATIVE_W // 2, 520)))

        info_surf = small_font.render(
            "TAB to switch fields   ENTER to submit",
            True, (140, 140, 160)
        )
        canvas.blit(info_surf, info_surf.get_rect(center=(NATIVE_W // 2, 580)))

        toggle_hint = small_font.render(
            "Don't have an account? Ctrl+S to Sign Up"
            if mode == "login" else
            "Already have an account? Ctrl+S to Log In",
            True, (140, 140, 160)
        )
        canvas.blit(toggle_hint, toggle_hint.get_rect(center=(NATIVE_W // 2, 610)))

        scaled = pygame.transform.scale(canvas, (MONITOR_W, MONITOR_H))
        screen.blit(scaled, (0, 0))
        pygame.display.flip()
        clock.tick(FPS)


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
    show_cover_page(
        screen,
        canvas,
        MONITOR_W,
        MONITOR_H
    )

    # ---------------- Account / save system ----------------
    db_available = True

    try:
        init_db()
    except Exception as e:
        print(f"Warning: could not reach MySQL ({e}). Playing without login/save.")
        db_available = False

    if db_available:
        user_id, username = show_login_page(screen, canvas, MONITOR_W, MONITOR_H)
    else:
        user_id, username = None, "Guest"

    clock = pygame.time.Clock()

    # Load assets
    load_bg_images()
    load_sounds()
    try:
        
        
        idle = pygame.image.load(
            asset("assets/pragassets/plaga_standing.png")
        ).convert_alpha()
        enemy_img = pygame.image.load(
                asset("assets/pragassets/enemy.png")
        ).convert_alpha()

        coin_image = pygame.image.load(
            asset("assets/pragassets/coin.png")
        ).convert_alpha()

        walk_frames = []

        for i in range(1, 8):
            walk_frames.append(

                pygame.image.load(
                    asset(f"assets/pragassets/praga_moving_{i}.png")
                ).convert_alpha()

            )

        attack1 = []

        for i in range(1, 4):
            attack1.append(

                pygame.image.load(
                    asset(f"assets/pragassets/praga_attack_{i}.png")
                ).convert_alpha()

            )

        attack2 = []

        for i in range(1, 4):
            attack2.append(pygame.image.load(asset(f"assets/pragassets/praga_attackr_{i}.png")).convert_alpha())
            ghoul_image = pygame.image.load(asset("assets/pragassets/ghoul.png")).convert_alpha()
            tonic_image = pygame.image.load(asset("assets/pragassets/toniic.png")).convert_alpha()
            wolf_image = pygame.image.load(asset("assets/pragassets/doggohurt.png")).convert_alpha()
            boss_image = pygame.image.load(asset("assets/pragassets/plagboss.png")).convert_alpha()
            rest_image = pygame.image.load(asset("assets/pragassets/dogorest.png")).convert_alpha()

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

    normal_spawns, ghoul_spawns, tonic_spawns, wolf_spawns,boss_spawns = build_enemy_spawns()

    enemies = [
        Enemy(x, y, enemy_img, spawn_id=i)
        for i, (x, y) in enumerate(normal_spawns)
    ]

    # Add bosses to the same enemy list
    enemies += [
        Boss(x, y, boss_image, spawn_id=i)
        for i, (x, y) in enumerate(boss_spawns)
    ]

    ghouls = [
        Ghoul(x, y, ghoul_image, spawn_id=i)
        for i, (x, y) in enumerate(ghoul_spawns)
    ]
    tonics = [
        Tonic(x, y, tonic_image, spawn_id=i)
        for i, (x, y) in enumerate(tonic_spawns)
    ]
    wolves = [
        HurtWolf(x, y, wolf_image)
        for x, y in wolf_spawns
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
    instruction_font = pygame.font.SysFont("monospace", 36, bold=True)
    tonic_message = ""
    tonic_message_timer = 0
    resting = False

    # enemy drops
    drops = []
    game_paused_for_levelup = False

    # ---------------- Load saved progress, if any ----------------
    coins = 0
    xp_to_next_level = COIN_DROP_MAX * 5 - 2
    has_rested_once = False
    game_won = False

    # Tracks the last spot the player rested at (or the DB save that was
    # loaded at startup, if any), so dying and pressing R sends the player
    # back there instead of the very start of the level.
    last_checkpoint = None

    if db_available and user_id is not None:
        try:
            saved_state = load_game_state(user_id)
        except Exception as e:
            print(f"Warning: could not load save ({e})")
            saved_state = None

        if saved_state:
            coins, xp_to_next_level, has_rested_once, game_won = apply_save_state(
                saved_state, player, enemies, ghouls, tonics, wolves
            )
            camera.x = player.rect.centerx - NATIVE_W / 2
            camera.y = player.rect.centery - NATIVE_H / 2
            last_checkpoint = saved_state

    def save_progress():
        """Snapshots the current run as the checkpoint to respawn at on death,
        and (if an account is logged in) writes it to the MySQL save slot too.
        Called whenever the player rests, AND whenever the boss is defeated —
        that way quitting right after a win doesn't roll the save back to the
        last time they rested."""

        nonlocal last_checkpoint

        state = build_save_state(
            player, enemies, ghouls, tonics, coins,
            xp_to_next_level, has_rested_once, game_won,
            normal_spawns, boss_spawns, ghoul_spawns
        )
        last_checkpoint = state

        if not (db_available and user_id is not None):
            return

        try:
            save_game_state(user_id, state)
        except Exception as e:
            print(f"Warning: could not save progress ({e})")

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
                if event.key == pygame.K_f:
                    # ---------------------------------------------
                    # If already resting -> wake up
                    # ---------------------------------------------
                    if resting:
                        resting = False

                        # Restore normal player sprite
                        player.image = player.idle

                        continue

                    # ---------------------------------------------
                    # Can't rest if enemies/ghouls are nearby
                    # ---------------------------------------------
                    if enemies_near_player(
                        player,
                        enemies,
                        ghouls,
                        1000
                    ):
                        tonic_message = "Too close to enemies to rest"
                        tonic_message_timer = 120
                        continue

                    # ---------------------------------------------
                    # FIRST REST / RESCUE
                    # Must have tonic AND be near hurt wolf
                    # ---------------------------------------------
                    if not has_rested_once:

                        # Check whether player is close enough to wolf
                        near_wolf = False

                        for wolf in wolves:
                            dx = wolf.rect.centerx - player.rect.centerx
                            dy = wolf.rect.centery - player.rect.centery

                            if dx * dx + dy * dy <= 150 * 150:
                                near_wolf = True
                                break

                        # Not close enough to rescue wolf
                        if not near_wolf:
                            tonic_message = "Get closer to the wolf to rescue it"
                            tonic_message_timer = 120
                            continue

                        # Find collected tonic
                        collected_tonic = None

                        for tonic in tonics:
                            if tonic.collected:
                                collected_tonic = tonic
                                break

                        # No tonic yet
                        if collected_tonic is None:
                            tonic_message = "Press U to pick up"
                            tonic_message_timer = 120
                            continue

                        # -----------------------------------------
                        # RESCUE WOLF / USE TONIC
                        # -----------------------------------------
                        collected_tonic.used = True
                        collected_tonic.collected = False

                        # Remove the hurt wolf
                        wolves.clear()

                        # -----------------------------------------
                        # Player can now rest anywhere
                        # -----------------------------------------
                        resting = True
                        has_rested_once = True

                        player.image = rest_image
                        player.current_slash = None
                        player.attacking = False

                        save_progress()

                        continue

                    # ---------------------------------------------
                    # AFTER WOLF HAS BEEN RESCUED
                    # F can now rest anywhere, subject to enemies
                    # ---------------------------------------------
                    resting = True

                    player.image = rest_image
                    player.current_slash = None
                    player.attacking = False

                    save_progress()
                if event.key == pygame.K_r and (player.is_dead or game_won):
                    # NOTE: PLAYER_LEVEL / HEALTH_MULTIPLIER / DAMAGE_MULTIPLIER /
                    # ATTACK_DAMAGE are already declared `global` above (in the
                    # level-up key handlers), so they don't need to be redeclared
                    # here — Python disallows a second `global` statement for a
                    # name that's already been assigned earlier in the function.

                    # Only send the player back to their last rest point if
                    # they actually died mid-run and a checkpoint exists.
                    # Restarting after a WIN (or with no checkpoint yet)
                    # starts a brand new run from the true beginning.
                    respawn_at_checkpoint = (
                        player.is_dead and not game_won and last_checkpoint is not None
                    )

                    # ---------- Rebuild enemies / ghouls / tonics from original spawn points ----------
                    enemies = [
                        Enemy(x, y, enemy_img, spawn_id=i)
                        for i, (x, y) in enumerate(normal_spawns)
                    ]

                    enemies += [
                        Boss(x, y, boss_image, spawn_id=i)
                        for i, (x, y) in enumerate(boss_spawns)
                    ]
                    ghouls = [
                        Ghoul(x, y, ghoul_image, spawn_id=i)
                        for i, (x, y) in enumerate(ghoul_spawns)
                    ]
                    tonics = [
                        Tonic(x, y, tonic_image, spawn_id=i)
                        for i, (x, y) in enumerate(tonic_spawns)
                    ]
                    wolves = [
                        HurtWolf(x, y, wolf_image)
                        for x, y in wolf_spawns
                    ]

                    # ---------- Clear drops ----------
                    drops = []

                    # ---------- Reset player to a clean slate ----------
                    player.is_dead = False
                    player.invuln_timer = 0
                    player.vel_x = 0
                    player.vel_y = 0
                    player.image = player.idle

                    if respawn_at_checkpoint:
                        # Died mid-run: respawn at the last place you rested,
                        # with level/coins/kills/tonics restored to that point.
                        coins, xp_to_next_level, has_rested_once, game_won = apply_save_state(
                            last_checkpoint, player, enemies, ghouls, tonics, wolves
                        )
                    else:
                        # No checkpoint yet, or starting a fresh run after a
                        # win: reset everything back to the true beginning.
                        PLAYER_LEVEL = 1
                        HEALTH_MULTIPLIER = 1
                        DAMAGE_MULTIPLIER = 1
                        ATTACK_DAMAGE = BASE_ATTACK_DAMAGE
                        player.max_health = PLAYER_BASE_MAX_HEALTH
                        player.health = player.max_health
                        player.rect.x = spawn_col * TILE_SIZE + 4
                        player.rect.y = spawn_row * TILE_SIZE - TILE_SIZE
                        coins = 0
                        xp_to_next_level = COIN_DROP_MAX * 5 - 2
                        has_rested_once = False
                        game_won = False
                        last_checkpoint = None

                    camera.x = player.rect.centerx - NATIVE_W / 2
                    camera.y = player.rect.centery - NATIVE_H / 2

                    # ---------- Reset any HUD messages ----------
                    tonic_message = ""
                    tonic_message_timer = 0
                    resting = False

        if game_paused_for_levelup:
            continue

        if not game_paused_for_levelup and not resting and not game_won:

            player.update(wall_rects)

            # ---------- Attack collisions ----------
            hitbox = player.get_attack_hitbox()

            if hitbox:
                for enemy in enemies:

                    if (
                        enemy.alive
                        and id(enemy) not in player.hit_this_swing
                        and hitbox.colliderect(enemy.rect)
                    ):

                        player.hit_this_swing.add(id(enemy))

                        # Deal damage
                        died = enemy.take_damage(ATTACK_DAMAGE)

                        # Knockback
                        direction = (
                            1
                            if enemy.rect.centerx >= player.rect.centerx
                            else -1
                        )

                        enemy.apply_knockback(direction)

                        # -----------------------------------------
                        # BOSS HIT
                        # -----------------------------------------
                        if getattr(enemy, "is_boss", False):

                            # Boss defeated
                            if died:
                                game_won = True
                                save_progress()  # persist the win so reloading doesn't undo it

                        # -----------------------------------------
                        # NORMAL ENEMY DEFEATED
                        # -----------------------------------------
                        elif died:

                            drops.append(
                                Drop(
                                    enemy.rect.centerx,
                                    enemy.rect.centery,
                                    random.randint(
                                        COIN_DROP_MIN,
                                        COIN_DROP_MAX
                                    ),
                                    coin_image
                                )
                            )
                for ghoul in ghouls:
                    if (
                        ghoul.alive
                        and id(ghoul) not in player.hit_this_swing
                        and hitbox.colliderect(ghoul.rect)
                    ):
                        player.hit_this_swing.add(id(ghoul))

                        died = ghoul.take_damage(ATTACK_DAMAGE)

                        dx = ghoul.rect.centerx - player.rect.centerx
                        dy = ghoul.rect.centery - player.rect.centery

                        ghoul.apply_knockback(dx, dy)

                        if died:
                            drops.append(
                                Drop(
                                    ghoul.rect.centerx,
                                    ghoul.rect.centery,
                                    random.randint(
                                        COIN_DROP_MIN + 2,
                                        COIN_DROP_MAX + 3
                                    ),
                                    coin_image
                                )
                            )

            # ---------- Clear dead enemies ----------
            enemies = [e for e in enemies if e.alive]
            ghouls = [g for g in ghouls if g.alive]

            # ---------- Update enemies ----------
            # ---------- Update enemies ----------
            for enemy in enemies:
                enemy.update(wall_rects)

                if getattr(enemy, "is_boss", False):

                    if enemy.health <= enemy.max_health * 0.5:

                        enemy.ghoul_spawn_timer -= 1 / FPS

                        if enemy.ghoul_spawn_timer <= 0:

                            ghoul_x = (
                                enemy.rect.centerx
                                + random.randint(-80, 80)
                            )

                            ghoul_y = (
                                enemy.rect.top
                                - random.randint(50, 100)
                            )

                            ghouls.append(
                                Ghoul(
                                    ghoul_x,
                                    ghoul_y,
                                    ghoul_image
                                )
                            )

                            # Next ghoul in 3–7 seconds
                            enemy.ghoul_spawn_timer = random.uniform(3, 7)

            for ghoul in ghouls:
                ghoul.update(player)

            for tonic in tonics:
                tonic.update(player)

            # ---------- Drops ----------
            for drop in drops:
                drop.update(player)

            coins += sum(
                d.value
                for d in drops
                if d.collected
            )

            if player.health >= player.max_health:
                player.health = player.max_health

            drops = [
                d for d in drops
                if not d.collected
            ]

            # ---------- Deal damage to player ----------
            if not player.is_dead:

                for enemy in enemies:
                    if player.rect.colliderect(enemy.rect):

                        direction = (
                            1
                            if player.rect.centerx >= enemy.rect.centerx
                            else -1
                        )

                        if player.take_damage(ENEMY_CONTACT_DAMAGE):
                            player.apply_knockback(direction)

                for ghoul in ghouls:
                    if player.rect.colliderect(ghoul.rect):

                        direction = (
                            1
                            if player.rect.centerx >= ghoul.rect.centerx
                            else -1
                        )

                        if player.take_damage(GHOUL_CONTACT_DAMAGE):
                            player.apply_knockback(direction)

            camera.update(player.rect)

            # ---------- Check for level-up ----------
            if not player.is_dead and coins >= xp_to_next_level:
                game_paused_for_levelup = True
                levelup_sound.play()
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

            # ---------- BOSS ENRAGED INDICATOR ----------
            if (
                getattr(enemy, "is_boss", False)
                and enemy.health <= enemy.max_health * 0.5
            ):

                enraged_font = pygame.font.SysFont(
                    "monospace",
                    28,
                    bold=True
                )

                enraged_text = enraged_font.render(
                    "ENRAGED!",
                    True,
                    (255, 60, 60)
                )

                # Position the text above the boss
                world_pos = pygame.Rect(
                    enemy.rect.centerx - enraged_text.get_width() // 2,
                    enemy.rect.top - 40,
                    enraged_text.get_width(),
                    enraged_text.get_height()
                )

                screen_rect = camera.apply(world_pos)

                canvas.blit(
                    enraged_text,
                    screen_rect
                )

        for ghoul in ghouls:
            ghoul.draw(canvas, camera)

        for ghoul in ghouls:
            ghoul.draw(canvas, camera)
        for wolf in wolves:
            wolf.draw(canvas, camera)

        player.draw(canvas, camera)
        for tonic in tonics:
            tonic.draw(canvas, camera)

        for drop in drops:
            drop.draw(canvas, camera)

        coin_hud = font.render(f"Experience: {coins} \n Level: {PLAYER_LEVEL}", True, (255, 215, 0))
        canvas.blit(coin_hud, (12, 152))

        # ---------- Tonic Pickup Instruction ----------

        # ---------- LARGE GAME INSTRUCTIONS ----------

        instruction_y = 40

        # Tonic pickup instruction
        for tonic in tonics:
            if not tonic.collected and not tonic.used and tonic.near_player(player):
                pickup_text = instruction_font.render(
                    "Press U to pick up",
                    True,
                    (255, 255, 255)
                )

                canvas.blit(pickup_text, (12, instruction_y))
                instruction_y += 40
                break


                # Rest instruction
                # ---------- Rest Instruction ----------

        # Before the wolf is rescued:
        # Only show "Press F to rest" when the player
        # is close to the hurt wolf.
        #
        # After the wolf is rescued:
        # Show it anywhere.

        near_wolf = False

        for wolf in wolves:
            dx = wolf.rect.centerx - player.rect.centerx
            dy = wolf.rect.centery - player.rect.centery

            if dx * dx + dy * dy <= 150 * 150:
                near_wolf = True
                break


        if not resting and (near_wolf or has_rested_once):

            rest_text = instruction_font.render(
                "Press F to rest",
                True,
                (255, 255, 255)
            )

            canvas.blit(
                rest_text,
                (12, instruction_y)
            )

            instruction_y += 40


        # Message such as:
        # "Too close to enemies to rest"
        # "Press U to pick up"
        if tonic_message_timer > 0:
            tonic_message_timer -= 1

            message = instruction_font.render(
                tonic_message,
                True,
                (255, 255, 255)
            )

            canvas.blit(message, (12, instruction_y))

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

        
        # ---------- YOU WON ----------
        if game_won:

            overlay = pygame.Surface(
                (NATIVE_W, NATIVE_H),
                pygame.SRCALPHA
            )

            overlay.fill((0, 0, 0, 190))
            canvas.blit(overlay, (0, 0))

            win_font = pygame.font.SysFont(
                "monospace",
                120,
                bold=True
            )

            win_text = win_font.render(
                "U WON",
                True,
                (255, 215, 0)
            )

            win_rect = win_text.get_rect(
                center=(
                    NATIVE_W // 2,
                    NATIVE_H // 2 - 60
                )
            )

            canvas.blit(
                win_text,
                win_rect
            )

            win_sub_font = pygame.font.SysFont(
                "monospace",
                32
            )

            win_sub = win_sub_font.render(
                "Press R to reset or ESC to quit",
                True,
                (255, 255, 255)
            )

            win_sub_rect = win_sub.get_rect(
                center=(
                    NATIVE_W // 2,
                    NATIVE_H // 2 + 70
                )
            )

            canvas.blit(
                win_sub,
                win_sub_rect
            )
            #game over
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
