from panda3d.core import *
from panda3d.physics import *
from time import sleep
from random import random, randint

# Bitmasks are like collision groups
# if the 'from' and 'to' objects have at least one digit in commo
# a collision test is attempted
# learn more here: https://docs.panda3d.org/1.10/python/programming/collision-detection/collision-bitmasks

# seperate bitmasks for the mancala pits so then less calculations are done
# saves collision calculation between different stones in different pits which
# will never collide (this saves a lot of work as there 48 stones)

BitMasks = {
        0: {
            0: BitMask32(0x1), # 0000 0000 0000 0000 0000 0000 0000 0001
            1: BitMask32(0x2), # 0000 ... 0010
            2: BitMask32(0x4), # 0000 ... 0100
            3: BitMask32(0x8),
            4: BitMask32(0x10),
            5: BitMask32(0x20),
            6: BitMask32(0x1000) # bit mask for plr 0 mancala
            },
        1: {
            0: BitMask32(0x40), # 0000 0000 0000 0000 0000 0000 0100 0000
            1: BitMask32(0x80), # 0000 ... 1000 0000
            2: BitMask32(0x100), # 0000 ... 0001 0000 0000
            3: BitMask32(0x200),
            4: BitMask32(0x400),
            5: BitMask32(0x800),
            6: BitMask32(0x2000) # bit mask for plr 1 mancala
            }
    }

class ColourGenerator():
    def __init__(self):
        self.COLOURS = [
            (.85, 0, 0, 0), # red
            (0, .85, 0, 0), # green
            (0, 0, .85, 0), # blue
            (.85, 0, .85, 0) # pink
            ]
    def next(self):
        # return a random colour
        return self.COLOURS[randint(0, len(self.COLOURS)-1)]

