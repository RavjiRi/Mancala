"""
Congklak written in Python.

This file is the controller for the main mancala.py on:
    - Creating a congklak board
    - Moving seeds (stones equivalent in mancala)
    - and more...

Author: Ritesh Ravji
"""

import itertools
from pathlib import Path
from time import sleep, time
from typing import Union, Iterable
from random import random, randint

# PEP: in order to preserve continuity, use camel case variable names
# this is because Panda3D is built on C so it uses camel case.

try:
    from panda3d.core import *
    from panda3d.physics import *
    from direct.task import *
except ImportError:
    raise ImportError(
        '''Please import the panda3d library to run this program
You can do this using pip or https://docs.panda3d.org/1.10/python/introduction/index''')

# Bitmasks are like collision groups
# if the 'from' and 'to' objects have at least one digit in common
# a collision test is attempted, learn more here:
# https://docs.panda3d.org/1.10/python/programming/collision-detection/collision-bitmasks

# seperate bitmasks for the mancala pits so then less calculations are done
# saves collision calculation between different stones in different pits which
# will never collide (this saves a lot of work as there 48 stones)

BITMASKS = {
        0: {
            0: BitMask32(0x1),  # 0000 0000 0000 0000 0000 0000 0000 0001
            1: BitMask32(0x2),  # 0000 ... 0010
            2: BitMask32(0x4),  # 0000 ... 0100
            3: BitMask32(0x8),
            4: BitMask32(0x10),
            5: BitMask32(0x20),
            6: BitMask32(0x1000),
            7: BitMask32(0x1),
            8: BitMask32(0x1),
            9: BitMask32(0x1),
            10: BitMask32(0x1),
            11: BitMask32(0x1),
            12: BitMask32(0x1),
            13: BitMask32(0x1),
            14: BitMask32(0x1),
            15: BitMask32(0x1),
            16: BitMask32(0x1),
            17: BitMask32(0x1),
            18: BitMask32(0x1)
            },
        1: {
            0: BitMask32(0x40),  # 0000 0000 0000 0000 0000 0000 0100 0000
            1: BitMask32(0x80),  # 0000 ... 1000 0000
            2: BitMask32(0x100),  # 0000 ... 0001 0000 0000
            3: BitMask32(0x200),
            4: BitMask32(0x400),
            5: BitMask32(0x800),
            6: BitMask32(0x2000),
            7: BitMask32(0x1),
            8: BitMask32(0x1),
            9: BitMask32(0x1),
            10: BitMask32(0x1),
            11: BitMask32(0x1),
            12: BitMask32(0x1),
            13: BitMask32(0x1),
            14: BitMask32(0x1),
            15: BitMask32(0x1),
            16: BitMask32(0x1),
            17: BitMask32(0x1),
            18: BitMask32(0x1)
            }
    }


class ColourGenerator:
    """Random colour generator."""

    def __init__(self) -> None:
        """Define an array of colours."""
        self.COLOURS = [
            (.85, 0, 0, 0),  # red
            (0, .85, 0, 0),  # green
            (0, 0, .85, 0),  # blue
            (.85, 0, .85, 0)  # pink
            ]

    def __next__(self) -> Iterable[Union[float, float, float, float]]:
        """Return a random colour."""
        return self.COLOURS[randint(0, len(self.COLOURS)-1)]

    def __iter__(self):
        """Return iterator."""
        return self


