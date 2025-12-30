from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import math
import random
import time

# ===== Global Variables =====
window_width = 800
window_height = 600

# Player variables
player_x, player_z = 0.0, 0.0
player_angle = 0.0  # Gun rotation
player_speed = 0.2

# Camera variables
cam_angle = 270.0
cam_height = 6.0
first_person = False

# Third-person follow camera 
cam_distance = 6.0        
cam_follow_height = 3.0  
cam_smooth = 0.12         
# current camera position state 
cam_x, cam_y, cam_z = 0.0, 3.0, 6.0

# Game state
life = 100
score = 0
misses = 0
game_over = False
cheat_mode = False
auto_follow = False

# Timing
start_time = None      
survival_time = None    

def end_game():
    """Mark game over and record survival_time once."""
    global game_over, survival_time, start_time
    if not game_over:
        game_over = True
        if start_time is not None and survival_time is None:
            survival_time = time.time() - start_time

# Bullets and enemies
bullets = []
enemies = []
enemy_bullets = []         
health_kits = []           
bombs = []                
mines = []                

# Constants
MAX_ENEMIES = 5
GRID_MIN = -15
GRID_MAX = 15
ENEMY_SPEED = 0.001  # Tuned speed for visible, smooth enemy movement
ENEMY_SHOOT_RANGE = 8.0   # when player within this range, enemy may fire
ENEMY_BULLET_SPEED = 0.25
ENEMY_MIN_COOLDOWN = 1.2
ENEMY_MAX_COOLDOWN = 3.0
MINES_COUNT = 6 

# Maze data 
MAZE_W = 0
MAZE_H = 0

# Checkpoints 
TOTAL_CHECKPOINTS = 5
checkpoints = []        
checkpoints_found = 0
final_checkpoint = None
final_checkpoint_active = False


aggressive_enemies = False


freeze_enemies = False

top_view = False

def place_checkpoints():
    
    global checkpoints, checkpoints_found
    checkpoints = []
    checkpoints_found = 0
    if not MAZE:
        return
    px_idx = int((player_x - GRID_MIN))
    pz_idx = int((player_z - GRID_MIN))
    free_cells = []
    for j in range(1, MAZE_H-1):
        for i in range(1, MAZE_W-1):
            if MAZE[j][i] != 0: continue
            
            if abs(i-px_idx) <= 2 and abs(j-pz_idx) <= 2: continue
            
            neigh_walls = 0
            for di,dj in ((1,0),(-1,0),(0,1),(0,-1)):
                ni, nj = i+di, j+dj
                if 0<=ni<MAZE_W and 0<=nj<MAZE_H and MAZE[nj][ni]==1:
                    neigh_walls += 1
            if neigh_walls >= 1:
                free_cells.append((i,j))
    random.shuffle(free_cells)
    for idx in range(min(TOTAL_CHECKPOINTS, len(free_cells))):
        i,j = free_cells[idx]
        wx = GRID_MIN + i + 0.5
        wz = GRID_MIN + j + 0.5
        checkpoints.append({'i':i,'j':j,'x':wx,'z':wz})

def is_wall(x, z):

    ix = int(math.floor(x - GRID_MIN))
    iz = int(math.floor(z - GRID_MIN))
    if ix < 0 or iz < 0 or ix >= MAZE_W or iz >= MAZE_H:
        return False
    return MAZE[iz][ix] == 1

def draw_maze():
    
    if not MAZE:
        return
    wall_color = (0.6, 0.2, 0.15)  # Brick wall color
    wall_height = 2.0
    wall_thickness = 0.15  

    for j in range(MAZE_H):
        for i in range(MAZE_W):
            wx = GRID_MIN + i
            wz = GRID_MIN + j

            if i == 0 or j == 0 or i == MAZE_W - 1 or j == MAZE_H - 1:
                # Draw boundary wall at the edges of the grid
                glColor3f(*wall_color)
                glPushMatrix()
                glTranslatef(wx + 0.5, wall_height / 2 - 0.9, wz + 0.5)  
                glScalef(1.0, wall_height, 1.0)
                glutSolidCube(1)
                glPopMatrix()
            elif MAZE[j][i] == 1:
                # Draw interior maze walls
                glColor3f(*wall_color)
                # North-South facing wall
                glPushMatrix()
                glTranslatef(wx + 0.5, wall_height / 2 - 0.9, wz + 1.0)  
                glScalef(1.0, wall_height, wall_thickness)
                glutSolidCube(1)
                glPopMatrix()
                # East-West facing wall
                glPushMatrix()
                glTranslatef(wx, wall_height / 2 - 0.9, wz + 0.5)  
                glScalef(wall_thickness, wall_height, 1.0)
                glutSolidCube(1)
                glPopMatrix()


