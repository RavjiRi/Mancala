"""
Mancala written in Python.

This program was written for Computer Science CSC335 at WHS.
This program uses and is written with the Panda3D library.
Click START to play the classic mancala!

Version: 27/5/24

Author: Ritesh Ravji
"""

# don't check for these libraries as these are core libraries
import sys
import threading
import importlib.util  # importing gamemodes
from os import _exit  # exit the program
from time import sleep
from queue import Queue  # store mouse clicks
from pathlib import Path
from codecs import decode  # decode instructions from file
from warnings import warn
from random import randint
from types import ModuleType  # module class for type hints
from datetime import datetime  # get time for logs
from argparse import ArgumentParser  # cli args

# PEP: in order to preserve continuity, use camel case variable names
# this is because Panda3D is built on C so it uses camel case.

WORKING_DIRECTORY = Path(__file__).parent.resolve()

# in case of local installation of Panda3D
# add command line arguments to add the install path
# from the root directory this should look like:
# "python3 Mancala.py --Panda3D H:\\Downloads\\Mancala\\Panda3D"
# from the current directory this should look like:
# "python3 Mancala.py --Panda3D Panda3D"
PARSER = ArgumentParser()
PARSER.add_argument("--Panda3D", default=None, type=Path,
                    help="run Panda3D from a local installation")
ARGS = PARSER.parse_args()

if ARGS.Panda3D:
    # command line arguments to use local installation of Panda3D
    if not ARGS.Panda3D.exists():
        raise FileNotFoundError("The path '{}' does not exist".format(ARGS.Panda3D))

    #PANDA3D_INSTALL = WORKING_DIRECTORY/'Panda3D'  # path of panda3d install
    PANDA3D_INSTALL = ARGS.Panda3D # path of panda3d install
    sys.path.append(PANDA3D_INSTALL.as_posix())

try:
    from direct.showbase.ShowBase import ShowBase
    from direct.gui.DirectGui import *
    from direct.task import *
    from panda3d.core import *
    from panda3d.physics import *
except ImportError:
    raise ImportError(
        '''Please import the panda3d library to run this program
You can do this using pip or https://docs.panda3d.org/1.10/python/introduction/index''')

USE_TKINTER = False

try:
    import Pmw  # Python mega widgets
except ImportError:
    warn('''The Pmw library is recommended for a better experience
Any popup windows when selecting a gamemode may be hidden behind the main app window''',
         RuntimeWarning)

    # import modules that will used as a workaround for not having Pmw
    from subprocess import Popen, PIPE
else:
    # successful import of Pmw
    # tkinter is allowed to load (can conflict with panda3d without Pmw)
    # so tell panda3d that tkinter can load with want-tk true
    loadPrcFileData("", "want-tk true")

    # unlock FPS
    loadPrcFileData("", "sync-video false")

    # line 3330:
    # https://github.com/panda3d/panda3d/blob/master/direct/src/showbase/ShowBase.py
    # allow tkinter to handle main loop for better response from MacOS
    loadPrcFileData("", "tk-main-loop true")

    # increase frame rate (even though max is 60 fps usually)
    # this is because the FPS with Pmw is 30 when it is set at 60 FPS
    loadPrcFileData("", "tk-frame-rate 120.0")

    USE_TKINTER = True
    import tkinter.filedialog

loadPrcFileData("", "load-file-type p3assimp")  # obj files can be loaded

LOG_TIME = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

# this suppresses output when run from command line
# also good for debugging
# not a big problem if the log folder is missing
# this will mean that there is some text from Panda3D at the start
loadPrcFileData("", "notify-output {}/logs/{}.txt".format(WORKING_DIRECTORY,
  LOG_TIME))  # log output

