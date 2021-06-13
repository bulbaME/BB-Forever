import pygame, time, random, pymunk

tick = 0.005
PI = 3.14159

pygame.init()
pygame.display.set_caption('B&B forever')
pygame.display.set_icon(pygame.image.load('icon2.png'))
screenWidth, screenHeight = 1280, 720
screen = pygame.display.set_mode((screenWidth, screenHeight))

space = pymunk.Space()
space.gravity = (0.0, 900.0)
space.sleep_time_threshold = 100000
s = 64


# classes
# -------------------------------------------------------------------------- #

class Player:
    def __init__(self, t, animations, frameTime = 100):
        self.type = t
        self.spriteNumber = 0
        self.sprite = None
        self.currentAnimation = ''
        self.animations = animations

        self.frameTime = frameTime
        self.nextFrameTicks = 0
        self.frameMax = 0
        self.frameCounter = 0
        self.animationStopped = False

        self.body = pymunk.Body()
        self.shape = pymunk.Poly(self.body, [(-s/3.2, -s/2), (s/3.2, -s/2), (-s/3.2, s/2), (s/3.2, s/2)])
        self.shape.mass = 1
        self.shape.collision_type = 2
        space.add(self.body, self.shape)

        self.collidesR = False
        self.collidesL = False
        self.collisionSkipRL = 0

        self.accelerating = False
        self.jumping = False
        self.mirrored = False
        self.onPlatform = False
        self.onladder = False
        self.using = False
        self.asleep = False
        self.ladderMoved = 0

        self.dynamicColliding = False
        self.collisionSkip = 0

        self.ammo = 50

        self.boxM = False
        self.boxMTimeout = 5
        self.boxMTicks = 0

        self.setAnimation(list(animations.keys())[0])

    def use(self):

        if self.type == 1:
            if self.ammo > 0:
                self.setAnimation('use')
                m = 1 if self.mirrored else -1
                Bullet((self.body.position[0] + 30 * m * -1, self.body.position[1] - 12), m * -1)
                self.body.apply_force_at_local_point((m * 50000, 0))
                self.ammo -= 1 
        else:
            self.setAnimation('use')
        
        self.using = True

    def setAnimation(self, name):
        self.currentAnimation = name
        self.frameCounter = 0
        self.nextFrameTicks = 0
        self.frameMax = len(self.animations[self.currentAnimation]) - 1

    def draw(self):
        self.body.angle = 0
        playerPos = (self.body.position[0] - s/2, self.body.position[1] - s/2)
        playerAngle = self.body.angle * (180 / PI)
        screen.blit(pygame.transform.rotate(self.sprite, playerAngle), playerPos)

    def nextFrame(self):
        self.frameCounter += 1
        if self.frameCounter > self.frameMax:
            if self.currentAnimation == 'use':
                self.using = False
                self.setAnimation('idle')
            else:
                self.frameCounter = 0

        frame = self.animations[self.currentAnimation][self.frameCounter]
        if len(frame) == 2:
            self.nextFrameTicks = frame[1]
        else:
            self.nextFrameTicks = self.frameTime

        self.sprite = frame[0]
        if self.mirrored:
            self.spriteMirror()

    def spriteMirror(self):
        self.sprite = pygame.transform.flip(self.sprite, True, False)
    
    def update(self, events):
        # movement
        if self.boxM:
            self.boxMTicks -= 1
            if not self.boxMTicks:
                self.boxM = False

        # check if on ladder
        self.onladder = False
        if self.sprite:
            p = self.body.position
            for l in ladders:
                if (l[0]-10 < p[0] < l[0] + 50) and\
                    (l[1]-32 < p[1] < l[1] + 64):
                    self.onladder = True
                    break

        for event in events:
            # key pressed once
            if event.type == pygame.KEYDOWN:
                # jump
                if event.key == pygame.K_w and not self.jumping and not self.onladder:
                    self.body.apply_force_at_local_point((0, -100000), (0,0))
                # shoot
                elif event.key == pygame.K_RETURN and not self.using and not self.jumping and not self.accelerating and not self.onladder:
                    self.use()

        # key down
        keys = pygame.key.get_pressed()
        # ladder 
        if self.onladder:
            if self.ladderMoved < -10 or self.ladderMoved > 10:
                self.ladderMoved = 0
                self.nextFrame()

            self.body.apply_force_at_local_point((0, -900))
            # upwards
            if keys[pygame.K_w]:
                self.ladderMoved += 0.2
                self.body._set_velocity((0, -100))
            # downwards
            elif keys[pygame.K_s]:
                self.body.apply_force_at_local_point((0, 100))

            else:
                self.body._set_velocity((0, 0))

        # left / right
        if keys[pygame.K_a] or keys[pygame.K_d]:
            self.accelerating = True

            if keys[pygame.K_a] and not self.collidesL:
                if not self.mirrored:
                    self.spriteMirror()
                self.mirrored = True
                self.body.position = (self.body.position[0] - 1.2, self.body.position[1])
            elif keys[pygame.K_d] and not self.collidesR:
                if self.mirrored:
                    self.spriteMirror()
                self.mirrored = False
                self.body.position = (self.body.position[0] + 1.2, self.body.position[1])
        else:
            self.accelerating = False

        # standing on the platform can cause strange effects
        if self.body._get_velocity()[1] < 0.001 and self.body._get_velocity()[1] > -0.001:
            self.jumping = False
        else:
            self.jumping = True

        if not self.using:
            if self.boxM and self.type == 2:
                if self.currentAnimation != 'box':
                    self.setAnimation('box')
            elif self.onladder:
                if self.currentAnimation != 'ladder':
                    self.setAnimation('ladder')
                    self.nextFrame()
            elif self.jumping and not self.boxM:
                if self.currentAnimation != 'jump':
                    self.setAnimation('jump')
            elif self.accelerating:
                if self.currentAnimation != 'walk':
                    self.setAnimation('walk')
            else:
                if self.currentAnimation != 'idle':
                    self.setAnimation('idle')

        # animation
        if not self.onladder:
            if self.nextFrameTicks == 0:
                self.nextFrame()
            self.nextFrameTicks -= 1

        # draw
        self.draw()