def draw_checkpoints():
   
    if cheat_mode:
        glDisable(GL_DEPTH_TEST)  
    glColor3f(0.0, 1.0, 1.0)
    for cp in checkpoints:
        glPushMatrix()
        glTranslatef(cp['x'], 0.4, cp['z'])
        glutSolidSphere(0.25, 12, 12)
        glPopMatrix()
    if cheat_mode:
        glEnable(GL_DEPTH_TEST) 
def draw_final_checkpoint():

    global final_checkpoint, final_checkpoint_active
    if not final_checkpoint_active or final_checkpoint is None:
        return
    if cheat_mode:
        glDisable(GL_DEPTH_TEST)
    glColor3f(1.0, 0.8, 0.0)  # Gold/yellow
    glPushMatrix()
    glTranslatef(final_checkpoint['x'], 0.5, final_checkpoint['z'])
    glutSolidSphere(0.35, 16, 16)
    glPopMatrix()
    if cheat_mode:
        glEnable(GL_DEPTH_TEST)

# Add health to each enemy
def spawn_enemies():
    global enemies
    enemies = []
    for _ in range(MAX_ENEMIES):
        ex, ez = random.uniform(GRID_MIN+1, GRID_MAX-1), random.uniform(GRID_MIN+1, GRID_MAX-1)
        enemies.append({
            'x': ex,
            'z': ez,
            'scale': 0.3,
            'scale_dir': 1,
            'last_shot': 0.0,
            'cooldown': random.uniform(ENEMY_MIN_COOLDOWN, ENEMY_MAX_COOLDOWN),
            'health': 2  # Each enemy starts with 2 health
        })

def dist2D(x1, z1, x2, z2):
    return math.sqrt((x1-x2)**2 + (z1-z2)**2)

def draw_grid():
    white = (1, 1, 1)
    black = (0.5, 0.5, 0.5)
    cell_size = 1

    for i in range(GRID_MIN, GRID_MAX):
        for j in range(GRID_MIN, GRID_MAX):
            if (i + j) % 2 == 0:
                glColor3f(*white)
            else:
                glColor3f(*black)

            glBegin(GL_QUADS)
            glVertex3f(i, -0.5, j)
            glVertex3f(i + cell_size, -0.5, j)
            glVertex3f(i + cell_size, -0.5, j + cell_size)
            glVertex3f(i, -0.5, j + cell_size)
            glEnd()



def draw_player():
    glPushMatrix()
   
    if game_over:
        
        glTranslatef(player_x, 0.1, player_z)        
        glRotatef(player_angle, 0, 1, 0)            
        glRotatef(270, 1, 0, 0)                      
    else:
        glTranslatef(player_x, 0.5, player_z)
        glRotatef(player_angle, 0, 1, 0)

    # Legs
    glColor3f(0.0, 0.0, 1.0)
    for offset in [-0.15, 0.15]:
        glPushMatrix()
        glTranslatef(offset, -0.5, 0)
        glRotatef(90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 0.1, 0.1, 0.6, 15, 15)
        glPopMatrix()

    # Body
    glColor3f(0.0, 0.5, 0.0)
    glPushMatrix()
    glTranslatef(0, 0.2, 0)
    glScalef(0.5, 0.8, 0.3)
    glutSolidCube(1)
    glPopMatrix()

    # Head
    glColor3f(0,0,0)
    glPushMatrix()
    glTranslatef(0, 0.9, 0)
    gluSphere(gluNewQuadric(), 0.25, 20, 20)
    glPopMatrix()

    # Arms
    glColor3f(1,1,1)
    for offset in [-0.2, 0.2]:
        glPushMatrix()
        glTranslatef(offset, 0.2, 0.3)
        glRotatef(45,1,0,0)
        gluCylinder(gluNewQuadric(),0.05,0.05,0.4,15,15)
        glPopMatrix()

    # Gun
    glColor3f(0.5,0.5,0.5)
    glPushMatrix()
    glTranslatef(0,0.1,0.3)
    gluCylinder(gluNewQuadric(),0.07,0.07,0.7,15,15)
    gluSphere(gluNewQuadric(),0.1,15,15)
    glPopMatrix()

    glPopMatrix()


