"""
This file is the controller for the main mancala.py on:
    - Creating a congklak board
    - Moving seeds (stones equivalent in mancala)
    - and more...
"""

from panda3d.core import *
from panda3d.physics import *
from direct.task import *
from time import sleep, time
from random import random, randint
from pathlib import Path
import itertools

# Bitmasks are like collision groups
# if the 'from' and 'to' objects have at least one digit in common
# a collision test is attempted, learn more here:
# https://docs.panda3d.org/1.10/python/programming/collision-detection/collision-bitmasks

# seperate bitmasks for the mancala pits so then less calculations are done
# saves collision calculation between different stones in different pits which
# will never collide (this saves a lot of work as there 48 stones)

BitMasks = {
        0: {
            0: BitMask32(0x1),  # 0000 0000 0000 0000 0000 0000 0000 0001
            1: BitMask32(0x2),  # 0000 ... 0010
            2: BitMask32(0x4),  # 0000 ... 0100
            3: BitMask32(0x8),
            4: BitMask32(0x10),
            5: BitMask32(0x20),
            6: BitMask32(0x1000)  # bit mask for plr 0 mancala
            },
        1: {
            0: BitMask32(0x40),  # 0000 0000 0000 0000 0000 0000 0100 0000
            1: BitMask32(0x80),  # 0000 ... 1000 0000
            2: BitMask32(0x100),  # 0000 ... 0001 0000 0000
            3: BitMask32(0x200),
            4: BitMask32(0x400),
            5: BitMask32(0x800),
            6: BitMask32(0x2000)  # bit mask for plr 1 mancala
            }
    }


class ColourGenerator():
    """Random colour generator."""

    def __init__(self):
        """Define an array of colours."""
        self.COLOURS = [
            (.85, 0, 0, 0),  # red
            (0, .85, 0, 0),  # green
            (0, 0, .85, 0),  # blue
            (.85, 0, .85, 0)  # pink
            ]

    def next(self):
        """Return a random colour."""
        return self.COLOURS[randint(0, len(self.COLOURS)-1)]


