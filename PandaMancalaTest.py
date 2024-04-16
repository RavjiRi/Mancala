from panda3d.core import loadPrcFileData, Material, DirectionalLight
loadPrcFileData("", "load-file-type p3assimp") # load objs
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import *
from direct.task import Task

from panda3d.core import *
from panda3d.physics import *
from time import sleep
from random import randint


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

class MyApp(ShowBase):

    def __init__(self):
        ShowBase.__init__(self) # init module
        self.disableMouse() # disable camera control with the mouse
        base.setFrameRateMeter(True)
        self.set_background_color(1, 1, 1, 1)
        
        ''' camera '''
        self.camera.setPos(-30, 0, 40) # z axis is the y axis that I am used to
        self.camera.lookAt(0,0,0)
        self.camLens.setFov(50) # default FOV is 40

        # start physics
        self.enableParticles()
        # physics handler
        self.pusher=PhysicsCollisionHandler() # handle physics collisions by automatically pushing colliding objects
        self.pusher.setDynamicFrictionCoef(0.5) # add friction
        self.pusher.setStaticFrictionCoef(0)
        traverser = CollisionTraverser('physics')
        self.cTrav = traverser # automatically handle physics operations
        #traverser.showCollisions(self.render) # DEBUG
        
        ''' directional light '''
        # directional light for the mancala board as it does not show up without it...
        light = DirectionalLight("alight")
        light.setColor((1, 1, 1, 1))
        light.setShadowCaster(True, 1024, 1024)
        lnp = self.render.attachNewNode(light) # light node path
        lnp.setPos(0, 0, 100)
        lnp.setHpr(0, -90, 0) # heading, yaw, pitch (the angle of light)
        self.render.setLight(lnp)
        
        ''' mancala model '''
        self.board = self.loader.loadModel("mancala/MancalaOrigin.obj") # noCache=True
        self.board.setP(self.board, 90) # rotate because I made the model wrong...
        self.board.setR(self.board, 10)
        self.board.reparentTo(self.render)
    
        ''' setup board '''
        y_pos_click = [9.8, 5.8, 1.9, -1.9, -5.8, -9.8]
        x_pos_click = [-2, 2]
        self.stones = {} # dictionary to store stones
        self.clickables = {} # dictionary to store clickables
        self.hoverables = {} # dictionary to store hoverables
        ''' loop through board parts '''
        # two sides because of two players
        for side in range(2):
            self.stones[side] = {}
            self.clickables[side] = {}
            self.hoverables[side] = {}
            # clickable obj nth from left
            for n in range(6):
                ''' create board collisions '''
                segment = self.loader.loadModel("mancala/CollisionAssets/Player{}/{}.obj".format(side, n), noCache=True)
                segment.setP(segment, 90)
                segment.reparentTo(self.render)
                segment.hide()
                for model in segment.find_all_matches("**/+GeomNode"):
                    model.setCollideMask(BitMasks[side][n])
                ''' create clickable points '''
                clickable = self.loader.loadModel('models/misc/sphere')
                self.clickables[side][n] = clickable
                self.hoverables[side][n] = clickable # all clickables can be hovered over
                x_pos = x_pos_click[side]
                y_pos = y_pos_click[n]
                clickable.setPos(x_pos, y_pos, 1)
                clickable.setScale(1.5, 1.5, 1.5)
                clickable.reparentTo(self.render)
                clickable.name='clickable ' + str(side) + "-" + str(n) # change name
                clickable.setTag('click', "True")
                clickable.setTag('hover', "True")
                clickable.setTag('side', str(side))
                clickable.setTag('n', str(n))
                clickable.hide() # make invisible
                ''' stones '''
                self.stones[side][n] = [] # store stones in array in dictionaries
                for count in range(4):
                    x, y, z = clickable.getPos()
                    stone = self.loader.loadModel('models/misc/sphere')
                    self.stones[side][n].append(stone)
                    stone.setScale(0.35, 0.35, 0.35)
                    # side 0 has blue, side 1 has green
                    if side == 0:
                        stone.setColor(0, 0, 1, 0)
                    elif side == 1:
                        stone.setColor(0, 1, 0, 0)
                    # start physics logic
                    node = NodePath("PhysicsNode")
                    node.reparentTo(self.render)
                    an = ActorNode("stone-physics")
                    Panp=node.attachNewNode(an)
                    self.physicsMgr.attachPhysicalNode(an)
                    stone.reparentTo(Panp)

                    # set stone position
                    Panp.setPos(x, y, 5+count*5)
                    
                    # create a collision sphere which will set how the stone looks to the collision system
                    cs = CollisionSphere(stone.getBounds().getCenter(), 0.35)
                    cn = CollisionNode('cnode')
                    '''
                    FROM objects are the 'moving' objs
                    INTO objects are the non moving 'walls'
                    '''
                    cn.setFromCollideMask(BitMasks[side][n])
                    cn.setIntoCollideMask(BitMasks[side][n])
                    cnodePath = Panp.attachNewNode(cn)
                    cnodePath.node().addSolid(cs)
                    self.pusher.addCollider(cnodePath, Panp)
                    traverser.addCollider(cnodePath, self.pusher)
                    #cnodePath.show() # DEBUG
            ''' board collisions for mancala '''
            segment = self.loader.loadModel("mancala/CollisionAssets/Player{}/Mancala.obj".format(side), noCache=True)
            segment.setP(segment, 90)
            segment.reparentTo(self.render)
            segment.hide()
            for model in segment.find_all_matches("**/+GeomNode"):
                model.setCollideMask(BitMasks[side][6])
            self.stones[side][6] = [] # create the array to store stones in mancala
            ''' create hoverable point '''
            hoverable = self.loader.loadModel('models/misc/sphere')
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
            hoverable.reparentTo(self.render)
            # reverse list so the first stones load on the left
            y_pos_click.reverse()

        # in case the stones fall through the model
        plane = CollisionPlane(Plane(Vec3(0, 0, 1), Point3(0, 0, -0.5)))
        cn = CollisionNode('plane')
        np = self.render.attachNewNode(cn)
        np.node().addSolid(plane)
        
        self.enableGravity()

        ''' setup collision-based mouse clicker '''
        self.myHandler = CollisionHandlerQueue()
        self.pickerNode = CollisionNode('mouseRay')
        # attach collision node to camera
        self.pickerNP = self.camera.attachNewNode(self.pickerNode)
        self.pickerNode.setFromCollideMask(GeomNode.getDefaultCollideMask())
        self.pickerRay = CollisionRay()
        # add the collision ray to the collision node
        self.pickerNode.addSolid(self.pickerRay)
        # detect collisions from pickerNP and handle with myHandler
        self.cTrav.addCollider(self.pickerNP, self.myHandler)
        
        self.accept('mouse1', self.clicked)
    def alignPosition(self, task, stone, go_to: Vec3):
        # gradually move stone to position
        an=stone.getParent().node()
        physical = an.getPhysical(0)
        phyObj = an.getPhysicsObject()
        thruster=stone.get_parent()

        max_speed = 10
        moveVec = (go_to-thruster.get_pos())
        moveDir = moveVec.normalized()
        moveDist = moveVec.length()
        ratio = (2/(1+pow(2.7, -moveDist))-1) # sigmoid function
        phyObj.setVelocity(moveDir*max_speed*ratio)
        return Task.cont
    '''
    NOT WORKING???

    def hovered(self, task, textNode, nodePath):
        if not base.mouseWatcherNode.hasMouse():
            # mouse is not on screen
            return Task.cont
        mpos = base.mouseWatcherNode.getMouse() # get mouse
        # sets collsion ray to start at camera and extend to inf in mouse direction
        self.pickerRay.setFromLens(base.camNode, mpos.getX(), mpos.getY())

        self.myTraverser.traverse(self.render) # detect collisions
        # Assume for simplicity's sake that myHandler is a CollisionHandlerQueue.
        if self.myHandler.getNumEntries() > 0:
            # This is so we get the closest object
            self.myHandler.sortEntries()
            pickedObj = self.myHandler.getEntry(0).getIntoNodePath()
            pickedObj = pickedObj.findNetTag('hover')
            if not pickedObj.isEmpty():
                # clicked on clickable
                nodePath.setPos(pickedObj.getPos())
                nodePath.show()
            else:
                nodePath.hide()
        return Task.cont
    def createQuickLook(self):
        hoverText = TextNode('txt')
        hoverText.set_text("1")
        hoverText.setAlign(TextNode.ACenter)
        hoverText.setTextColor(0, 0, 0, 1)
        hoverText.setCardColor(2, 2, 2, 1)
        hoverText.setCardAsMargin(0, 0, 0, 0)
        hoverText.setBoundsType(BoundingBox.BTBox)
        f=DirectFrame(frameSize=(-1, 1, -1, 1))
        f.attach_new_node(f)
        np=self.render.attach_new_node(hoverText)
        np.setTwoSided(True)
        np.setScale(0.5)
        np.setPos(0, 0, 0)
        np.setBillboardPointEye(-10, fixed_depth=True)
        np.setBin("fixed", 0)
        np.setDepthWrite(False)
        np.setDepthTest(False)
        task = self.taskMgr.add(self.hovered, "hoverTask", extraArgs=["hoverTask", hoverText, np])
        '''
    def isGameComplete(self):
        # stones left for player 0 and 1
        stones_plr0 = sum(len(self.stones[0][n]) for n in range(6))
        stones_plr1 = sum(len(self.stones[1][n]) for n in range(6))
        return (stones_plr0 == 0) or (stones_plr1 == 0)
    def sumStones(self, plr):
        # sum stones for player 1 or 0
        return sum(len(self.stones[plr][n]) for n in range(6))
    def createStartButton(self, func):
        # Add button
        b = DirectButton(text="START",
                         scale=.05, command=func, frameSize=(-2, 2, -1, 1))
        return b
    def createTurnText(self):
        roboto = self.loader.loadFont("mancala/Roboto/Roboto-Regular.ttf")
        return DirectLabel(text='Your turn',
                           pos=(0, 0, 0.8), text_scale = (0.15, 0.15), frameColor=(0, 0, 0, 0),
                           textMayChange=True, parent=aspect2d, text_font=roboto)
    def setStationary(self, stone):
        an=stone.getParent().node()
        phyObj = an.getPhysicsObject()

        phyObj.setVelocity(Vec3(0, 0, 0))
    def enableGravity(self):
        gravityFN = ForceNode('world-forces')
        gravityFNP = self.render.attachNewNode(gravityFN)
        gravityForce = LinearVectorForce(0,0,-9.8) #gravity acceleration
        gravityFN.addForce(gravityForce)

        self.physicsMgr.addLinearForce(gravityForce)
    def clicked(self):
        mpos = base.mouseWatcherNode.getMouse() # get mouse
        # sets collsion ray to start at camera and extend to inf in mouse direction
        self.pickerRay.setFromLens(base.camNode, mpos.getX(), mpos.getY())

        self.cTrav.traverse(self.render) # detect collisions
        # Assume for simplicity's sake that myHandler is a CollisionHandlerQueue.
        if self.myHandler.getNumEntries() > 0:
            # This is so we get the closest object
            self.myHandler.sortEntries()
            pickedObj = self.myHandler.getEntry(0).getIntoNodePath()
            print("clicked on:", pickedObj)
            print("net", pickedObj.findNetTag('click'))
    def returnClickedPit(self, func, q):
        mpos = base.mouseWatcherNode.getMouse() # get mouse
        # sets collsion ray to start at camera and extend to inf in mouse direction
        self.pickerRay.setFromLens(base.camNode, mpos.getX(), mpos.getY())

        self.cTrav.traverse(self.render) # detect collisions
        # Assume for simplicity's sake that myHandler is a CollisionHandlerQueue.
        if self.myHandler.getNumEntries() > 0:
            # This is so we get the closest object
            self.myHandler.sortEntries()
            pickedObj = self.myHandler.getEntry(0).getIntoNodePath()
            pickedObj = pickedObj.findNetTag('click')
            if not pickedObj.isEmpty():
                # clicked on clickable
                side = int(pickedObj.getTag('side'))
                n = int(pickedObj.getTag('n'))
                if side == 0 and self.stones[side][n]:
                    # can only pick on your own side (plr 0 side)
                    q.put(pickedObj)
                    func()
            