def draw_bullet(b):
    
    glPushMatrix()
    glTranslatef(b['x'], 0.5, b['z'])  # Position the bullet
    glColor3f(1, 1, 0)  # Yellow color for the bullet
    gluSphere(gluNewQuadric(), 0.1, 20, 20)  
    glPopMatrix()

def draw_enemy(enemy):

    glPushMatrix()
    glTranslatef(enemy['x'], 0.5, enemy['z'])
    glRotatef(enemy.get('angle', 0), 0, 1, 0)  # Rotate the enemy to face the player

    # Legs
    if aggressive_enemies:
        glColor3f(1.0, 0.0, 0.0)  # Red (aggressive)
    else:
        glColor3f(1.0, 0.0, 0.0)  # Red (default)
    for offset in [-0.15, 0.15]:
        glPushMatrix()
        glTranslatef(offset, -0.5, 0)
        glRotatef(90, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 0.1, 0.1, 0.6, 15, 15)
        glPopMatrix()

    # Body
    if aggressive_enemies:
        glColor3f(1.0, 0.0, 0.0)  # Red  (aggressive)
    else:
        glColor3f(0.0, 0.0, 1)  # Blue (default)
    glPushMatrix()
    glTranslatef(0, 0.2, 0)
    glScalef(0.5, 0.8, 0.3)
    glutSolidCube(1)
    glPopMatrix()

    # Head
    glColor3f(0, 0, 0)  # Black 
    glPushMatrix()
    glTranslatef(0, 0.9, 0)
    gluSphere(gluNewQuadric(), 0.25, 20, 20)
    glPopMatrix()

    # Arms
    glColor3f(1, 1, 1)  # White arms
    for offset in [-0.2, 0.2]:
        glPushMatrix()
        glTranslatef(offset, 0.2, 0.3)
        glRotatef(45, 1, 0, 0)
        gluCylinder(gluNewQuadric(), 0.05, 0.05, 0.4, 15, 15)
        glPopMatrix()

    # Gun (only for non-aggressive enemies)
    if not aggressive_enemies:
        glColor3f(0.5, 0.5, 0.5)  # Gray gun
        glPushMatrix()
        glTranslatef(0, 0.1, 0.3)
        gluCylinder(gluNewQuadric(), 0.07, 0.07, 0.7, 15, 15)
        gluSphere(gluNewQuadric(), 0.1, 15, 15)
        glPopMatrix()

    glPopMatrix()

def draw_enemies():
    for e in enemies:
        draw_enemy(e)

def draw_enemy_bullet(b):
    glPushMatrix()
    glTranslatef(b['x'], 0.5, b['z'])  # Position the bullet
    glColor3f(1, 1, 0)  # Yellow color for the bullet
    gluSphere(gluNewQuadric(), 0.1, 20, 20)
    glPopMatrix()

def draw_health_kits():
    glColor3f(0.0, 1.0, 0.0)  # Green
    for kit in health_kits:
        glPushMatrix()
        glTranslatef(kit['x'], 0.25, kit['z'])
        glScalef(0.4, 0.4, 0.4)
        glutSolidCube(1)
        glPopMatrix()

def draw_bombs():
    glColor3f(0.7, 0.1, 0.1)  # Red bomb
    for bomb in bombs:
        if bomb['active']:
            glPushMatrix()
            glTranslatef(bomb['x'], bomb['y'], bomb['z'])
            glutSolidSphere(0.35, 16, 16)
            glPopMatrix()

def draw_mines():
    glColor3f(0.2, 0.2, 0.2)  # Dark gray for mine
    for mine in mines:
        glPushMatrix()
        glTranslatef(mine['x'], 0.1, mine['z'])
        glScalef(0.3, 0.1, 0.3)
        glutSolidCube(1)
        glPopMatrix()

