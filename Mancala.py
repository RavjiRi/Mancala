from time import sleep
from random import randint
from queue import Queue
import threading # don't check for these libraries as these are core libraries
import sys
import codecs
from warnings import warn
from pathlib import Path
import importlib.util
from os import _exit

# in case of local installation of Panda3D
working_directory = Path(__file__).parent.resolve()
panda3d_install = working_directory/'Panda3D' # path of panda3d install
sys.path.append(panda3d_install.as_posix())

try:
    from direct.showbase.ShowBase import ShowBase
    from direct.gui.DirectGui import *
    from direct.task import *
    from panda3d.core import *
    from panda3d.physics import *
except ImportError:
    raise ImportError("Please import the panda3d library to run this program using pip or https://docs.panda3d.org/1.10/python/introduction/index")

useTkinter = False
try:
    import Pmw # Python mega widgets
except ImportError:
    warn('''The Pmw library is recommended for a better experience
Any popup windows when selecting a gamemode may be hidden behind the main app window''', RuntimeWarning)

    # import modules that will used as a workaround for not having Pmw
    from subprocess import Popen, PIPE
else:
    # successful import of Pmw
    # tkinter is allowed to load (can conflict with panda3d without Pmw)
    # so tell panda3d that tkinter can load with want-tk true
    loadPrcFileData("", "want-tk true")

    # line 3330: https://github.com/panda3d/panda3d/blob/master/direct/src/showbase/ShowBase.py
    # allow tkinter to handle main loop for better response from MacOS
    loadPrcFileData("", "tk-main-loop true")
    
    # increase frame rate (even though max is 60 fps usually)
    # this is because the FPS with Pmw is 30 when it is set at 60 FPS
    loadPrcFileData("", "tk-frame-rate 120.0")

    useTkinter = True
    import tkinter.filedialog

loadPrcFileData("", "load-file-type p3assimp") # obj files can be loaded

