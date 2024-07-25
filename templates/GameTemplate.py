"""
'GAMEMODE' mancala written in Python.

This file is the controller for the main mancala.py on:
    - Creating a mancala board
    - Moving stones
    - and more...

Author: YOUR NAME
"""

try:
    from panda3d.core import *
    from panda3d.physics import *
    from direct.task import *
except ImportError:
    raise ImportError(
        '''Please import the panda3d library to run this program
You can do this using pip or https://docs.panda3d.org/1.10/python/introduction/index''')


# This is a sort-of template that explains how to make a game mode
# it might be easier to read the classic gamemode though...

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
        self._y_pos_click = []
        # x positions of clickables
        # (player 0 side x pos is -2 and player 1 is 2)
        self._X_POS_CLICK = []
        self._winner = None  # _ means it is a protected variable (PEP)
        self._turn = 0  # player 0 goes first

        # these can be accessed from outside the class
        # definitley keep these variables
        self.stones = {}  # dictionary to store stones
        self.clickables = {}  # dictionary to store clickables
        self.hoverables = {}  # dictionary to store hoverables
        self.STONES_PER_PIT = 4
        # path to classic assets folder
        self.TEMPLATE_ASSETS = Path(__file__).parent.resolve()/'template_assets'
        if not self.TEMPLATE_ASSETS.exists():
            raise FileNotFoundError('''The template_assets folder was not found...
Make sure the template_assets folder is present in the same directory as GameTemplate.py''')

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

        # check for board assets
        # add your own 3D models using obj files
        if not (self.TEMPLATE_ASSETS/'mancala.obj').exists():
            raise FileNotFoundError('''The mancala.obj file was not found...
Make sure the file is present in the template_assets folder''')

        if not (self.TEMPLATE_ASSETS/'collision_assets').exists():
            raise FileNotFoundError('''The collision_assets folder was not found...
Make sure the folder is present in the template_assets folder''')

        if not (self.TEMPLATE_ASSETS/'mancala.mtl').exists():
            warn('''The mancala.mtl file was not found...
Make sure the file is present in the template_assets folder
The mancala board may appear grey without this file''',
                 RuntimeWarning)

        # setup mancala board
        self.BOARD = APP.loader.loadModel(self.TEMPLATE_ASSETS/'mancala.obj',
                                          noCache=True)
        # rotate because I made the model wrong...
        self.BOARD.setP(self.BOARD, 90)
        self.BOARD.setR(self.BOARD, 10)
        self.BOARD.reparentTo(APP.render)

        # loop through the board parts
        # two sides because of two players
        for side in range(2):
            self.stones[side] = {}
            self.clickables[side] = {}
            self.hoverables[side] = {}

            # check that the Player folders exist
            if not (self.TEMPLATE_ASSETS/'collision_assets/Player{}'.format(side)).exists():
                raise FileNotFoundError('''The Player{} folder was not found...
Make sure the folder is present in the collision_assets folder'''.format(side))

            # clickable obj nth from left
            for n in range(6):
                # check that the collision objs exist
                if not (self.TEMPLATE_ASSETS/'collision_assets/Player{}/{}.obj'.format(side, n)).exists():
                    raise FileNotFoundError('''The {}.obj file was not found...
Make sure the folder is present in the Player{} folder'''.format(n, side))

                # create board collisions for each pit
                pit = APP.loader.loadModel(
                    self.TEMPLATE_ASSETS/'collision_assets/Player{}/{}.obj'.format(side, n),
                    noCache=True)
                pit.reparentTo(APP.render)
                pit.hide()  # make sure it is not visible
                for model in pit.find_all_matches("**/+GeomNode"):
                    # add a collide mask so stones in the pit don't fall through

                # create clickable points
                clickable = APP.loader.loadModel('models/misc/sphere')
                self.clickables[side][n] = clickable
                self.hoverables[side][n] = clickable  # all clickables can be hovered over
                x_pos = self._X_POS_CLICK[side]  # x pos of the pit
                y_pos = self._y_pos_click[n]  # y pos of the pit
                clickable.setPos(x_pos, y_pos, 1)
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
                    panp.setPos(x, y, 5+count*5)

                    # create a collision sphere which will set how the stone looks to the collision system
                    cs = CollisionSphere(stone.getBounds().getCenter(), 0.35)
                    cn = CollisionNode('cnode')

                    # from objects are the 'moving' objs
                    # into objects are the non moving 'walls'

                    # used when the stone is colliding into
                    # add collisions to stones
                    #cn.setFromCollideMask(BITMASKS[side][n])
                    #cn.setIntoCollideMask(BITMASKS[side][n])
                    cnode_path = panp.attachNewNode(cn)
                    cnode_path.node().addSolid(cs)  # attach collision sphere
                    APP.pusher.addCollider(cnode_path, panp)  # add to physics pusher which keeps it out of other objects
                    APP.cTrav.addCollider(cnode_path, APP.pusher)  # add to traverser which handles physics
                    # show collision objects for debugging
                    # cnodePath.show()
            if not (self.TEMPLATE_ASSETS/'collision_assets/Player{}/Mancala.obj'.format(side)).exists():
                raise FileNotFoundError('''The Mancala.obj file was not found...
Make sure the folder is present in the Player{} folder'''.format(side))
            # board collisions for the stone stores
            # this is where the stones are banked
            segment = APP.loader.loadModel(self.TEMPLATE_ASSETS/"collision_assets/Player{}/Mancala.obj".format(side), noCache=True)
            segment.reparentTo(APP.render)
            segment.hide()  # should not be visible
            for model in segment.find_all_matches("**/+GeomNode"):
                # add a collide mask so stones in the store don't fall through
                # the stone store is the 6th from the left
            self.stones[side][6] = []  # create the array to store stones in
            # create hoverable point
            hoverable = APP.loader.loadModel('models/misc/sphere')
            self.hoverables[side][6] = hoverable
            if side == 0:
                #y_pos = -13.9
            else:
                #y_pos = 13.9
            hoverable.setPos(0, y_pos, 1)
            hoverable.setScale(1.5, 1.5, 1.5)
            hoverable.hide()
            hoverable.setTag('hover', "True")
            hoverable.setTag('side', str(side))
            hoverable.setTag('n', str(6))
            hoverable.reparentTo(APP.render)
            # reverse list so the first stones load on the left
            self._y_pos_click.reverse()

        # backup collsion 'floor' in case the stones fall through the model
        plane = CollisionPlane(Plane(Vec3(0, 0, 1), Point3(0, 0, -0.5)))
        cn = CollisionNode('plane')
        np = APP.render.attachNewNode(cn)
        np.node().addSolid(plane)

        self.gameComplete = False

    def clickedPit(self, clickedSide: int, clickedN: int) -> None:
        """Move the stones for the given clicked pit.

        This function is called by the main Mancala.py file
        The whole turn is run on this function
        
        Args:
            clickedSide (int): The side that is clicked
            clickedN (int): The pit nth from the left that is clicked
        Returns:
            None
        """

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

    def isGameComplete(self) -> bool:
        """Return if the game is complete.

        Args:
            None
        Returns:
            If the game is complete (bool)
        """

    @property
    def instructions(self) -> str:
        """Return the instructions.

        The instructions are saved at class init and is should be retrieved here

        Args:
            None
        Returns:
            The game instructions (str)
        """

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

    # Code used by the this class only can go after this
    # single leading underscore means weak 'internal use' (PEP)