def update_bombs():
    global bombs, enemies
    gravity = -0.08
    for bomb in bombs:
        if not bomb['active']:
            continue
        bomb['vy'] += gravity
        bomb['y'] += bomb['vy']
        # If bomb hits the ground, deactivate
        if bomb['y'] <= 0.5:
            bomb['y'] = 0.5
            bomb['active'] = False
        # Check collision with enemies (only while falling)
        for e in enemies[:]:
            if bomb['active'] and dist2D(bomb['x'], bomb['z'], e['x'], e['z']) < 0.6 and bomb['y'] <= 1.0:
                e['health'] -= 1
                bomb['active'] = False
                if e['health'] <= 0:
                    try: enemies.remove(e)
                    except ValueError: pass

def update_mines():

    global mines, enemies, life
    for mine in mines:
        # Player collision: damage player by 2 and respawn mine
        if dist2D(mine['x'], mine['z'], player_x, player_z) < 0.6:
            life -= 2
            if life <= 0:
                end_game()
            free_cells = []
            for j in range(1, MAZE_H-1):
                for i in range(1, MAZE_W-1):
                    if MAZE[j][i] == 0 and (abs(GRID_MIN + i + 0.5 - mine['x']) > 0.1 or abs(GRID_MIN + j + 0.5 - mine['z']) > 0.1):
                        free_cells.append((i, j))
            if free_cells:
                ni, nj = random.choice(free_cells)
                mine['x'] = GRID_MIN + ni + 0.5
                mine['z'] = GRID_MIN + nj + 0.5
            # skip checking enemies for this mine this frame
            continue

        for e in enemies:
            if dist2D(mine['x'], mine['z'], e['x'], e['z']) < 0.35:
                e['health'] -= 1
                # Respawn mine at a new random free cell
                free_cells = []
                for j in range(1, MAZE_H-1):
                    for i in range(1, MAZE_W-1):
                        if MAZE[j][i] == 0 and (abs(GRID_MIN + i + 0.5 - mine['x']) > 0.1 or abs(GRID_MIN + j + 0.5 - mine['z']) > 0.1):
                            free_cells.append((i, j))
                if free_cells:
                    ni, nj = random.choice(free_cells)
                    mine['x'] = GRID_MIN + ni + 0.5
                    mine['z'] = GRID_MIN + nj + 0.5
               
                break

def update_enemies(dt):
    global life, freeze_enemies
    if game_over:
        return

    
    if freeze_enemies:
        for e in enemies:
            e['scale'] += 0.4 * dt * e.get('scale_dir', 1)
            if e['scale'] > 0.45:
                e['scale'] = 0.45; e['scale_dir'] = -1
            if e['scale'] < 0.25:
                e['scale'] = 0.25; e['scale_dir'] = 1
            dx = player_x - e['x']
            dz = player_z - e['z']
            e['angle'] = math.degrees(math.atan2(dx, dz))
        return

    now = time.time()
    for e in enemies:
        # simple pulsing scale
        e['scale'] += 0.4 * dt * e.get('scale_dir', 1)
        if e['scale'] > 0.45:
            e['scale'] = 0.45; e['scale_dir'] = -1
        if e['scale'] < 0.25:
            e['scale'] = 0.25; e['scale_dir'] = 1

        # Rotate enemy to face the player
        dx = player_x - e['x']
        dz = player_z - e['z']
        e['angle'] = math.degrees(math.atan2(dx, dz))

        if aggressive_enemies:
            
            dlen = math.hypot(dx, dz)
            if dlen > 0.01:
                speed = 0.012 * dt * 60 
                move_x = (dx / dlen) * speed
                move_z = (dz / dlen) * speed
                # Try to move, but don't go through walls
                next_x = e['x'] + move_x
                next_z = e['z'] + move_z
                # Only update if not colliding with wall
                if not is_wall(next_x, e['z']):
                    e['x'] = next_x
                if not is_wall(e['x'], next_z):
                    e['z'] = next_z
            # Check collision with player
            if dist2D(e['x'], e['z'], player_x, player_z) < 0.6:
                if life > 0:
                    life -= 1
                    if life <= 0:
                        end_game()
        else:
            e['x'] += (random.random() - 0.5) * 0.02 * dt * 60
            e['z'] += (random.random() - 0.5) * 0.02 * dt * 60
            # Clamp inside arena and avoid walls
            if is_wall(e['x'], e['z']):
                # Try to move back if inside wall
                e['x'] = max(GRID_MIN+1, min(GRID_MAX-1, e['x']))
                e['z'] = max(GRID_MIN+1, min(GRID_MAX-1, e['z']))
            # shooting logic
            if dist2D(player_x, player_z, e['x'], e['z']) <= ENEMY_SHOOT_RANGE:
                if now - e.get('last_shot', 0.0) >= e.get('cooldown', ENEMY_MIN_COOLDOWN):
                    dlen = math.hypot(dx, dz)
                    if dlen > 0.001:
                        vx = (dx / dlen) * ENEMY_BULLET_SPEED
                        vz = (dz / dlen) * ENEMY_BULLET_SPEED
                        enemy_bullets.append({'x': e['x'], 'z': e['z'], 'dx': vx, 'dz': vz})
                        e['last_shot'] = now
                        e['cooldown'] = random.uniform(ENEMY_MIN_COOLDOWN, ENEMY_MAX_COOLDOWN)

        # Clamp inside arena
        e['x'] = max(GRID_MIN+1, min(GRID_MAX-1, e['x']))
        e['z'] = max(GRID_MIN+1, min(GRID_MAX-1, e['z']))