class Mancala(ShowBase):
    """Class that is responsible for the app and window (inherits Panda3D ShowBase)"""
    def __init__(self):
        ShowBase.__init__(self) # start the module (creates window)
        self.disableMouse() # disable camera control with the mouse
        base.setFrameRateMeter(True) # show frame rate
        self.set_background_color(1, 1, 1, 1)
        properties = WindowProperties()
        properties.setTitle('Mancala')
        self.win.requestProperties(properties) # set window properties

        if useTkinter:
            self.tk_root = base.tkRoot
            self.tk_root.withdraw() # stop the empty popup window

        self.win.setCloseRequestEvent('window_closed')
        self.accept('window_closed', self.window_closed)
        
        self.enableParticles() # starts physics
        self.pusher = PhysicsCollisionHandler() # handle physics collisions by automatically pushing colliding objects
        self.pusher.setDynamicFrictionCoef(0.5) # add friction
        self.pusher.setStaticFrictionCoef(0)
        self.cTrav = CollisionTraverser('physics') # automatically handle physics operations

        self.clickableTag = "clickable" # clickable objects have this tag
        self.roboto = self.loader.loadFont("fonts/Roboto/Roboto-Regular.ttf")
        self.roboto_bold = self.loader.loadFont("fonts/Roboto/Roboto-Bold.ttf")

        from gamemodes.congklak import main
        self.controller = main(self) # game controller
        self.controller.load() # load board from external file
        
        self.enableGravity()
        self.startMouse()

        self.turnText = DirectLabel(text='Your turn',
                           pos=(0, 0, 0.8), text_scale = (0.15, 0.15), frameColor=(0, 0, 0, 0),
                           textMayChange=True, parent=aspect2d, text_font=self.roboto)
        self.turnText.hide()

        # create a new daemon thread (daemon threads close with main thread)
        # this is because a while loop starts and this is blocking
        # the app window will freeze if this happens
        t = threading.Thread(target=self.start_game, args=(), daemon=True)

        # start the thread when clicked
        self.st_button = DirectButton(text="START",
                         scale=.05, command=t.start, frameSize=(-2, 2, -1, 1))
        self.gm_button = DirectButton(text="GAMEMODE",
                         scale=.05,
                         command=self.PopupWindowOpen,
                         frameSize=(-2, 2, -1, 1),
                         pos=(0, 0, -0.3),
                         text_scale=(0.6, 0.6))
        self.ins_button = DirectButton(text="INSTRUCTIONS",
                         scale=.05,
                         command=self.OpenInstructions,
                         frameSize=(-2.3, 2.3, -1, 1),
                         pos=(0, 0, -0.6),
                         text_scale=(0.6, 0.6))

    def clearScene(self):
        """Clears the scene

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

    def onMouseClick(self):
        """This function runs when the mouse is clicked

        This uses code from the Panda3D documentation
        https://docs.panda3d.org/1.10/python/programming/collision-detection/clicking-on-3d-objects
        
        Args:
            None
        Returns:
            None
        """
        mpos = base.mouseWatcherNode.getMouse() # get mouse
        # sets collsion ray to start at camera and extend to inf in mouse direction
        self.pickerRay.setFromLens(base.camNode, mpos.getX(), mpos.getY())

        self.cTrav.traverse(self.render) # detect collisions

        if self.mouseHandler.getNumEntries() > 0:
            # This is so we get the closest object
            self.mouseHandler.sortEntries()
            pickedObj = self.mouseHandler.getEntry(0).getIntoNodePath()
            
            self.mouseq.queue.clear() # empty queue
            self.mouseq.put(pickedObj) # put clicked obj in queue
        
    def startMouse(self):
        """Setup collision-based mouse clicker

        This uses code from the Panda3D documentation
        https://docs.panda3d.org/1.10/python/programming/collision-detection/clicking-on-3d-objects

        Args:
            None
        Returns:
            None
        """
        self.mouseHandler = CollisionHandlerQueue()
        self.pickerNode = CollisionNode('mouseRay')
        # attach collision node to camera
        self.pickerNP = self.camera.attachNewNode(self.pickerNode)
        self.pickerNode.setFromCollideMask(GeomNode.getDefaultCollideMask())
        self.pickerRay = CollisionRay()
        # add the collision ray to the collision node
        self.pickerNode.addSolid(self.pickerRay)
        # detect collisions from pickerNP and handle with myHandler
        self.cTrav.addCollider(self.pickerNP, self.mouseHandler)

        # store mouse clicks in a queue so if you want to wait for mouse click, call the blocking Queue.get()
        self.mouseq = Queue()
        # run onMouseClick when mouse is clicked
        self.accept('mouse1', self.onMouseClick)
    def OpenInstructions(self):
        """Open the instructions

        Opens the instructions and add bold characters, etc
        Uses Panda3D text properties
        https://docs.panda3d.org/1.10/python/programming/gui/embedded-text-properties

        Args:
            None
        Returns:
            None
        """
        tpBold = TextProperties()
        tpBold.setFont(self.roboto_bold)
        tpMgr = TextPropertiesManager.getGlobalPtr()
        tpMgr.setProperties('bold', tpBold)

        ins_text = self.controller.instructions
        # direct gui cannot apply bold unless \1 and \2 are ascii
        # so decode the raw str from file to 'unicode_escape'
        ins_text = codecs.decode(ins_text, 'unicode_escape')

        # create an inital height for the canvas
        canvas_height = 5

        self.ins_frame = DirectScrolledFrame(pos=(0, -1, 0.65), frameColor=(0.5, 0.5, 0.5, 0.9),
                         canvasSize = (-1/2, 1/2, -.1, canvas_height), frameSize=(-0.7, 0.7, -1.5, 0.1))
        self.ins_label = DirectLabel(text=ins_text,
                                  parent = self.ins_frame.getCanvas(), frameColor=(0, 0, 0, 0),
                                  pos=(0, 0, canvas_height-0.1), text_font=self.roboto,
                                  text_wordwrap=12, text_scale=0.1, text_align=TextNode.ACenter)
        self.title = DirectLabel(text="\1bold\1INSTRUCTIONS",
                                  frameColor=(0.5, 0.5, 0.5, 1), frameSize=(-0.7, 0.7, -0.1, 0.1),
                                  pos=(0, -1, 0.85), text_font=self.roboto, borderWidth=(1, 1),
                                  text_wordwrap=12, text_scale=0.1, text_align=TextNode.ACenter)

        
        # Panda3D as far as I am aware of doesn't have a good system
        # for fixing text within a specific height
        # this might get a bit messy...

        # so get the height of the button
        w1, w2, h1, h2 = self.ins_label.getBounds()
        text_height = abs(h1)+abs(h2) # h1 may be negative

        # set the canvas height as text height
        self.ins_frame['canvasSize']=(-1/2, 1/2, -.1, text_height)
        # re center the text
        self.ins_label.setPos(0.2, 0, abs(h1)-0.05)

        self.exit_ins = DirectButton(text="CLOSE",
                         scale=.05,
                         command=self.CloseInstructions,
                         frameSize=(-0.7/.05, 0.7/.05, -1, 1),
                         pos=(0, 0, -0.9),
                         text_scale=(0.6, 0.6))

    def CloseInstructions(self):
        """Close the instructions

        Args:
            None
        Returns:
            None
        """
        self.ins_frame.destroy()
        self.exit_ins.destroy()
        

    def PopupWindowOpen(self):
        """Creates a popup file browser to select gamemode

        Creates a popup using tkinter to select a gamemode
        The selected gamemode is imported using importlib

        Args:
            None
        Returns:
            None
        """
        gamemode_path = None
        if useTkinter:
            file = tkinter.filedialog.askopenfile(parent=self.tk_root, initialdir=working_directory/'gamemodes',
                title='Please select a directory', filetypes=[("Python files", ".py")])
            if not file:
                # the user clicked close...
                return
            gamemode_path = file.name
            file.close()
        else:
            p = Popen(['python', 'popen.py'], stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            gamemode_path = stdout.decode('utf-8')
            if not gamemode_path:
                # the user clicked close...
                return

        # import file directly
        # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
        spec = importlib.util.spec_from_file_location("gamemode", gamemode_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["gamemode"] = module # attach to sys.modules
        spec.loader.exec_module(module)
        self.controller = module.main(self) # game controller

        self.clearScene()
        
        self.controller.load() # load board from external file

    def enableGravity(self):
        """Enable gravity on the scene

        Args:
            None
        Returns:
            None
        """
        gravityFN = ForceNode('world-forces')
        gravityFNP = self.render.attachNewNode(gravityFN)
        gravityForce = LinearVectorForce(0,0,-9.8) # gravity acceleration
        gravityFN.addForce(gravityForce)

        self.physicsMgr.addLinearForce(gravityForce)
    def window_closed(self):
        """On window closed event, destroy the window and exit program

        Args:
            None
        Returns:
            None
        """
        self.destroy()
        _exit(0) # fully restart (closes window on mac)
    def returnClickedPit(self):
        """Return the clicked pit

        Wait for click and check if it is a valid clicked object (a pit and on the players side)

        Args:
            None
        Returns:
            The clicked pit node path
        """
        clickedPit = None
        while not clickedPit:
            clickedObj = self.mouseq.get() # blocking, so it will wait until a value is placed in queue
            pickedObj = clickedObj.findNetTag(self.clickableTag) # check if clicked is a clickable
            if not pickedObj.isEmpty():
                # clicked on clickable
                side = int(pickedObj.getTag('side'))
                n = int(pickedObj.getTag('n'))
                if side == 0 and len(self.controller.stones[side][n]):
                    # is on plr 0 side and not empty
                    clickedPit = pickedObj
        return clickedPit

    def start_game(self):
        # hide the buttons
        self.st_button.hide()
        self.gm_button.hide()
        self.ins_button.hide()

        controller = app.controller # game controller
        choiceCeil = len(controller.clickables[1])-1 # the max number (ceiling) the rng can generate (because of the amount of clickables)
        
        
        while not controller.is_game_complete():
            turn = controller.turn
            self.turnText.show()
            if turn == 0:
                # change the text to "Your turn"
                self.turnText['text'] = "Your turn"
                clickedObj = app.returnClickedPit()
                self.turnText.hide()

                # the side of the selected pit
                clicked_side = int(clickedObj.getTag('side'))
                # the nth pit from the left that is selected
                clicked_n = int(clickedObj.getTag('n'))
            else:
                # change the text to "Opponents turn"
                self.turnText['text'] = "Opponents turn"
                hasStones = False
                while not hasStones:
                    n = randint(0, choiceCeil)
                    clicked_side = 1
                    clicked_n = n
                    if len(controller.stones[1][n]):
                        # keep generating a new pit until it has stones
                        hasStones = True
                
            controller.clicked_pit(clicked_side, clicked_n)
        if controller.winner == 0:
            print("You win!")
            self.turnText['text'] = "You win!"
        elif controller.winner == 1:
            print("You lose...")
            self.turnText['text'] = "You lose..."
        else:
            print("You tie")
            self.turnText['text'] = "Tie"
        self.turnText.show()

# main guard for threading
if __name__ == "__main__":
    app = Mancala()
    
    app.run()