class Platform:
    def __init__(self, movement, speed = [1, 0]):
        self.body, self.shape, self.sprite = None, None, None
        self.speed = speed
        self.movement = movement
        self.x, self.y = 0, 0

    def setp(self, body, shape, sprite):
        self.body = body
        self.shape = shape
        self.sprite = sprite
        self.position = body.position

    def draw(self):
        screen.blit(self.sprite[gameData['state']], self.newPos)

    def step(self):
        self.x += self.speed[0]
        self.y += self.speed[1]

        if self.x >= self.movement[0]:
            self.x = self.movement[0]
            self.speed[0] = -self.speed[0]
        
        elif self.x < 0:
            self.x = 0
            self.speed[0] = -self.speed[0]

        if self.y >= self.movement[1]:
            self.y = self.movement[1]
            self.speed[1] = -self.speed[1]

        elif self.y < 0:
            self.y = 0
            self.speed[1] = -self.speed[1]

        self.newPos = (self.position[0] + self.x, self.position[1] + self.y)

        self.body.position = self.newPos
        self.body.velocity = (self.speed[0] * 200, self.speed[1] * 200)
        self.draw()

class Box:
    def __init__(self, mass = 100):
        self.body, self.shape, self.sprite = None, None, None
        self.mass = mass
        self.id = len(boxes) + 20

        boxes.append(self)

    def setp(self, body, shape, sprite):
        self.body = body
        self.shape = shape
        self.sprite = sprite
        self.shape.collision_type = self.id

        space.add_collision_handler(self.id, 2).pre_solve = lambda a, s, d: onCollisionBox(a, s, d, players[gameData['state']], self)
        space.add_collision_handler(self.id, 0).pre_solve = lambda a, s, d: onCollisionBoxFloor(a, s, d, self)

    def draw(self):
        angle = self.body.angle * (180 / PI)
        screen.blit(pygame.transform.rotate(self.sprite[gameData['state']], angle), self.position)

    def step(self):
        self.position = (self.body.position[0] - s / 2, self.body.position[1] - s / 2)
        self.draw()