def update_bullets():
    global bullets, enemies, score, misses, health_kits, aggressive_enemies, bombs
    prev_score = score
    for b in bullets[:]:
        dx = b.get('dx', 0.0)
        dz = b.get('dz', 0.0)
        travel = math.hypot(dx, dz)
        if travel == 0:
            try: bullets.remove(b)
            except ValueError: pass
            continue

        # Use smaller step size for more accurate collision
        step_size = 0.03 
        steps = max(1, int(math.ceil(travel / step_size)))
        removed = False
        for _ in range(steps):
            nx = b['x'] + dx / steps
            nz = b['z'] + dz / steps

            # wall collision
            if is_wall(nx, nz):
                try: bullets.remove(b)
                except ValueError: pass
                removed = True
                break

           
            hit = None
            for e in enemies[:]:
                
                enemy_radius = max(e.get('scale', 0.3) * 0.9, 0.22)
                if dist2D(nx, nz, e['x'], e['z']) < (enemy_radius + 0.12):
                    hit = e
                    break
            if hit:
                try: bullets.remove(b)
                except ValueError: pass
                hit['health'] -= 1
                if hit['health'] <= 0:
                    try: enemies.remove(hit)
                    except ValueError: pass
                    score += 1
                    if score >= 5:
                        aggressive_enemies = True
                    health_kits.append({'x': hit['x'], 'z': hit['z']})
                    ex = random.uniform(GRID_MIN+1, GRID_MAX-1)
                    ez = random.uniform(GRID_MIN+1, GRID_MAX-1)
                    enemies.append({
                        'x': ex,
                        'z': ez,
                        'scale': 0.3,
                        'scale_dir': 1,
                        'last_shot': 0.0,
                        'cooldown': random.uniform(ENEMY_MIN_COOLDOWN, ENEMY_MAX_COOLDOWN),
                        'health': 3
                    })
                removed = True
                break

           
            b['x'], b['z'] = nx, nz

        if removed:
            continue

        # bounds check
        if b['x'] < GRID_MIN-1 or b['x'] > GRID_MAX+1 or b['z'] < GRID_MIN-1 or b['z'] > GRID_MAX+1:
            try: bullets.remove(b)
            except ValueError: pass
            misses += 1
    # Drop a bomb every time score increases by 2
    if score // 2 > prev_score // 2:
        free_cells = []
        for j in range(1, MAZE_H-1):
            for i in range(1, MAZE_W-1):
                if MAZE[j][i] == 0:
                    free_cells.append((i, j))
        if free_cells:
            i, j = random.choice(free_cells)
            wx = GRID_MIN + i + 0.5
            wz = GRID_MIN + j + 0.5
            bombs.append({'x': wx, 'z': wz, 'y': 12.0, 'vy': 0.0, 'active': True})