class Classic():
    ''' functions that are required and called by the main code '''
    def __init__(self, app):
        ''' setup the class variables '''
        self.app = app # store app for use outside init function
        # y positions of clickables from left to right
        self.y_pos_click = [9.8, 5.8, 1.9, -1.9, -5.8, -9.8]
        # x positions of clickables (player 0 side x pos is -2 and player 1 is 2)
        self.x_pos_click = [-2, 2]
        self.stones = {} # dictionary to store stones
        self.clickables = {} # dictionary to store clickables
        self.hoverables = {} # dictionary to store hoverables
        self.stonesPerPit = 4
    def load(self):
        app = self.app # save space by dropping self

        # this is so the main code can tell what objects can be clicked on
        app.clickableTag = "clickable"
        
        # setup camera
        app.camera.setPos(-30, 0, 40) # by experimentation of what looks nice
        app.camera.lookAt(0,0,0) # look the the board which is at the center
        app.camLens.setFov(50) # default FOV is 40

        # debug but NOT recommended because of how much the program slows down
        # traverser.showCollisions(app.render)
        
        # setup directional light for the mancala board as it does not show up without it...
        light = DirectionalLight("light")
        light.setColor((1, 1, 1, 1))
        light.setShadowCaster(True, 1024, 1024)
        lnp = app.render.attachNewNode(light) # light node path
        lnp.setPos(0, 0, 100)
        lnp.setHpr(0, -90, 0) # heading, yaw, pitch (the angle of light)
        app.render.setLight(lnp) # add light to render (the scene)
        
        # setup mancala board
        self.board = app.loader.loadModel("gamemodes/classic_assets/mancala.obj", noCache=True) # noCache=True
        self.board.setP(self.board, 90) # rotate because I made the model wrong...
        self.board.setR(self.board, 10)
        self.board.reparentTo(app.render)

        RandomColour = ColourGenerator()
        
        # loop through the board parts
        # two sides because of two players
        for side in range(2):
            self.stones[side] = {}
            self.clickables[side] = {}
            self.hoverables[side] = {}
            # clickable obj nth from left
            for n in range(6):
                # create board collisions for each pit
                pit = app.loader.loadModel("gamemodes/classic_assets/collision_assets/Player{}/{}.obj".format(side, n), noCache=True)
                pit.setP(pit, 90)
                pit.reparentTo(app.render)
                pit.hide() # make sure it is not visible
                for model in pit.find_all_matches("**/+GeomNode"):
                    # add a collide mask so stones in the pit don't fall through
                    model.setCollideMask(BitMasks[side][n])

                # create clickable points
                clickable = app.loader.loadModel('models/misc/sphere')
                self.clickables[side][n] = clickable
                self.hoverables[side][n] = clickable # all clickables can be hovered over
                x_pos = self.x_pos_click[side] # x pos of the pit
                y_pos = self.y_pos_click[n] # y pos of the pit
                clickable.setPos(x_pos, y_pos, 1)
                clickable.setScale(1.5, 1.5, 1.5)
                clickable.reparentTo(app.render)
                clickable.name='clickable ' + str(side) + "-" + str(n) # change name though it is not important
                clickable.setTag(app.clickableTag, "True") # this is how we will tell if we clicked the clickable
                clickable.setTag('hover', "True") # it is hoverable
                clickable.setTag('side', str(side)) # it is on the side of player 0/1
                clickable.setTag('n', str(n)) # nth from the left
                clickable.hide() # make invisible

                # stones
                self.stones[side][n] = [] # store stones in array in dictionaries
                for count in range(self.stonesPerPit):
                    x, y, z = clickable.getPos() # location of clickable object for later
                    stone = app.loader.loadModel('models/misc/sphere')
                    self.stones[side][n].append(stone)
                    stone.setScale(0.35, 0.35, 0.35)
                    stone.setColor(RandomColour.next())
                    
                    # start physics logic
                    node = NodePath("PhysicsNode")
                    node.reparentTo(app.render)
                    an = ActorNode("stone-physics")
                    Panp=node.attachNewNode(an)
                    app.physicsMgr.attachPhysicalNode(an)
                    stone.reparentTo(Panp)

                    # set stone position
                    # when we move the stone we must move the node path Panp as Panp is moved by the physics system
                    Panp.setPos(x+random()/4, y+random()/4, 5+count*5) # add random() to add a randomness to the stone scattering
                    
                    # create a collision sphere which will set how the stone looks to the collision system
                    cs = CollisionSphere(stone.getBounds().getCenter(), 0.35)
                    cn = CollisionNode('cnode')
                    
                    # from objects are the 'moving' objs
                    # into objects are the non moving 'walls'
                    cn.setFromCollideMask(BitMasks[side][n]) # used when the stone is colliding into
                    cn.setIntoCollideMask(BitMasks[side][n]) # used when the stone is collided into
                    cnodePath = Panp.attachNewNode(cn)
                    cnodePath.node().addSolid(cs) # attach collision sphere
                    app.pusher.addCollider(cnodePath, Panp) # add to physics pusher which keeps it out of other objects
                    app.cTrav.addCollider(cnodePath, app.pusher) # add to traverser which handles physics
                    # show collision objects for debugging
                    # cnodePath.show() 
            # board collisions for the mancala (where the stones go, not the board itself)
            segment = app.loader.loadModel("gamemodes/classic_assets/collision_assets/Player{}/Mancala.obj".format(side), noCache=True)
            segment.setP(segment, 90)
            segment.reparentTo(app.render)
            segment.hide() # should not be visible
            for model in segment.find_all_matches("**/+GeomNode"):
                # add a collide mask so stones in the mancala don't fall through
                # the mancala is the 6th from the left
                model.setCollideMask(BitMasks[side][6])
            self.stones[side][6] = [] # create the array to store stones in mancala
            # create hoverable point
            hoverable = app.loader.loadModel('models/misc/sphere')
            self.hoverables[side][6] = hoverable
            if side == 0:
                y_pos = -13.9
            else:
                y_pos = 13.9
            hoverable.setPos(0, y_pos, 1)
            hoverable.setScale(1.5, 1.5, 1.5)
            hoverable.hide()
            hoverable.setTag('hover', "True")
            hoverable.setTag('side', str(side))
            hoverable.setTag('n', str(6))
            hoverable.reparentTo(app.render)
            # reverse list so the first stones load on the left
            self.y_pos_click.reverse()

        # backup collsion 'floor' in case the stones fall through the model
        plane = CollisionPlane(Plane(Vec3(0, 0, 1), Point3(0, 0, -0.5)))
        cn = CollisionNode('plane')
        np = app.render.attachNewNode(cn)
        np.node().addSolid(plane)

        self.turn = 0 # player 0 goes first
        self.gameComplete = False
    def clickedPit(self, clicked_side, clicked_n):
        app = self.app # save space by dropping self
        clicked_stones = self.stones[clicked_side][clicked_n]
        
        side = clicked_side
        n = clicked_n
        # while clicked_stones is NOT empty
        while clicked_stones:
            currentPit = self.hoverables[side][n]
            go_to = currentPit.getPos()+Vec3(0, 0, 5)
            for stone in clicked_stones:
                # hover above the current pit
                task = app.taskMgr.add(app.alignPosition, "moveTask", extraArgs=["moveTask", stone, go_to])
            sleep(1)
            app.taskMgr.removeTasksMatching("moveTask")

            side, n = self.next_pit(side, n) # get the next pit
            go_to = self.hoverables[side][n].getPos()+Vec3(0, 0, 5)
            for stone in clicked_stones:
                # move above the next pit
                task = app.taskMgr.add(app.alignPosition, "moveTask", extraArgs=["moveTask", stone, go_to])
            sleep(1)
            app.taskMgr.removeTasksMatching("moveTask")
            for stone in clicked_stones:
                # stop stones from moving
                self.setStationary(stone)
            
            droppedStone = clicked_stones.pop() # remove last stone in array and return it
            cn = droppedStone.getParent().find('cnode').node() # collision node
            # set the collide masks to the collide mask of the new pit
            cn.setFromCollideMask(BitMasks[side][n])
            cn.setIntoCollideMask(BitMasks[side][n])
            self.stones[side][n].append(droppedStone) # add to new pit
            self.setStationary(droppedStone) # just incase, stop the stone from moving
        # no more stones in the clicked pit
        if self.sumStones(0) == 0 or self.sumStones(1) == 0:
            # there are no more stones on one side of the board, game is finished
            self.gameComplete = True
            if len(self.stones[0][6]) > len(self.stones[1][6]):
                # player 0 has more stones in their mancala
                self.winner = 0
            elif len(self.stones[0][6]) < len(self.stones[1][6]):
                # player 1 has more stones in their mancala
                self.winner = 1
            else:
                self.winner = "TIE"
        if self.turn == 0:
            self.turn = 1
        else:
            self.turn = 0
    def getTurn(self):
        return self.turn
    def isGameComplete(self):
        return self.gameComplete
    def getWinner(self):
        return self.winner
    ''' code used by the this class only '''
    def next_pit(self, side, n):
        n+=1
        if n>=7:
            n=0
            if side == 0:
                side = 1
            else:
                side = 0
        return side, n
    def sumStones(self, plr):
        # sum stones for player 1 or 0
        return sum(len(self.stones[plr][n]) for n in range(6))
    def setStationary(self, stone):
        an=stone.getParent().node()
        phyObj = an.getPhysicsObject()

        phyObj.setVelocity(Vec3(0, 0, 0))