class Bullet:
    def __init__(self, position, direction):
        self.sprite = normalizeImage('assets/bullet.png')
        self.direction = direction
        self.body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.body.position = position
        self.shape = pymunk.Poly(self.body, [(0, 0), (0, 8), (4, 0), (4, 8)])
        self.shape.body_type = 8
        self.destroy = False

        kinematicBehaviours.append(self)

    def draw(self):
        screen.blit(self.sprite, self.body.position)

    def step(self):
        self.body.position = (self.body.position[0] + self.direction * 3, self.body.position[1])
        self.draw()

# -------------------------------------------------------------------------- #



# loaders
# -------------------------------------------------------------------------- #

def loadMap(fileName, tiles):
    file = open(fileName, 'r')

    lc = 0
    while True:
        l = file.readline()
        if not l:
            break

        lc += 1
        first = 0
        for c in range(len(l)):
            position = (c * s, lc * s)
            # ladders
            if l[c] == 'L':
                toDraw[1].append([tiles['L'][0], position])
                ladders.append(position)

            # process each texture
            elif l[c] in tiles.keys():
                tile = tiles[l[c]]
                collisionPoints = [(-s/2, -s/2), (s/2, -s/2), (-s/2, s/2), (s/2, s/2)]
                if len(tile) > 2 and tile[2]:
                    collisionPoints = tile[2]

                if tile[1] == 1:
                    # make line from tiles
                    toDraw[0].append([tile[0], position])
                    
                    if c < len(l) - 1 and l[c + 1] in tiles.keys() and tiles[l[c + 1]][1] == 1:
                        if not first:
                            first = position
                    else:
                        if not first:
                            first = position
                        last = (position[0] + s, first[1])

                        for first, last, colType in [[first, (last[0] - first[0], 0), 0],
                            [first, (0, s), 1],
                            [(first[0], first[1] + s), (last[0] - first[0], 0), 0],
                            [(last[0], last[1]), (0, s), 1]]:

                            body = pymunk.Body(body_type = pymunk.Body.STATIC)
                            body.position = first
                            shape = pymunk.Segment(body, (0, 0), last, 1)
                            shape.collision_type = colType
                            
                            space.add(body, shape)
                        first = 0

                elif tile[1] == 2 or tile[1] == 3:
                    body = pymunk.Body(body_type = pymunk.Body.KINEMATIC if tile[1] == 2 else pymunk.Body.DYNAMIC)
                    body.position = position
                    shape = pymunk.Poly(body, collisionPoints)
                    
                    if tile[1] == 2:
                        shape.collision_type = 5
                        body._set_velocity((5, 0))
                    
                    else:
                        shape.collision_type = 6
                        shape.friction = 1
                        shape.mass = tile[3].mass
                        
                    tile[3].setp(body, shape, tile[0])
                    kinematicBehaviours.append(tile[3])
                    space.add(body, shape)

            # set player position
            elif l[c] == 'p':
                players[gameData['state']].body.position = position

credits = []
def loadCredits():
    global credits
    credits[0] = normalizeImage('credits/credit.png')
    credits[1] = (0, 0)
    credits[2] = credits[0].get_size()[1]

instruction = 1
def loadInstruction(slide):
    try:
        img = normalizeImage(f'help/{slide}.png')
        screen.blit(img, (0, 0))
    except:
        changeLevel(0)