def update_enemy_bullets():
    global enemy_bullets, life
    # when player is dead, clear any in-flight enemy bullets and stop processing
    if game_over:
        enemy_bullets.clear()
        return

    for b in enemy_bullets[:]:
        travel = math.hypot(b['dx'], b['dz'])
        if travel == 0:
            try: enemy_bullets.remove(b)
            except ValueError: pass
            continue
        step_size = 0.1
        steps = max(1, int(math.ceil(travel / step_size)))
        hit = False
        for _ in range(steps):
            nx = b['x'] + b['dx'] / steps
            nz = b['z'] + b['dz'] / steps
            if is_wall(nx, nz):
                hit = True
                try: enemy_bullets.remove(b)
                except ValueError: pass
                break
            # check player hit
            if dist2D(nx, nz, player_x, player_z) < 0.6:
                try: enemy_bullets.remove(b)
                except ValueError: pass
                life -= 1
                if life <= 0:
                    end_game()
                hit = True
                break
            b['x'], b['z'] = nx, nz
        if hit:
            continue
        # bounds
        if b['x'] < GRID_MIN-1 or b['x'] > GRID_MAX+1 or b['z'] < GRID_MIN-1 or b['z'] > GRID_MAX+1:
            try: enemy_bullets.remove(b)
            except ValueError: pass

def clamp_player_pos():
    global player_x, player_z
    player_x = max(GRID_MIN, min(GRID_MAX, player_x))
    player_z = max(GRID_MIN, min(GRID_MAX, player_z))

def keyboardListener(key, x, y):
    global player_x, player_z, player_angle, life, score, misses, game_over, cheat_mode, auto_follow, top_view, freeze_enemies
   
    if game_over:
        if key == b'r':
            reset_game()
        return
    
    if key == b'f':
        freeze_enemies = not freeze_enemies
        return

    if key == b'w':
        nx = player_x + player_speed * math.sin(math.radians(player_angle))
        nz = player_z + player_speed * math.cos(math.radians(player_angle))
        if not is_wall(nx, nz):
            player_x, player_z = nx, nz
        clamp_player_pos()
    elif key == b's':
        nx = player_x - player_speed * math.sin(math.radians(player_angle))
        nz = player_z - player_speed * math.cos(math.radians(player_angle))
        if not is_wall(nx, nz):
            player_x, player_z = nx, nz
        clamp_player_pos()
    elif key == b'a':
        player_angle = (player_angle + 5) % 360
    elif key == b'd':
        player_angle = (player_angle - 5) % 360
    elif key == b'c':
        cheat_mode = not cheat_mode
    elif key == b'v':
        top_view = not top_view

def specialKeyListener(key, x, y):
    global cam_angle, cam_height, cheat_mode
    if key == GLUT_KEY_LEFT:
        cam_angle = (cam_angle - 5) % 360
    elif key == GLUT_KEY_RIGHT:
        cam_angle = (cam_angle + 5) % 360
    elif key == GLUT_KEY_UP:
        cam_height += 0.5
    elif key == GLUT_KEY_DOWN:
        cam_height = max(1.0, cam_height - 0.5)
    elif key == GLUT_KEY_F1:
        cheat_mode = not cheat_mode

def mouseListener(button, state, x, y):
    global bullets, first_person
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN and not game_over:
        bullet_speed = 0.4
        dx = bullet_speed * math.sin(math.radians(player_angle))
        dz = bullet_speed * math.cos(math.radians(player_angle))
        bullets.append({'x': player_x, 'z': player_z, 'dx': dx, 'dz': dz})
    elif button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        first_person = not first_person

def reset_game():
    global life, score, misses, game_over, player_x, player_z, player_angle, bullets, cheat_mode, auto_follow, start_time, survival_time
    global final_checkpoint, final_checkpoint_active
    life = 5
    score = 0
    misses = 0
    game_over = False
    # Reset timing for a new run
    start_time = time.time()
    survival_time = None
    player_x = 0.0
    player_z = 0.0
    player_angle = 0.0
    bullets.clear()
    cheat_mode = False
    auto_follow = False
    create_maze()
    spawn_enemies()
    final_checkpoint = None
    final_checkpoint_active = False

def update_health_kits():
    global health_kits, life
    for kit in health_kits[:]:
        if dist2D(player_x, player_z, kit['x'], kit['z']) < 0.8:
            life += 1
            try:
                health_kits.remove(kit)
            except ValueError:
                pass