class main():
    """Functions that are required and called by the main code."""

    def __init__(self, app: object) -> None:
        """Setup the class variables.

        This function is run when the class is initalised
        Setup the variables required for the rest of the class

        Args:
            app (object): The Mancala.py main class responsible for the app and window
        Returns:
            None
        """
        # _ means weak internal use
        # these should not be accessed from outside the class
        self._APP = app  # store app for use outside init function
        # y positions of clickables from left to right
        # not constant as it is reversed later
        self._y_pos_click = [13.8, 9.8, 5.8, 1.9, -1.9, -5.8, -9.8, -13.8]
        # x positions of clickables
        # (player 0 side x pos is -2 and player 1 is 2)
        self._X_POS_CLICK = [(-6, -2), (6, 2)]
        self._winner = None  # _ means it is a protected variable (PEP)
        self._turn = 0  # player 0 goes first

        # these can be accessed from outside the class
        self.stones = {}  # dictionary to store stones
        self.clickables = {}  # dictionary to store clickables
        self.hoverables = {}  # dictionary to store hoverables
        self.STONES_PER_PIT = 1
        self.STONES_TIMEOUT = 5
        # path to congklak assets folder
        self.CONGKLAK_ASSETS = Path(__file__).parent.resolve()/'bao_assets'

        self._STR_INSTRUCTIONS = self._instructionsFromFile()

    def load(self) -> None:
        """Load the board on to the scene (render).

        This function is called by the main Mancala.py file
        Set up and load the board, place stones, setup collisions, etc

        Args:
            None
        Returns:
            None
        """
        APP = self._APP  # save space by dropping self

        # this is so the main code can tell what objects can be clicked on
        APP.CLICKABLE_TAG = "clickable"

        # setup camera
        APP.camera.setPos(-30, 0, 40)  # by experimentation of what looks nice
        APP.camera.lookAt(0, 0, 0)  # look the the board which is at the center
        APP.camLens.setFov(50)  # default FOV is 40

        # debug but NOT recommended because of how much the program slows down
        # traverser.showCollisions(app.render)

        # setup directional light for the mancala board
        # as it does not show up without it...
        LIGHT = DirectionalLight("light")
        LIGHT.setColor((1, 1, 1, 1))
        LIGHT.setShadowCaster(True, 1024, 1024)
        LNP = APP.render.attachNewNode(LIGHT)  # light node path
        LNP.setPos(0, 0, 100)
        LNP.setHpr(0, -90, 0)  # heading, yaw, pitch (the angle of light)
        APP.render.setLight(LNP)  # add light to render (the scene)

        # setup mancala board
        self.BOARD = APP.loader.loadModel(self.CONGKLAK_ASSETS/'BaoBoardComplete.obj',
                                          noCache=True)
        # rotate because I made the model wrong...
        self.BOARD.setP(self.BOARD, 90)
        self.BOARD.reparentTo(APP.render)

        COLOUR_GENERATOR = ColourGenerator()

        # loop through the board parts
        # two sides because of two players
        for side in range(2):
            self.stones[side] = {}
            self.clickables[side] = {}
            self.hoverables[side] = {}

            # clickable obj nth from left
            for n in range(8*2):
                layer = n//8
                # create board collisions for each pit
                pit = APP.loader.loadModel(self.CONGKLAK_ASSETS/'collision_assets/BaoCollision.obj', noCache=True)
                pit.setP(pit, 90)
                x_pos = self._X_POS_CLICK[side][layer]  # x pos of the pit
                y_pos = self._y_pos_click[n%8]  # y pos of the pit
                pit.setPos(x_pos, y_pos, 1)
                pit.reparentTo(APP.render)
                pit.hide()  # make sure it is not visible
                for model in pit.find_all_matches("**/+GeomNode"):
                    # add a collide mask so stones in the pit don't fall through
                    model.setCollideMask(BITMASKS[side][n])

                # create clickable points
                clickable = APP.loader.loadModel('models/misc/sphere')
                self.clickables[side][n] = clickable
                self.hoverables[side][n] = clickable  # all clickables can be hovered over

                clickable.setPos(x_pos, y_pos, 1)
                clickable.setScale(1.5, 1.5, 1.5)
                clickable.reparentTo(APP.render)
                # change name though it is not important
                clickable.name = 'clickable ' + str(side) + "-" + str(n)
                # this is how we will tell if we clicked the clickable
                clickable.setTag(APP.CLICKABLE_TAG, "True")
                clickable.setTag('hover', "True")  # it is hoverable
                # it is on the side of player 0/1
                clickable.setTag('side', str(side))
                clickable.setTag('n', str(n))  # nth from the left
                clickable.hide()  # make invisible

                # store stones in array in dictionaries
                self.stones[side][n] = []
                for count in range(self.STONES_PER_PIT):
                    # location of clickable object for later
                    x, y, z = clickable.getPos()
                    stone = APP.loader.loadModel('models/misc/sphere')
                    self.stones[side][n].append(stone)
                    stone.setScale(0.35, 0.35, 0.35)
                    stone.setColor(next(COLOUR_GENERATOR))

                    # start physics logic
                    node = NodePath("PhysicsNode")
                    node.reparentTo(APP.render)
                    an = ActorNode("stone-physics")
                    panp = node.attachNewNode(an)
                    APP.physicsMgr.attachPhysicalNode(an)
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
                    cn.setFromCollideMask(BITMASKS[side][n])
                    # used when the stone is collided into
                    cn.setIntoCollideMask(BITMASKS[side][n])
                    cnode_path = panp.attachNewNode(cn)
                    cnode_path.node().addSolid(cs)  # attach collision sphere
                    APP.pusher.addCollider(cnode_path, panp)  # add to physics pusher which keeps it out of other objects
                    APP.cTrav.addCollider(cnode_path, APP.pusher)  # add to traverser which handles physics
                    # show collision objects for debugging
                    # cnodePath.show()

                if layer == 0 and n%8==7:
                    # if it is the last pit in the outer layer
                    # reverse list so the first stones load on the right
                    # so the path is counter clockwise
                    self._y_pos_click.reverse()
            # reverse list so the first stones load on the left
            #self._y_pos_click.reverse()

        # backup collsion 'floor' in case the stones fall through the model
        plane = CollisionPlane(Plane(Vec3(0, 0, 1), Point3(0, 0, -0.5)))
        cn = CollisionNode('plane')
        np = APP.render.attachNewNode(cn)
        np.node().addSolid(plane)

        self.gameComplete = False

    def clickedPit(self, clickedSide: int, clickedN: int, **kwargs) -> None:
        """Move the stones for the given clicked pit.

        This function is called by the main Mancala.py file
        The whole turn is run on this function
        
        Args:
            clickedSide (int): The side that is clicked
            clickedN (int): The pit nth from the left that is clicked
            **kwargs: Optional keyword args, the original clicked side and clicked n
                oClickedSide (int): the original side that is clicked
                oClickedN (int): the original nth pit that is clicked
        Returns:
            None
        """
        app = self._APP  # save space by dropping self
        clickedStones = self.stones[clickedSide][clickedN]

        # save for when seeds are captured
        oClickedSide = kwargs.get('oClickedSide', clickedSide)
        oClickedN = kwargs.get('oClickedN', clickedN)

        side = clickedSide
        n = clickedN
        # repeat for the # of stones in the clicked pit
        for i in range(len(clickedStones)):
            currentPit = self.hoverables[side][n]
            goTo = currentPit.getPos()+Vec3(0, 0, 5)

            self._moveStones(clickedStones, goTo)
            sleep(1)
            self._releaseAllStones()

            side, n = self._nextPit(side, n)  # get the next pit

            if side != self._turn and n == 6:
                # about to drop in the opponents store
                # skip per the rules
                side, n = self._nextPit(side, n)  # get the next pit

            goTo = self.hoverables[side][n].getPos()+Vec3(0, 0, 5)

            self._moveStones(clickedStones, goTo)
            sleep(1)
            self._releaseAllStones()

            for stone in clickedStones:
                # stop stones from moving
                # in case it has any glitchy velocity
                self._setStationary(stone)

            # pop removes last stone in array and return it
            droppedStone = clickedStones.pop()
            cn = droppedStone.getParent().find('cnode').node()  # collision node
            # set the collide masks to the collide mask of the new pit
            cn.setFromCollideMask(BITMASKS[side][n])
            cn.setIntoCollideMask(BITMASKS[side][n])
            self.stones[side][n].append(droppedStone)  # add to new pit
            # just incase, stop the stone from moving
            self._setStationary(droppedStone)
        # no more stones in the clicked pit

        (adjSide1, adjN1), (adjSide2, adjN2) = self._adjPits(side, n)

        if (side == self._turn and len(self.stones[side][n]) >= 1 and n//8 == 1
            and len(self.stones[adjSide1][adjN1]) and len(self.stones[adjSide2][adjN2])):
            # the last stone landed on:
            #   their own side
            #   AND it is the inner pit (n//8) is 1
            #   AND adj stones are not empty
            #   AND was not previously empty/is was occupied (now it has more than one stone)
            # as per the rules, pick up adj stones the stone and redistribute
            currentPit = self.hoverables[side][n]
            goTo = currentPit.getPos()+Vec3(0, 0, 5)

            adjPit1 = self.hoverables[adjSide1][adjN1]
            adjPit2 = self.hoverables[adjSide2][adjN2]
            adj1GoTo = adjPit1.getPos()+Vec3(0, 0, 5)
            adj2GoTo = adjPit2.getPos()+Vec3(0, 0, 5)

            # hover over the respective pits
            self._moveStones(self.stones[side][n], goTo)
            self._moveStones(self.stones[adjSide1][adjN1], adj1GoTo)
            self._moveStones(self.stones[adjSide2][adjN2], adj2GoTo)

            sleep(0.5)

            # hover over the starting pit as per the rules
            hoverPit = self.hoverables[oClickedSide][oClickedN]
            goTo = hoverPit.getPos()+Vec3(0, 0, 5)
            self._releaseAllStones()

            # hover over the starting pit
            self._moveStones(self.stones[side][n], goTo)
            self._moveStones(self.stones[adjSide1][adjN1], goTo)
            self._moveStones(self.stones[adjSide2][adjN2], goTo)

            # because the stone could potentially move from one side to the other
            # wait for the stones to arrive at the seed store
            self._waitForStones(self.stones[adjSide1][adjN1], goTo)
            self._waitForStones(self.stones[adjSide2][adjN2], goTo)
            self._waitForStones(self.stones[side][n], goTo)

            self._releaseAllStones()
            for stone in itertools.chain(self.stones[adjSide1][adjN1], self.stones[adjSide2][adjN2], self.stones[side][n]):
                # pop removes last stone in array and return it
                # dropped_stone = self.stones[adj_side][adj_n].pop()
                cn = stone.getParent().find('cnode').node()  # collision node
                # set the collide masks to the collide mask of the new pit
                cn.setFromCollideMask(BITMASKS[oClickedSide][oClickedN])
                cn.setIntoCollideMask(BITMASKS[oClickedSide][oClickedN])
                self.stones[oClickedSide][oClickedN].append(stone)  # add to seed store

                # stop stones from moving
                # in case it has any glitchy velocity
                self._setStationary(stone)
            self.stones[adjSide1][adjN1].clear()
            self.stones[adjSide2][adjN2].clear()
            self.stones[side][n].clear()
        elif len(self.stones[side][n]) > 1:
            # the last stone landed on:
            #   has at least one stone previously (so more than one stone now)
            # as per the rules, continue going around
            sleep(1.5)  # some time for the stones to drop into the pit
            return self.clickedPit(side, n, oClickedSide = oClickedSide, oClickedN = oClickedN)

        # if there are no more stones on one side of the board...
        if self._sumStones(0) == 0 or self._sumStones(1) == 0:
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

        #if side == self._turn and n == 6:
        #    # last stone landed in the stone store so go again
        #    pass
        elif self._turn == 0:
            self._turn = 1
        else:
            self._turn = 0

    @property
    def turn(self) -> int:
        """Return the current turn.

        This function has a property decorator so it can be accessed like a variable/property
        This means self._turn is not exposed and is less likely to be externally edited

        Args:
            None
        Returns:
            The current turn (player 0 or 1)
        """
        return self._turn

    def isGameComplete(self) -> bool:
        """Return if the game is complete.

        Args:
            None
        Returns:
            If the game is complete (bool)
        """
        return self.gameComplete

    @property
    def instructions(self) -> str:
        """Return the instructions.

        The instructions are saved at class init and is should be retrieved here

        Args:
            None
        Returns:
            The game instructions (str)
        """
        return self._STR_INSTRUCTIONS

    @property
    def winner(self) -> Union[int, str]:
        """Return the winner.

        This function has a property decorator so it can be accessed like a variable/property
        This means self._winner is not exposed and is less likely to be externally edited

        Args:
            None
        Returns:
            The winner (player 0 or 1 or tie)
        """
        return self._winner

    # Code used by the this class only
    # single leading underscore means weak 'internal use' (PEP)

    def _instructionsFromFile(self) -> str:
        """Read the instructions file and return its contents.

        This function is called at class init

        Args:
            None
        Returns:
            The game instructions (str)
        """
        try:
            rules_txt = open(self.CONGKLAK_ASSETS/"rules.txt", mode='r')
        except FileNotFoundError:
            print('no instructions!')
            return ''
        instructions = ""
        with rules_txt as file:
            instructions = file.read()

        return instructions

    def _alignPosition(self, task: str, stone: NodePath, goTo: Vec3):
        """Gradually move stone to position.

        Moves stone to position, this is blocking so run the background with Task

        Args:
            task (str): The name of the task passed through
            stone (NodePath): The stone represented by Panda3D as a node path
            goTo (Vec3): A Panda3D class containing x, y, z coords to move to
        Returns:
            Task.cont (int): A constant used internally by Panda3D
                this is to show the function is completed
                (see Panda3D documentation for more)
        """
        an = stone.getParent().node()  # actor node
        # physics object, look at panda3d docs for more
        phyObj = an.getPhysicsObject()
        thruster = stone.get_parent()  # this should be a node path

        maxSpeed = 10  # the max speed possible when moving the stone
        moveVec = (goTo-thruster.get_pos())  # direction*size from current stone position to go_to
        moveDir = moveVec.normalized()  # direction
        moveDist = moveVec.length()  # size
        ratio = (2/(1+pow(2.7, -moveDist))-1)  # sigmoid function, to calculate the speed of the stone
        phyObj.setVelocity(moveDir*maxSpeed*ratio)
        return Task.cont  # task finished (see panda3d task docs)

    def _waitForStones(self, stones: list, pos: Vec3) -> bool:
        """Wait for stones to move to the position.

        Args:
            stones (list): The list of clicked stones to wait for
            pos (Vec3): A Panda3D class containing x, y, z coords to reach
        Returns:
            atPos (bool): If the stones have reached the position
        """
        atPos = False  # are all stones are at pos
        startTime = time()
        while not atPos or time()-startTime >= self.STONES_TIMEOUT:
            sleep(0.1)
            atPos = True
            for stone in stones:
                thruster = stone.get_parent()  # this should be a node path
                if (thruster.getPos()-pos).length() >= 0.5:
                    atPos = False  # not at position!
        return atPos

    def _moveStones(self, clickedStones: list, goTo: Vec3) -> None:
        """Moves clicked stones to position.

        Stones are move to go_to in the background, so it is non-blocking

        Args:
            clickedStones (list): The list of clicked stones to move
            goTo (Vec3): A Panda3D class containing x, y, z coords to move to
        Returns:
            None
        """
        for stone in clickedStones:
            # hover above the current pit
            self._APP.taskMgr.add(
                self._alignPosition, "moveTask",
                extraArgs=["moveTask", stone, goTo]
            )

    def _releaseAllStones(self) -> None:
        """Release all the stones.

        Stones will no longer be moved by move_stones in the background

        Args:
            None
        Returns:
            None
        """
        self._APP.taskMgr.removeTasksMatching("moveTask")

    def _nextPit(self, side: int, n: int) -> tuple:
        """Return the next pit to the right.

        A function to make moving the stones easier.

        Args:
            side (int): The side of the pit
            n (int): the nth from the left
        Returns:
            The side and nth from the left of the next pit
        """
        n += 1
        if n >= 16:
            n = 0
        return side, n

    def _adjPits(self, side: int, n: int) -> tuple:
        """Return the adjacent pits on the opponents side.

        Args:
            side (int): The side of the pit
            n (int): the nth from the left
        Returns:
            The adjacent pits ((side: int, n: int), (side: int, n: int))
        """
        return (-side+1, n-8), (-side+1, -n+23)

    def _sumStones(self, plr: int) -> int:
        """Return the total stones on the given side.

        Args:
            plr (int): Sum for player 0 or 1
        Returns:
            The total stone of the given side
        """
        # sum stones for player 1 or 0
        return sum(len(self.stones[plr][n]) for n in range(6))

    def _setStationary(self, stone: NodePath) -> None:
        """Set the stone stationary (no velocity).

        Args:
            stone (NodePath): The stone represented by Panda3D as a node path
        Returns:
            None
        """
        an = stone.getParent().node()
        phyObj = an.getPhysicsObject()

        phyObj.setVelocity(Vec3(0, 0, 0))