menuButtons = []
def loadMenu():
    global menuButtons
    resetLevel()

    menuButtons = {
        'start': [[normalizeImage('buttons/start1.png'), normalizeImage('buttons/start2.png'), normalizeImage('buttons/start3.png')], (600, 100)],
        'help': [[normalizeImage('buttons/help1.png'), normalizeImage('buttons/help2.png'), normalizeImage('buttons/help3.png')], (600, 250)],
        'sound': [[normalizeImage('buttons/sound1.png'), normalizeImage('buttons/sound2.png'), normalizeImage('buttons/sound3.png')], (600, 400), [normalizeImage('buttons/sound1.png'), normalizeImage('buttons/sound2.png'), normalizeImage('buttons/sound3.png')]],
        'music': [[normalizeImage('buttons/music1.png'), normalizeImage('buttons/music2.png'), normalizeImage('buttons/music3.png')], (750, 400), [normalizeImage('buttons/music1.png'), normalizeImage('buttons/music2.png'), normalizeImage('buttons/music3.png')]],
        'credits': [[normalizeImage('buttons/credits1.png'), normalizeImage('buttons/credits2.png'), normalizeImage('buttons/credits3.png')], (600, 550)],
        'exit': [[normalizeImage('buttons/exit1.png'), normalizeImage('buttons/exit2.png'), normalizeImage('buttons/exit3.png')], (600, 700)]
    }

def changeLevel(level):
    global players
    resetLevel()

    if level:
        players = [Player(1, {
            'idle':   [[normalizeImage('player/1/idle/1.png')],     [normalizeImage('player/1/idle/2.png')],     [normalizeImage('player/1/idle/3.png')]],
            'jump':   [[normalizeImage('player/1/jump/1.png')],     [normalizeImage('player/1/jump/2.png')],     [normalizeImage('player/1/jump/3.png')]],
            'use':    [[normalizeImage('player/1/use/1.png')],      [normalizeImage('player/1/use/2.png'), 20]],
            'ladder': [[normalizeImage('player/1/ladder/1.png')],   [normalizeImage('player/1/ladder/2.png')],   [normalizeImage('player/1/ladder/3.png')]],
            'walk':   [[normalizeImage('player/1/walk/1.png'), 38], [normalizeImage('player/1/walk/2.png'), 38], [normalizeImage('player/1/walk/3.png'), 38], [normalizeImage('player/1/walk/4.png'), 38]]
            }), Player(2, {
            'idle':   [[normalizeImage('player/2/idle/1.png')],     [normalizeImage('player/2/idle/2.png')],     [normalizeImage('player/2/idle/3.png')]],
            'jump':   [[normalizeImage('player/2/jump/1.png')],     [normalizeImage('player/2/jump/2.png')],     [normalizeImage('player/2/jump/3.png')]],
            'use':    [[normalizeImage('player/2/use/1.png')],      [normalizeImage('player/2/use/2.png')],      [normalizeImage('player/2/use/3.png')]],
            'ladder': [[normalizeImage('player/2/ladder/1.png')],   [normalizeImage('player/2/ladder/2.png')],   [normalizeImage('player/2/ladder/3.png')]],
            'walk':   [[normalizeImage('player/2/walk/1.png'), 38], [normalizeImage('player/2/walk/2.png'), 38], [normalizeImage('player/2/walk/3.png'), 38], [normalizeImage('player/2/walk/4.png'), 38]],
            'box':    [[normalizeImage('player/2/box/1.png')],      [normalizeImage('player/2/box/2.png')],      [normalizeImage('player/2/box/3.png')],      [normalizeImage('player/2/box/4.png')]]
            }), Player(3, {
            'idle':   [[normalizeImage('player/3/idle/1.png')],     [normalizeImage('player/3/idle/2.png')],     [normalizeImage('player/3/idle/3.png')]],
            'jump':   [[normalizeImage('player/3/jump/1.png')],     [normalizeImage('player/3/jump/2.png')],     [normalizeImage('player/3/jump/3.png')]],
            'use':    [[normalizeImage('player/3/use/1.png')],      [normalizeImage('player/3/use/2.png')]],
            'ladder': [[normalizeImage('player/3/ladder/1.png')],   [normalizeImage('player/3/ladder/2.png')],   [normalizeImage('player/3/ladder/3.png')]],
            'walk':   [[normalizeImage('player/3/walk/1.png'), 38], [normalizeImage('player/3/walk/2.png'), 38], [normalizeImage('player/3/walk/3.png'), 38], [normalizeImage('player/3/walk/4.png'), 38]]
        })]

        loadMap(f'map{level}.txt', tiles)
    else:
        loadMenu()