def update_checkpoints_and_door():
  
    global checkpoints, checkpoints_found, final_checkpoint, final_checkpoint_active, game_over
    if game_over:
        return
    # player collects checkpoints
    for cp in checkpoints[:]:
        if dist2D(player_x, player_z, cp['x'], cp['z']) < 0.8:
            try: checkpoints.remove(cp)
            except ValueError: pass
            checkpoints_found += 1
    # spawn final checkpoint after all initial found
    if checkpoints_found >= TOTAL_CHECKPOINTS and not final_checkpoint_active:
        # Find a random free cell for the final checkpoint
        free_cells = []
        for j in range(1, MAZE_H-1):
            for i in range(1, MAZE_W-1):
                if MAZE[j][i] == 0:
                    free_cells.append((i, j))
        if free_cells:
            i, j = random.choice(free_cells)
            wx = GRID_MIN + i + 0.5
            wz = GRID_MIN + j + 0.5
            final_checkpoint = {'x': wx, 'z': wz}
            final_checkpoint_active = True
    # win if player reaches final checkpoint
    if final_checkpoint_active and final_checkpoint is not None:
        if dist2D(player_x, player_z, final_checkpoint['x'], final_checkpoint['z']) < 0.9:
            end_game()

def create_maze(density=0.12, seed=None):

    global MAZE, MAZE_W, MAZE_H, final_checkpoint, final_checkpoint_active
    if seed is not None:
        random.seed(seed)
    size = GRID_MAX - GRID_MIN
    MAZE_W = MAZE_H = size
    MAZE = [[0 for _ in range(MAZE_W)] for __ in range(MAZE_H)]
    # border walls
    for x in range(MAZE_W):
        MAZE[0][x] = 1
        MAZE[MAZE_H-1][x] = 1
    for y in range(MAZE_H):
        MAZE[y][0] = 1
        MAZE[y][MAZE_W-1] = 1
    
    px_idx = int((0.0 - GRID_MIN))
    pz_idx = int((0.0 - GRID_MIN))
    for y in range(1, MAZE_H-1):
        for x in range(1, MAZE_W-1):
            if abs(x-px_idx) <= 1 and abs(y-pz_idx) <= 1:
                continue
            if random.random() < density:
                MAZE[y][x] = 1
                
                if random.random() < 0.5 and x+1 < MAZE_W-1:
                    MAZE[y][x+1] = 1
                if random.random() < 0.5 and y+1 < MAZE_H-1:
                    MAZE[y+1][x] = 1
    place_checkpoints()
    final_checkpoint = None
    final_checkpoint_active = False
    place_mines()