class main():
    """Functions that are required and called by the main code."""

    #__slots__ = []
    def __init__(self, app):
        """Setup the class variables."""
        self._app = app  # store app for use outside init function
        # y positions of clickables from left to right
        self._y_pos_click = [9.8, 5.8, 1.9, -1.9, -5.8, -9.8]
        # x positions of clickables
        # (player 0 side x pos is -2 and player 1 is 2)
        self._x_pos_click = [-2, 2]
        self.stones = {}  # dictionary to store stones
        self.clickables = {}  # dictionary to store clickables
        self.hoverables = {}  # dictionary to store hoverables
        self.stonesPerPit = 1#7
        self.stones_timeout = 5 # move stones timeout
        self._winner = None # _ means it is a protected variable (PEP)
        self._turn = 0  # player 0 goes first
        # path to congklak assets folder
        self.congklak_assets = Path(__file__).parent.resolve()/'congklak_assets'
        self._str_instructions = self._instructions_from_file()

    def load(self):
        """Load the board on to the scene (render)."""
        app = self._app  # save space by dropping self

        # this is so the main code can tell what objects can be clicked on
        app.clickableTag = "clickable"

        # setup camera
        app.camera.setPos(-30, 0, 40)  # by experimentation of what looks nice
        app.camera.lookAt(0, 0, 0)  # look the the board which is at the center
        app.camLens.setFov(50)  # default FOV is 40

        # debug but NOT recommended because of how much the program slows down
        # traverser.showCollisions(app.render)

        # setup directional light for the mancala board
        # as it does not show up without it...
        light = DirectionalLight("light")
        light.setColor((1, 1, 1, 1))
        light.setShadowCaster(True, 1024, 1024)
        lnp = app.render.attachNewNode(light)  # light node path
        lnp.setPos(0, 0, 100)
        lnp.setHpr(0, -90, 0)  # heading, yaw, pitch (the angle of light)
        app.render.setLight(lnp)  # add light to render (the scene)

        # setup mancala board
        self.board = app.loader.loadModel(self.congklak_assets/'mancala.obj', noCache=True)
        # rotate because I made the model wrong...
        self.board.setP(self.board, 90)
        self.board.setR(self.board, 10)
        self.board.reparentTo(app.render)

        random_colour = ColourGenerator()

        # loop through the board parts
        # two sides because of two players
        for side in range(2):
            self.stones[side] = {}
            self.clickables[side] = {}
            self.hoverables[side] = {}
            # clickable obj nth from left
            for n in range(6):
                # create board collisions for each pit
                pit = app.loader.loadModel(self.congklak_assets/'collision_assets/Player{}/{}.obj'.format(side, n), noCache=True)
                pit.setP(pit, 90)
                pit.reparentTo(app.render)
                pit.hide()  # make sure it is not visible
                for model in pit.find_all_matches("**/+GeomNode"):
                    # add a collide mask so stones in the pit don't fall through
                    model.setCollideMask(BitMasks[side][n])

                # create clickable points
                clickable = app.loader.loadModel('models/misc/sphere')
                self.clickables[side][n] = clickable
                self.hoverables[side][n] = clickable  # all clickables can be hovered over
                x_pos = self._x_pos_click[side]  # x pos of the pit
                y_pos = self._y_pos_click[n]  # y pos of the pit
                clickable.setPos(x_pos, y_pos, 1)
                clickable.setScale(1.5, 1.5, 1.5)
                clickable.reparentTo(app.render)
                # change name though it is not important
                clickable.name = 'clickable ' + str(side) + "-" + str(n)
                # this is how we will tell if we clicked the clickable
                clickable.setTag(app.clickableTag, "True")
                clickable.setTag('hover', "True")  # it is hoverable
                # it is on the side of player 0/1
                clickable.setTag('side', str(side))
                clickable.setTag('n', str(n))  # nth from the left
                clickable.hide()  # make invisible

                # store stones in array in dictionaries
                self.stones[side][n] = []
                for count in range(self.stonesPerPit):
                    # location of clickable object for later
                    x, y, z = clickable.getPos()
                    stone = app.loader.loadModel('models/misc/sphere')
                    self.stones[side][n].append(stone)
                    stone.setScale(0.35, 0.35, 0.35)
                    stone.setColor(random_colour.next())

                    # start physics logic
                    node = NodePath("PhysicsNode")
                    node.reparentTo(app.render)
                    an = ActorNode("stone-physics")
                    panp = node.attachNewNode(an)
                    app.physicsMgr.attachPhysicalNode(an)
                    stone.reparentTo(panp)

                    # set stone position
                    # when we move the stone we must move the node path Panp
                    # this is because Panp is moved by the physics system
                    panp.setPos(x+random()/4, y+random()/4, 5+count*5)  # add random() to add a randomness to the stone scattering

                    # create a collision sphere which will set how the stone looks to the collision system
                    cs = CollisionSphere(stone.getBounds().getCenter(), 0.35)
                    cn = CollisionNode('cnode')

                    # from objects are the 'moving' objs
                    # into objects are the non moving 'walls'

                    # used when the stone is colliding into
                    cn.setFromCollideMask(BitMasks[side][n])
                    # used when the stone is collided into
                    cn.setIntoCollideMask(BitMasks[side][n])
                    cnode_path = panp.attachNewNode(cn)
                    cnode_path.node().addSolid(cs)  # attach collision sphere
                    app.pusher.addCollider(cnode_path, panp)  # add to physics pusher which keeps it out of other objects
                    app.cTrav.addCollider(cnode_path, app.pusher)  # add to traverser which handles physics
                    # show collision objects for debugging
                    # cnodePath.show()
            # board collisions for the stone stores
            # this is where the stones are banked
            segment = app.loader.loadModel(self.congklak_assets/"collision_assets/Player{}/Mancala.obj".format(side), noCache=True)
            segment.setP(segment, 90)
            segment.reparentTo(app.render)
            segment.hide()  # should not be visible
            for model in segment.find_all_matches("**/+GeomNode"):
                # add a collide mask so stones in the mancala don't fall through
                # the mancala is the 6th from the left
                model.setCollideMask(BitMasks[side][6])
            self.stones[side][6] = []  # create the array to store stones in mancala
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
            self._y_pos_click.reverse()

        # backup collsion 'floor' in case the stones fall through the model
        plane = CollisionPlane(Plane(Vec3(0, 0, 1), Point3(0, 0, -0.5)))
        cn = CollisionNode('plane')
        np = app.render.attachNewNode(cn)
        np.node().addSolid(plane)

        self.gameComplete = False

    def clicked_pit(self, clicked_side, clicked_n):
        """Move the stones for the given clicked pit."""
        app = self._app  # save space by dropping self
        clicked_stones = self.stones[clicked_side][clicked_n]

        side = clicked_side
        n = clicked_n
        # repeat for the # of stones in the clicked pit
        for i in range(len(clicked_stones)):
            current_pit = self.hoverables[side][n]
            go_to = current_pit.getPos()+Vec3(0, 0, 5)

            self.move_stones(clicked_stones, go_to)
            sleep(1)
            self.release_all_stones()

            side, n = self.next_pit(side, n)  # get the next pit

            if side != self._turn and n == 6:
                # about to drop in the opponents store
                # skip per the rules
                side, n = self.next_pit(side, n)  # get the next pit

            go_to = self.hoverables[side][n].getPos()+Vec3(0, 0, 5)

            self.move_stones(clicked_stones, go_to)
            sleep(1)
            self.release_all_stones()

            for stone in clicked_stones:
                # stop stones from moving
                # in case it has any glitchy velocity
                self.set_stationary(stone)

            # pop removes last stone in array and return it
            dropped_stone = clicked_stones.pop()
            cn = dropped_stone.getParent().find('cnode').node()  # collision node
            # set the collide masks to the collide mask of the new pit
            cn.setFromCollideMask(BitMasks[side][n])
            cn.setIntoCollideMask(BitMasks[side][n])
            self.stones[side][n].append(dropped_stone)  # add to new pit
            # just incase, stop the stone from moving
            self.set_stationary(dropped_stone)
        # no more stones in the clicked pit

        if side == self._turn and len(self.stones[side][n]) == 1 and n != 6:
            # the last stone landed on:
            #   their own side
            #   AND was previously empty (now it has one stone)
            #   AND it is not a seed store (has to be a pit)
            # as per the rules, bank the stone and the adj stones
            current_pit = self.hoverables[side][n]
            go_to = current_pit.getPos()+Vec3(0, 0, 5)
            
            adj_side, adj_n = self.adj_pit(side, n)
            adj_pit = self.hoverables[adj_side][adj_n]
            adj_go_to = adj_pit.getPos()+Vec3(0, 0, 5)

            # hover over the respective pits
            self.move_stones(self.stones[side][n], go_to)
            self.move_stones(self.stones[adj_side][adj_n], adj_go_to)

            seed_store = self.hoverables[self._turn][6]
            go_to = seed_store.getPos()+Vec3(0, 0, 5)
            self.release_all_stones()

            # hover over the seed store
            self.move_stones(self.stones[side][n], go_to)
            self.move_stones(self.stones[adj_side][adj_n], go_to)

            # because the stone could potentially move from one side to the other
            # wait for the stones to arrive at the seed store
            self.wait_for_stones(self.stones[adj_side][adj_n], go_to)
            self.wait_for_stones(self.stones[side][n], go_to)

            self.release_all_stones()
            for stone in itertools.chain(self.stones[adj_side][adj_n], self.stones[side][n]):
                # pop removes last stone in array and return it
                # dropped_stone = self.stones[adj_side][adj_n].pop()
                cn = stone.getParent().find('cnode').node()  # collision node
                # set the collide masks to the collide mask of the new pit
                cn.setFromCollideMask(BitMasks[self._turn][6])
                cn.setIntoCollideMask(BitMasks[self._turn][6])
                self.stones[self._turn][6].append(stone)  # add to seed store
                
                # stop stones from moving
                # in case it has any glitchy velocity
                self.set_stationary(stone)
            self.stones[adj_side][adj_n].clear()
            self.stones[side][n].clear()
        elif len(self.stones[side][n]) > 1 and n != 6:
            # the last stone landed on:
            #   has at least one stone previously (so more than one stone now)
            #   AND it is not a seed store (has to be a pit)
            # as per the rules, continue going around
            sleep(1.5) # some time for the stones to drop into the pit
            return self.clicked_pit(side, n)

        # if there are no more stones on one side of the board...
        if self.sum_stones(0) == 0 or self.sum_stones(1) == 0:
            # there are no more stones on one side of the board
            # this means game is finished
            self.gameComplete = True
            if len(self.stones[0][6]) > len(self.stones[1][6]):
                # player 0 has more stones in their store
                self._winner = 0
            elif len(self.stones[0][6]) < len(self.stones[1][6]):
                # player 1 has more stones in their store
                self._winner = 1
            else:
                self._winner = "TIE"

        if side == self._turn and n == 6:
            # last stone landed in the stone store so go again
            pass
        elif self._turn == 0:
            self._turn = 1
        else:
            self._turn = 0

    @property
    def turn(self):
        """Return the current turn.

        This function has a property decorator so it can be accessed like a variable/property
        This means self._turn is not exposed and is less likely to be externally edited
        """
        return self._turn

    def is_game_complete(self):
        """Return if the game is complete."""
        return self.gameComplete

    def _instructions_from_file(self):
        rules_txt = open(self.congklak_assets/"rules.txt", mode='r')
        instructions = ""
        with rules_txt as file:
            instructions = file.read()

        return instructions

    @property
    def instructions(self):
        return self._str_instructions

    @property
    def winner(self):
        """Return the winner.

        This function has a property decorator so it can be accessed like a variable/property
        This means self._winner is not exposed and is less likely to be externally edited
        """
        return self._winner

    ''' code used by the this class only '''
    def align_position(self, task, stone, go_to: Vec3):
        """Gradually move stone to position."""
        an=stone.getParent().node()  # actor node
        # physics object, look at panda3d docs for more
        phy_obj = an.getPhysicsObject()
        thruster = stone.get_parent()  # this should be a node path

        max_speed = 10  # the max speed possible when moving the stone
        move_vec = (go_to-thruster.get_pos())  # direction*size from current stone position to go_to
        move_dir = move_vec.normalized()  # direction
        move_dist = move_vec.length()  # size
        ratio = (2/(1+pow(2.7, -move_dist))-1)  # sigmoid function, to calculate the speed of the stone
        phy_obj.setVelocity(move_dir*max_speed*ratio)
        return Task.cont  # task finished (see panda3d task docs)

    def wait_for_stones(self, stones, pos: Vec3):
        '''Wait for stones to move to the pos
        '''
        atPos = False # are all stones are at pos
        startTime = time()
        while not atPos or time()-startTime >= self.stones_timeout:
            sleep(0.1)
            atPos = True
            for stone in stones:
                thruster = stone.get_parent()  # this should be a node path
                if (thruster.getPos()-pos).length() >= 0.5:
                    atPos = False # not at position!
        return atPos
    def move_stones(self, clicked_stones, go_to: Vec3):
        for stone in clicked_stones:
            # hover above the current pit
            self._app.taskMgr.add(
                self.align_position, "moveTask",
                extraArgs=["moveTask", stone, go_to]
            )

    def release_all_stones(self):
        self._app.taskMgr.removeTasksMatching("moveTask")

    def next_pit(self, side, n):
        """Return the next pit to the right.

        A function to make moving the stones easier.

        Args:
            side (int): The side of the pit
            n (int): the nth from the left

        Returns:
            The side and nth from the left of the next pit
        """
        n += 1
        if n >= 7:
            n = 0
            if side == 0:
                side = 1
            else:
                side = 0
        return side, n

    def adj_pit(self, side, n):
        """Return the adjacent pit"""
        return -side+1, 5-n

    def sum_stones(self, plr):
        """Return the total stones on the given side."""
        # sum stones for player 1 or 0
        return sum(len(self.stones[plr][n]) for n in range(6))

    def set_stationary(self, stone):
        """Set the stone stationary (no velocity)."""
        an=stone.getParent().node()
        phy_obj = an.getPhysicsObject()

        phy_obj.setVelocity(Vec3(0, 0, 0))