class Mancala(ShowBase):
    """Class that is responsible for the app and window.

    This class inherits Panda3D ShowBase
    """

    def __init__(self) -> None:
        """Start the app and window."""
        ShowBase.__init__(self)  # start the module (creates window)
        self.disableMouse()  # disable camera control with the mouse
        base.setFrameRateMeter(True)  # show frame rate
        self.set_background_color(1, 1, 1, 1)
        properties = WindowProperties()
        properties.setTitle('Mancala')
        self.win.requestProperties(properties)  # set window properties

        if USE_TKINTER:
            self.tkRoot = base.tkRoot
            self.tkRoot.withdraw()  # stop the empty popup window

        self.win.setCloseRequestEvent('window_closed')
        self.accept('window_closed', self.windowClosed)

        self.enableParticles()  # starts physics

        # handle physics collisions by automatically pushing colliding objects
        self.pusher = PhysicsCollisionHandler()
        self.pusher.setDynamicFrictionCoef(0.5)  # add friction
        self.pusher.setStaticFrictionCoef(1)

        # automatically handle physics operations
        self.cTrav = CollisionTraverser('physics')

        self.CLICKABLE_TAG = "clickable"  # clickable objects have this tag
        self.ROBOTO = self.loader.loadFont("fonts/Roboto/Roboto-Regular.ttf")
        self.ROBOTO_BOLD = self.loader.loadFont("fonts/Roboto/Roboto-Bold.ttf")

        self.module = self.loadGamemode(WORKING_DIRECTORY/'gamemodes/classic.py')
        self.controller = self.module.main(self)  # game controller
        self.controller.load()  # load board from external file

        self.startGravity()
        self.startMouse()

        self.TURN_TEXT = DirectLabel(text='Your turn',
                                     pos=(0, 0, 0.8), text_scale=(0.15, 0.15),
                                     frameColor=(0, 0, 0, 0), textMayChange=True,
                                     parent=aspect2d, text_font=self.ROBOTO)

        self.TURN_TEXT.hide()

        # create a new daemon thread (daemon threads close with main thread)
        # this is because a while loop starts and this is blocking
        # the app window will freeze if this happens
        self.startGameThread = threading.Thread(target=self.startGame, args=(), daemon=True)

        # start the thread when clicked
        self.ST_BUTTON = DirectButton(text="START",
                                      scale=.05, command=self.startGameThread.start,
                                      frameSize=(-2, 2, -1, 1))
        self.GM_BUTTON = DirectButton(text="GAMEMODE",
                                      scale=.05, command=self.popupWindowOpen,
                                      frameSize=(-2, 2, -1, 1), pos=(0, 0, -0.3),
                                      text_scale=(0.6, 0.6))
        self.INS_BUTTON = DirectButton(text="INSTRUCTIONS",
                                       scale=.05, command=self.openInstructions,
                                       frameSize=(-2.3, 2.3, -1, 1), pos=(0, 0, -0.6),
                                       text_scale=(0.6, 0.6))
        self.MM_BUTTON = DirectButton(text='MAIN MENU',
                                      scale=.05, command=self.reset,
                                      frameSize=(-5, 5, -2.5, 2.5), pos=(0, 0, -0.3),
                                      text_scale=(1.5, 1.5))
        self.MM_BUTTON.hide()

    def clearScene(self) -> None:
        """Clear the scene.

        Clears the scene to be ready for a new board
        Removes everything but the camera

        Args:
            None
        Returns:
            None
        """
        for i in self.render.getChildren():
            if i.name != 'camera':
                i.removeNode()
        self.render.clearLight()

    def onMouseClick(self) -> None:
        """Run this function when the mouse is clicked.

        This uses code from the Panda3D documentation
        https://docs.panda3d.org/1.10/python/programming/collision-detection/clicking-on-3d-objects

        Args:
            None
        Returns:
            None
        """
        MOUSE = base.mouseWatcherNode.getMouse()  # get mouse
        # sets collsion ray to start at camera and extend to inf in mouse direction
        self.PICKER_RAY.setFromLens(base.camNode, MOUSE.getX(), MOUSE.getY())

        self.cTrav.traverse(self.render)  # detect collisions

        if self.MOUSE_HANDLER.getNumEntries() > 0:
            # This is so we get the closest object
            self.MOUSE_HANDLER.sortEntries()
            pickedObj = self.MOUSE_HANDLER.getEntry(0).getIntoNodePath()

            self.MOUSE_Q.queue.clear()  # empty queue
            self.MOUSE_Q.put(pickedObj)  # put clicked obj in queue

    def startMouse(self) -> None:
        """Setup collision-based mouse clicker.

        This uses code from the Panda3D documentation
        https://docs.panda3d.org/1.10/python/programming/collision-detection/clicking-on-3d-objects

        Args:
            None
        Returns:
            None
        """
        self.MOUSE_HANDLER = CollisionHandlerQueue()
        self.PICKER_NODE = CollisionNode('mouseRay')
        # attach collision node to camera
        self.PICKER_NP = self.camera.attachNewNode(self.PICKER_NODE)
        self.PICKER_NODE.setFromCollideMask(GeomNode.getDefaultCollideMask())
        self.PICKER_RAY = CollisionRay()
        # add the collision ray to the collision node
        self.PICKER_NODE.addSolid(self.PICKER_RAY)
        # detect collisions from pickerNP and handle with myHandler
        self.cTrav.addCollider(self.PICKER_NP, self.MOUSE_HANDLER)

        # store mouse clicks in a queue so if you want to wait for mouse click, call the blocking Queue.get()
        self.MOUSE_Q = Queue()
        # run onMouseClick when mouse is clicked
        self.accept('mouse1', self.onMouseClick)

    def reset(self) -> None:
        """Reset the game.

        Reload the board, set back to main menu

        Args:
            None
        Returns:
            None
        """
        self.clearScene()

        self.disableGravity()

        self.controller = self.module.main(self)  # game controller

        self.controller.load()  # load board from external file

        # create a new Thread otherwise an error occurs
        # "RuntimeError: threads can only be started once"
        self.startGameThread = threading.Thread(target=self.startGame, args=(), daemon=True)
        self.ST_BUTTON["command"] = self.startGameThread.start

        self.ST_BUTTON.show()
        self.GM_BUTTON.show()
        self.INS_BUTTON.show()
        self.TURN_TEXT.hide()
        self.MM_BUTTON.hide()

    def openInstructions(self) -> None:
        """Open the instructions.

        Opens the instructions and add bold characters, etc
        Uses Panda3D text properties
        https://docs.panda3d.org/1.10/python/programming/gui/embedded-text-properties

        Args:
            None
        Returns:
            None
        """
        
        TP_BOLD = TextProperties()
        TP_BOLD.setFont(self.ROBOTO_BOLD)
        TP_MGR = TextPropertiesManager.getGlobalPtr()
        TP_MGR.setProperties('bold', TP_BOLD)

        INS_TEXT = self.controller.instructions
        # direct gui cannot apply bold unless \1 and \2 are ascii
        # so decode the raw str from file to 'unicode_escape'
        INS_TEXT = decode(INS_TEXT, 'unicode_escape')

        # create an inital height for the canvas
        canvasHeight = 5

        # instructions frame
        self.ins_frame = DirectScrolledFrame(pos=(0, -1, 0.65), frameColor=(0.5, 0.5, 0.5, 1),
                         canvasSize = (-1/2, 1/2, -.1, canvasHeight), frameSize=(-0.7, 0.7, -1.5, 0.1))
        self.ins_label = DirectLabel(text=INS_TEXT,
                                  parent = self.ins_frame.getCanvas(), frameColor=(0, 0, 0, 0),
                                  pos=(0, 0, canvasHeight-0.1), text_font=self.ROBOTO,
                                  text_wordwrap=12, text_scale=0.1, text_align=TextNode.ACenter)
        
        # Panda3D as far as I am aware of doesn't have a good system
        # for fixing text within a specific height
        # this might get a bit messy...

        # so get the height of the button
        w1, w2, h1, h2 = self.ins_label.getBounds()
        textHeight = abs(h1)+abs(h2) # h1 may be negative

        # set the canvas height as text height
        self.ins_frame['canvasSize']=(-1/2, 1/2, -.1, textHeight)
        # re center the text
        self.ins_label.setPos(0.2, 0, abs(h1)-0.05)

        self.exit_ins = DirectButton(text="CLOSE",
                         scale=.05,
                         command=self.closeInstructions,
                         frameSize=(-0.7/.05, 0.7/.05, -1, 1),
                         pos=(0, 0, -0.9),
                         text_scale=(0.6, 0.6))

    def closeInstructions(self) -> None:
        """Close the instructions.

        Args:
            None
        Returns:
            None
        """
        self.ins_frame.destroy()
        self.exit_ins.destroy()

    def loadGamemode(self, path: str) -> ModuleType:
        """Load gamemode as a module.

        The selected gamemode is imported using importlib

        Args:
            path (str): system path to file
        Returns:
            module (ModuleType)
        """
        # check the path to gamemode folder exists
        if not Path(path).exists():
            raise FileNotFoundError('''The gamemode folder was not found...
Make sure the gamemode folder is present in the same directory as this script''')
        # import file directly
        # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
        spec = importlib.util.spec_from_file_location("gamemode", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    def popupWindowOpen(self) -> None:
        """Create a popup file browser to select gamemode.

        Creates a popup using tkinter to select a gamemode
        The selected gamemode is imported using importlib

        Args:
            None
        Returns:
            None
        """
        gamemodePath = None
        if USE_TKINTER:
            file = tkinter.filedialog.askopenfile(parent=self.tkRoot,
                                                  initialdir=WORKING_DIRECTORY/'gamemodes',
                                                  title='Please select a directory',
                                                  filetypes=[("Python files", ".py")])
            if not file:
                # the user clicked close...
                return
            gamemodePath = file.name
            file.close()
        else:
            process = Popen(['python', WORKING_DIRECTORY/'popen.py'], stdout=PIPE, stderr=PIPE)
            stdout, stderr = process.communicate()
            gamemodePath = stdout.decode('utf-8')
            if not gamemodePath:
                # the user clicked close...
                return

        self.module = self.loadGamemode(gamemodePath)
        self.controller = self.module.main(self)  # game controller

        self.clearScene()

        self.controller.load()  # load board from external file

    def startGravity(self) -> None:
        """Setup gravity on the scene.

        Args:
            None
        Returns:
            None
        """
        GRAVITY_FN = ForceNode('world-forces')
        GRAVITY_FNP = self.render.attachNewNode(GRAVITY_FN)
        self.GRAVITY_FORCE = LinearVectorForce(0, 0, -9.8)  # gravity acceleration
        GRAVITY_FN.addForce(self.GRAVITY_FORCE)

    def enableGravity(self) -> None:
        """Enable gravity on the scene.

        Args:
            None
        Returns:
            None
        """
        self.physicsMgr.addLinearForce(self.GRAVITY_FORCE)

    def disableGravity(self) -> None:
        """Disable gravity on the scene.

        Args:
            None
        Returns:
            None
        """
        self.physicsMgr.removeLinearForce(self.GRAVITY_FORCE)

    def windowClosed(self) -> None:
        """On window closed event, destroy the window and exit program.

        Args:
            None
        Returns:
            None
        """
        self.destroy()
        _exit(0)  # fully restart (closes window on mac)

    def returnClickedPit(self) -> NodePath:
        """Return the clicked pit.

        Wait for click and check if it is a valid clicked object (a pit and on the players side)

        Args:
            None
        Returns:
            clickedPit (NodePath): The clicked pit node path
        """
        clickedPit = None
        while not clickedPit:
            # blocking, so it will wait until a value is placed in queue
            clickedObj = self.MOUSE_Q.get()
            # check if clicked is a clickable
            pickedObj = clickedObj.findNetTag(self.CLICKABLE_TAG)
            if not pickedObj.isEmpty():
                # clicked on clickable
                side = int(pickedObj.getTag('side'))
                n = int(pickedObj.getTag('n'))
                if side == 0 and len(self.controller.stones[side][n]):
                    # is on plr 0 side and not empty
                    clickedPit = pickedObj

        return clickedPit

    def startGame(self) -> None:
        """Start the game.

        This should be run on another thread and run when start button is clicked

        Args:
            None
        Returns:
            None
        """
        self.enableGravity()

        # hide the buttons
        self.ST_BUTTON.hide()
        self.GM_BUTTON.hide()
        self.INS_BUTTON.hide()

        controller = app.controller  # game controller

        # the max number (ceiling) the rng can generate (because of the amount of clickables)
        CHOICE_CEIL = len(controller.clickables[1])-1

        while not controller.isGameComplete():
            turn = controller.turn
            self.TURN_TEXT.show()
            if turn == 0:
                # change the text to "Your turn"
                self.TURN_TEXT['text'] = "Your turn"
                clickedObj = app.returnClickedPit()
                self.TURN_TEXT.hide()

                # the side of the selected pit
                clickedSide = int(clickedObj.getTag('side'))
                # the nth pit from the left that is selected
                clickedN = int(clickedObj.getTag('n'))
            else:
                # change the text to "Opponents turn"
                self.TURN_TEXT['text'] = "Opponents turn"
                hasStones = False
                while not hasStones:
                    n = randint(0, CHOICE_CEIL)
                    clickedSide = 1
                    clickedN = n
                    if len(controller.stones[1][n]):
                        # keep generating a new pit until it has stones
                        hasStones = True

            controller.clickedPit(clickedSide, clickedN)
        if controller.winner == 0:
            print("You win!")
            self.TURN_TEXT['text'] = "You win!"
        elif controller.winner == 1:
            print("You lose...")
            self.TURN_TEXT['text'] = "You lose..."
        else:
            print("You tie")
            self.TURN_TEXT['text'] = "Tie"
        self.TURN_TEXT.show()
        self.MM_BUTTON.show()


# main guard for threading
if __name__ == "__main__":
    app = Mancala()

    app.run()