# -------------------------------------------------------------------------- #



# collisions
# -------------------------------------------------------------------------- #

def onCollisionFloor(arbiter, space, data, player):
    arbiter.friction = 1
    arbiter.elasticity = 1

    if arbiter.total_impulse[1] > 0:
        player.onPlatform = False

    return True

def onCollisionWall(arbiter, space, data, player):
    if arbiter.normal[0] > 0.9:
        player.collidesL = True
        player.collisionSkipRL = 5
    elif arbiter.normal[0] < -0.9:
        player.collidesR = True
        player.collisionSkipRL = 5

    if player.collisionSkipRL > 0:
        player.collisionSkipRL -= 1
    else:
        player.collidesL = False
        player.collidesR = False
    return True

def onCollisionPlatform(arbiter, space, data, player):
    if arbiter.normal[1] < -0.9:
        player.onPlatform = True
    arbiter.friction = 1

    return True

def onCollisionBox(arbiter, space, data, player, box):
    arbiter.friction = 1

    if arbiter.normal[0] > 0.9:
        if player.type == 2:
            box.body.apply_force_at_local_point((-100000, 0), (32, 32))
        player.boxM = True
        player.boxMTicks = player.boxMTimeout

    elif arbiter.normal[0] < -0.9:
        if player.type == 2:
            box.body.apply_force_at_local_point((100000, 0), (32, 32))
        player.boxM = True
        player.boxMTicks =  player.boxMTimeout

    return True

def onCollisionBoxFloor(arbiter, space, data, box):
    arbiter.friction = 1
    return True

def onCollisionBullet(arbiter, space, data):
    print(1)
    return True

space.add_collision_handler(0, 2).pre_solve = lambda a, s, d: onCollisionFloor(a, s, d, players[gameData['state']])
space.add_collision_handler(1, 2).pre_solve = lambda a, s, d: onCollisionWall(a, s, d, players[gameData['state']])
space.add_collision_handler(2, 2).pre_solve = lambda a, s, d: False
space.add_collision_handler(5, 2).pre_solve = lambda a, s, d: onCollisionPlatform(a, s, d, players[gameData['state']])
space.add_collision_handler(8, 1).begin = onCollisionBullet

# -------------------------------------------------------------------------- #



# utils
# -------------------------------------------------------------------------- #

def normalizeImage(image, m = 4):
    img = pygame.image.load(image)
    w, h = img.get_size()

    return pygame.transform.scale(img, (w * m, h * m))

def resetLevel():
    global toDraw, kinematicBehaviours, ladders, menuButtons, boxes, electricity
    space = pymunk.Space()
    space.gravity = (0.0, 900.0)
    
    toDraw = [[], []]
    kinematicBehaviours = []
    ladders = []
    menuButtons = []
    boxes = []
    electricity = []

    for s in space.shapes:
        space.remove(s.body, s)

# -------------------------------------------------------------------------- #


# menu update
def menu(events):
    global instruction, credits
    if gameData['level'] == -1:
        for event in events:
            if event.type == pygame.K_RETURN:
                instruction += 1
        
        loadInstruction(instruction)

    elif gameData['level'] == -2:
        credits[1] = (credits[1][0], credits[1][1] - 0.2)
        for event in events:
            if event.type == pygame.K_RETURN:
                changeLevel(0)

        if credits[1][1] < -credits[2]:
            changeLevel(0)

        screen.blit(credits[0], credits[1])

    elif gameData['level'] == 0:
        for bk in menuButtons.keys():
            buttonAnimation = menuButtons[bk][0]
            buttonFrame = buttonAnimation[0]
            if menuButtons[bk].get_rect().collidepoint(pygame.mouse.get_pos()):
                for event in events:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        buttonFrame = buttonAnimation[2]

                    elif event.type == pygame.MOUSEBUTTONUP:
                        if bk == 'start':
                            changeLevel(1)

                        elif bk == 'exit':
                            exit()

                        elif bk == 'help':
                            gameData['level'] = -1
                            instruction = 1

                        elif bk == 'credits':
                            gameData['level'] = -2
                            loadCredits()

                        elif bk == 'sound' or bk == 'music':
                            temp = menuButtons[bk][0]
                            menuButtons[bk][0] = menuButtons[bk][2]
                            menuButtons[bk][2] = temp

                            if bk == 'sound':
                                if sounds:
                                    sounds = False
                                else:
                                    sounds = True
                            else:
                                if music:
                                    music = False
                                else:
                                    music = True
                    else:
                        buttonFrame = buttonAnimation[1]

            screen.blit(buttonFrame, menuButtons[bk][1])