def place_mines(count=MINES_COUNT, min_distance_from_player=3.0):
    global mines
    mines = []
    if not MAZE or MAZE_W <= 2 or MAZE_H <= 2:
        return

    free_cells = []
    for j in range(1, MAZE_H - 1):
        for i in range(1, MAZE_W - 1):
            if MAZE[j][i] != 0:
                continue
            wx = GRID_MIN + i + 0.5
            wz = GRID_MIN + j + 0.5

            if dist2D(wx, wz, player_x, player_z) < min_distance_from_player:
                continue
            free_cells.append((i, j))

    random.shuffle(free_cells)
    for idx in range(min(count, len(free_cells))):
        i, j = free_cells[idx]
        wx = GRID_MIN + i + 0.5
        wz = GRID_MIN + j + 0.5
        mines.append({'x': wx, 'z': wz})

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1, 1, 1)
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def showScreen():
    global cam_x, cam_y, cam_z
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    aspect = window_width / window_height
    gluPerspective(60, aspect, 0.5, 100)

    if top_view:
        eyeX = player_x
        eyeY = 12.0
        eyeZ = player_z
        centerX = player_x
        centerY = 0.0
        centerZ = player_z
        gluLookAt(eyeX, eyeY, eyeZ, centerX, centerY, centerZ, 0, 0, -1)
    elif first_person:
        eyeX = player_x 
        eyeY = 0.9 
        eyeZ = player_z 
        centerX = player_x + math.sin(math.radians(player_angle))
        centerY = 0.9
        centerZ = player_z + math.cos(math.radians(player_angle))
        gluLookAt(eyeX, eyeY, eyeZ, centerX, centerY, centerZ, 0, 1, 0)
    else:
        # Compute target camera position behind the player based on player_angle
        rad = math.radians(player_angle)
        # Move camera closer and lower
        target_x = player_x - (cam_distance * 0.7) * math.sin(rad)  # 0.7x closer
        target_z = player_z - (cam_distance * 0.7) * math.cos(rad)
        target_y = player_x and (cam_follow_height * 0.7 + 0.7) or (cam_follow_height * 0.7)  # lower height

        # Sothly interpolate current camera position toward target
        cam_x += (target_x - cam_x) * cam_smooth
        cam_y += (target_y - cam_y) * cam_smooth
        cam_z += (target_z - cam_z) * cam_smooth
        look_x = player_x
        look_y = 1.0
        look_z = player_z
        gluLookAt(cam_x, cam_y, cam_z, look_x, look_y, look_z, 0, 1, 0)

    draw_grid()
    draw_maze()
    draw_checkpoints()
    draw_final_checkpoint()
    draw_bombs()
    draw_mines()
    won = game_over and final_checkpoint_active and final_checkpoint is not None and dist2D(player_x, player_z, final_checkpoint['x'], final_checkpoint['z']) < 0.9
    if not won:
        draw_player()
        draw_enemies()
        for eb in enemy_bullets:
            draw_enemy_bullet(eb)
        for bullet in bullets:
            draw_bullet(bullet)
        draw_health_kits()

    # Draw text (health, score, checkpoints)
    glDisable(GL_DEPTH_TEST)
    hud_y = window_height - 30

    if won:
        draw_text(10, hud_y, "Congratulations! You survived!", GLUT_BITMAP_HELVETICA_18)
        draw_text(10, hud_y - 30, f"Final Score: {score}", GLUT_BITMAP_HELVETICA_18)
        if survival_time is not None:
            draw_text(10, hud_y - 60, f"Survival Time: {survival_time:.1f} s")
    elif game_over:
        draw_text(window_width // 2 - 80, window_height // 2, "GAME OVER", GLUT_BITMAP_HELVETICA_18)
        draw_text(window_width // 2 - 120, window_height // 2 - 30, "Press 'r' to restart", GLUT_BITMAP_HELVETICA_18)
        if survival_time is not None:
            draw_text(10, hud_y - 125, f"Survival Time: {survival_time:.1f} s", GLUT_BITMAP_HELVETICA_18)
    else:
        draw_text(10, hud_y, f"Health: {life}")
        draw_text(10, hud_y - 25, f"Score: {score}")
        draw_text(10, hud_y - 50, f"Checkpoints: {checkpoints_found}/{TOTAL_CHECKPOINTS}")
        if final_checkpoint_active:
            draw_text(10, hud_y - 75, "Final checkpoint active!", GLUT_BITMAP_HELVETICA_18)
        if cheat_mode:
            draw_text(10, hud_y - 100, "Cheat Mode: ON")
        if freeze_enemies:
            draw_text(10, hud_y - 125, "Enemies: FROZEN", GLUT_BITMAP_HELVETICA_18)
    glEnable(GL_DEPTH_TEST)

    glutSwapBuffers()

def animate():
    """Update game state and redraw the screen."""
    global last_time
    current_time = time.time()
    delta_time = current_time - last_time
    last_time = current_time
    update_bullets()
    update_enemy_bullets()
    update_enemies(delta_time)
    update_bombs()
    update_mines()  # Update mines (enemy collision/respawn)
    update_checkpoints_and_door()
    update_health_kits()
    glutPostRedisplay()

def init():
    glClearColor(0,0,0,1)
    glEnable(GL_DEPTH_TEST)  # Enable depth testing so objects occlude each other properly


def main():
    global last_time, start_time, survival_time
    last_time = time.time()
    start_time = time.time()
    survival_time = None
    
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(window_width, window_height)
    glutInitWindowPosition(200,200)
    glutCreateWindow(b"Warfare Arena 3D")
    create_maze()
    spawn_enemies()
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)
    glutIdleFunc(animate)

    init()
    glutMainLoop()

if __name__ == "__main__":
    main()
