from time import sleep
from random import randint
from queue import Queue
import threading # don't check for these libraries as these are core libraries
import sys
from pathlib import Path
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

loadPrcFileData("", "load-file-type p3assimp") # obj files can be loaded

class Mancala(ShowBase):
    def __init__(self):
        ShowBase.__init__(self) # init module
        self.disableMouse() # disable camera control with the mouse
        base.setFrameRateMeter(True)
        self.set_background_color(1, 1, 1, 1)
        properties = WindowProperties()
        properties.setTitle('Mancala')
        self.win.requestProperties(properties) # set window properties

        self.win.setCloseRequestEvent('window_closed')
        self.accept('window_closed', self.window_closed)
        
        self.enableParticles() # start physics
        self.pusher = PhysicsCollisionHandler() # handle physics collisions by automatically pushing colliding objects
        self.pusher.setDynamicFrictionCoef(0.5) # add friction
        self.pusher.setStaticFrictionCoef(0)
        self.cTrav = CollisionTraverser('physics') # automatically handle physics operations

        self.clickableTag = "clickable" # clickable objects have this tag

        from gamemodes.congklak import Classic
        self.controller = Classic(self) # game controller
        self.controller.load() # load board from external file
        
        self.enableGravity()
        self.startMouse()

    def clearScene(self):
        # remove everything but the camera
        for i in self.render.getChildren():
            if i.name != 'camera':
                i.removeNode()
        self.render.clearLight()

    def onMouseClick(self):
        '''
            code used from panda3d documentation
            https://docs.panda3d.org/1.10/python/programming/collision-detection/clicking-on-3d-objects
        '''
        mpos = base.mouseWatcherNode.getMouse() # get mouse
        # sets collsion ray to start at camera and extend to inf in mouse direction
        self.pickerRay.setFromLens(base.camNode, mpos.getX(), mpos.getY())

        self.cTrav.traverse(self.render) # detect collisions
        # Assume for simplicity's sake that mouseHandler is a CollisionHandlerQueue.
        if self.mouseHandler.getNumEntries() > 0:
            # This is so we get the closest object
            self.mouseHandler.sortEntries()
            pickedObj = self.mouseHandler.getEntry(0).getIntoNodePath()
            
            self.mouseq.queue.clear() # empty queue
            self.mouseq.put(pickedObj) # put clicked obj in queue
        
    def startMouse(self):
        '''
            setup collision-based mouse clicker
            https://docs.panda3d.org/1.10/python/programming/collision-detection/clicking-on-3d-objects
        '''
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
    def createStartButton(self, func):
        # add start button
        b = DirectButton(text="START",
                         scale=.05, command=func, frameSize=(-2, 2, -1, 1))
        return b
    def createGamemodeButton(self):
        # add gamemode button
        b = DirectButton(text="GAMEMODE",
                         scale=.05,
                         command=self.PopupWindowOpen,
                         frameSize=(-2, 2, -1, 1),
                         pos=(0, 0, -0.3),
                         text_scale=(0.6, 0.6))
        return b
    def PopupWindowOpen(self):
        from subprocess import Popen, PIPE
        p = Popen(['python', 'popen.py'], stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        gamemode_path = stdout.decode('utf-8')
        
        # import file directly
        # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
        import importlib.util
        spec = importlib.util.spec_from_file_location("gamemode", gamemode_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["gamemode"] = module # attach to sys.modules
        spec.loader.exec_module(module)
        self.controller = module.Classic(self) # game controller

        self.clearScene()
        
        self.controller.load() # load board from external file

    def createTurnText(self):
        roboto = self.loader.loadFont("fonts/Roboto/Roboto-Regular.ttf")
        return DirectLabel(text='Your turn',
                           pos=(0, 0, 0.8), text_scale = (0.15, 0.15), frameColor=(0, 0, 0, 0),
                           textMayChange=True, parent=aspect2d, text_font=roboto)
    def enableGravity(self):
        gravityFN = ForceNode('world-forces')
        gravityFNP = self.render.attachNewNode(gravityFN)
        gravityForce = LinearVectorForce(0,0,-9.8) # gravity acceleration
        gravityFN.addForce(gravityForce)

        self.physicsMgr.addLinearForce(gravityForce)
    def window_closed(self):
        self.destroy()
        _exit(0) # fully restart (closes window on mac)
    def returnClickedPit(self):
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

def main(app):
    event = threading.Event()
    turnText = app.createTurnText()
    turnText.hide()
    
    button = app.createStartButton(event.set)
    gm_button = app.createGamemodeButton()
    event.wait() # wait for click
    event.clear() # reset 'internal flag' (read threading docs)
    button.hide()
    gm_button.hide()

    controller = app.controller # game controller
    choiceCeil = len(controller.clickables[1])-1 # the max number (ceiling) the rng can generate (because of the amount of clickables)
    
    
    while not controller.is_game_complete():
        turn = controller.get_turn()
        turnText.show()
        if turn == 0:
            turnText['text'] = "Your turn"
            clickedObj = app.returnClickedPit()
            turnText.hide()
            # the side of the selected pit
            clicked_side = int(clickedObj.getTag('side'))
            # the nth pit from the left that is selected
            clicked_n = int(clickedObj.getTag('n'))
        else:
            turnText['text'] = "Opponents turn"
            hasStones = False
            while not hasStones:
                n = randint(0, choiceCeil)
                clicked_side = 1
                clicked_n = n
                if len(controller.stones[1][n]):
                    # keep generating a new pit until it has stones
                    hasStones = True
            
        controller.clicked_pit(clicked_side, clicked_n)
    if controller.get_winner() == 0:
        print("You win!")
    elif controller.get_winner() == 1:
        print("You lose...")
    else:
        print("You tie")

# main guard for threading
if __name__ == "__main__":
    app = Mancala()

    # create a new daemon thread (daemon threads close with main thread)
    t = threading.Thread(target=main, args=(app,), daemon=True)
    t.start()
    
    app.run()