# settings
def settings(show):
    global sounds, music

# game update
def game(events):
    for event in events:
        # key pressed
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if gameData['paused']:
                    gameData['paused'] = False
                    settings(False)
                else:
                    gameData['paused'] = True
                    settings(True)

            
            elif event.key == pygame.K_SPACE and gameData['splitted']:
                gameData['state'] = 1 if gameData['state'] == 2 else 2
            elif event.key == pygame.K_LCTRL:
                if gameData['splitted']:
                    red = players[1].sprite.get_rect()
                    blue = players[2].sprite.get_rect()
                    if red.colliderect(blue):
                        gameData['splitted'] = False
                        gameData['state'] = 0

                else:
                    gameData['splitted'] = True
                    gameData['state'] = 1
                    players[2].body.position = players[1].body.position = players[0].body.position

    for t in toDraw[0]:
        screen.blit(t[0][gameData['state']], t[1])

    if gameData['paused']:
        players[gameData['state']].draw()
        for b in kinematicBehaviours:
            b.draw()

    else:
        players[gameData['state']].update(events)
        for b in kinematicBehaviours:
            b.step()

    for t in toDraw[1]:
        screen.blit(t[0][gameData['state']], t[1])

    space.step(tick)

toDraw = [[], []]
kinematicBehaviours = []
ladders = []
players = []
boxes = []
electricity = []

sounds, music = True, True

gameData = {
    'splitted': False,
    'state': 0,
    'paused': False,
    'level': 1
}

tiles = {
    '1': [[normalizeImage('tiles/16dcl.png')], 1],
    '2': [[normalizeImage('tiles/16dcr.png')], 1],
    '3': [[normalizeImage('tiles/16dl.png')], 1],
    '4': [[normalizeImage('tiles/16dm.png')], 1],
    '5': [[normalizeImage('tiles/16dr.png')], 1],
    '6': [[normalizeImage('tiles/16ml.png')], 1],
    '7': [[normalizeImage('tiles/16mm.png')], 1],
    '8': [[normalizeImage('tiles/16mr.png')], 1],
    '9': [[normalizeImage('tiles/16tcl.png')], 1],
    'a': [[normalizeImage('tiles/16tcr.png')], 1],
    'b': [[normalizeImage('tiles/16tl.png')], 1],
    'c': [[normalizeImage('tiles/16tm.png')], 1],
    'd': [[normalizeImage('tiles/16tr.png')], 1],
    '_': [[normalizeImage('assets/bar.png')], 2, [(0, 0), (64, 0), (64, 16), (0, 16)], Platform((1024, 0))],
    '-': [[normalizeImage('assets/bar.png')], 2, [(0, 0), (64, 0), (64, 16), (0, 16)], Platform((1024, 0))],
    'B': [[normalizeImage('assets/box.png')], 3, [(-24, -24), (24, -24), (-24, 24), (24, 24)], Box()],
    'L': [[normalizeImage('assets/ladder.png')], 8]
}

time1 = time.time()

changeLevel(1)

# game loop
while True:
    screen.fill((0, 0, 0))

    # time counter
    time2 = time.time()
    wait = tick - (time2 - time1)
    time1 = time.time()

    # events
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            exit()

    if gameData['level'] > 0:
        game(events)

    else:
        menu(events)

    if wait > 0:
        time.sleep(wait)
    pygame.display.flip()