class MancalaUtils():
    '''
    functions which are not directly related to the main app class
    which help make code smaller and more readable
    '''
    def next_pit(self, side, n):
        n+=1
        if n>=7:
            n=0
            if side == 0:
                side = 1
            else:
                side = 0
        return side, n

import threading, queue
def main(app):
    util = MancalaUtils()
    event = threading.Event()
    q = queue.Queue()
    turnText = app.createTurnText()
    turnText.hide()

    turn = 0 # player 0 goes first
    
    button = app.createStartButton(event.set)
    event.wait() # wait for click
    event.clear() # reset 'internal flag' (read threading docs)
    button.hide()
    while not app.isGameComplete():
        turnText.show()
        if turn == 0:
            turnText['text'] = "Your turn"
            app.accept('mouse1', app.returnClickedPit, extraArgs=[event.set, q])
            event.wait() # wait for click on clickable object
            event.clear()
            app.ignore('mouse1') # remove event listener
            clickedObj = q.get()
            turnText.hide()
        else:
            turnText['text'] = "Opponents turn"
            hasStones = False
            while not hasStones:
                n = randint(0, 5)
                clickedObj = app.clickables[1][n]
                if len(app.stones[1][n]):
                    # keep generating a new pit until it has stones
                    hasStones = True
            
        # the side of the selected pit
        clicked_side = int(clickedObj.getTag('side'))
        # the nth pit from the left that is selected
        clicked_n = int(clickedObj.getTag('n'))
        clicked_stones = app.stones[clicked_side][clicked_n]
        
        side = clicked_side
        n = clicked_n
        # while clicked_stones is NOT empty
        while clicked_stones:
            currentPit = app.hoverables[side][n]
            go_to = currentPit.getPos()+Vec3(0, 0, 5)
            for stone in clicked_stones:
                # hover above the current pit
                task = app.taskMgr.add(app.alignPosition, "moveTask", extraArgs=["moveTask", stone, go_to])
            sleep(1)
            app.taskMgr.removeTasksMatching("moveTask")

            side, n = util.next_pit(side, n) # get the next pit
            go_to = app.hoverables[side][n].getPos()+Vec3(0, 0, 5)
            for stone in clicked_stones:
                # move above the next pit
                task = app.taskMgr.add(app.alignPosition, "moveTask", extraArgs=["moveTask", stone, go_to])
            sleep(1)
            app.taskMgr.removeTasksMatching("moveTask")
            for stone in clicked_stones:
                app.setStationary(stone)
            
            droppedStone = clicked_stones.pop()
            cn = droppedStone.getParent().find('cnode').node()
            cn.setFromCollideMask(BitMasks[side][n])
            cn.setIntoCollideMask(BitMasks[side][n])
            app.stones[side][n].append(droppedStone)
            app.setStationary(droppedStone)
        if turn == 0:
            turn = 1
        else:
            turn = 0
    if app.sumStones(0) == 0:
        print("You win!")
    else:
        print("You lose...")

if __name__ == "__main__":
    app = MyApp()
    
    t = threading.Thread(target=main, args=(app,))
    t.start()
    
    app.run()
