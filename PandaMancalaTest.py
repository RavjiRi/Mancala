from math import pi, sin, cos
import copy
from panda3d.core import loadPrcFileData, Material, DirectionalLight
loadPrcFileData("", "load-file-type p3assimp") # load objs
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import *
from direct.task import Task

from direct.actor.Actor import Actor

from direct.interval.IntervalGlobal import Sequence

from panda3d.core import PointLight, AmbientLight, NodePath, Point3
from panda3d.core import *
from panda3d.physics import *
from time import sleep


BitMasks = {
        0: {
            0: BitMask32(0x1), # 0000 0000 0000 0000 0000 0000 0000 0001
            1: BitMask32(0x2), # 0000 ... 0010
            2: BitMask32(0x4), # 0000 ... 0100
            3: BitMask32(0x8),
            4: BitMask32(0x10),
            5: BitMask32(0x20),
            6: BitMask32(0x1000) # bit mask for plr 0 goal
            },
        1: {
            0: BitMask32(0x40), # 0000 0000 0000 0000 0000 0000 0100 0000
            1: BitMask32(0x80), # 0000 ... 1000 0000
            2: BitMask32(0x100), # 0000 ... 0001 0000 0000
            3: BitMask32(0x200),
            4: BitMask32(0x400),
            5: BitMask32(0x800),
            6: BitMask32(0x2000) # bit mask for plr 1 goal
            }
    }

class MyApp(ShowBase):

    def __init__(self):
        ShowBase.__init__(self) # init module
        self.disableMouse() # Disable the camera trackball controls.
        base.setFrameRateMeter(True)
        self.set_background_color(1, 1, 1, 1)
        
        ''' camera '''
        self.camera.setPos(30, 0, 40) # z axis is the y axis that I am used to
        self.camera.lookAt(0,0,0)
        self.camLens.setFov(50) # default FOV is 40

        # start physics
        self.enableParticles()
        # physics handler
        self.pusher=PhysicsCollisionHandler()#CollisionHandlerPusher()
        self.pusher.setDynamicFrictionCoef(0.5) # add friction
        self.pusher.setStaticFrictionCoef(0)
        traverser = CollisionTraverser('physics')
        self.cTrav = traverser # automatically handle physics operations
        #traverser.showCollisions(self.render) # DEBUG
        
        # self.workspace = NodePath("workspace")
        ''' directional light '''
        # directional light for the mancala board as it does not show up without it...
        light = DirectionalLight("alight")
        light.setColor((1, 1, 1, 1))
        light.setShadowCaster(True, 1024, 1024)
        lnp = self.render.attachNewNode(light) # light node path
        lnp.setPos(0, 0, 100)
        lnp.setHpr(0, -90, 0) # heading, yaw, pitch (the angle of light)
        #self.workspace.setLight(alnp)
        self.render.setLight(lnp)
        
        ''' light model '''        
        self.light_model = self.loader.loadModel('models/misc/sphere')
        self.light_model.setColor(0, 0, 1, 1)
        self.light_model.setScale(0.2, 0.2, 0.2)
        self.light_model.setPos(-4, 4, 10)
        self.light_model.reparentTo(self.render)
        
        ''' mancala model '''
        self.board = self.loader.loadModel("mancala/MancalaOrigin.obj")
        self.board.setP(self.board, 90) # rotate because I made the model wrong...
        self.board.setR(self.board, 10)
        self.board.reparentTo(self.render)
        #self.board.hide()
        #self.board.reparentTo(self.workspace)
        #self.workspace.reparentTo(self.render)
    
        ''' untitled model '''
        #self.collision_board = self.loader.loadModel("mancala/untitled.obj", noCache=True)
        #self.collision_board.setP(self.collision_board, 90) # rotate because I made the model wrong...
        #self.collision_board.reparentTo(self.render)
        y_pos_click = [9.8, 5.8, 1.9, -1.9, -5.8, -9.8]
        x_pos_click = [-2, 2]
        self.stones = {}
        self.clickables = {}
        ''' loop through board parts '''
        # two sides because of two players
        for side in range(2):
            self.stones[side] = {}
            self.clickables[side] = {}
            # clickable obj nth from left
            for n in range(6):
                ''' create board collisions '''
                segment = self.loader.loadModel("mancala/CollisionAssets/{}-{}.obj".format(side, n+1))
                segment.setP(segment, 90)
                segment.reparentTo(self.render)
                segment.hide()
                for model in segment.find_all_matches("**/+GeomNode"):
                    model.setCollideMask(BitMasks[side][n])
                ''' create clickable points '''
                clickable = self.loader.loadModel('models/misc/sphere')
                self.clickables[side][n] = clickable
                y_pos = y_pos_click[n]
                x_pos = x_pos_click[side]
                clickable.setPos(x_pos, y_pos, 1)
                clickable.setScale(1.5, 1.5, 1.5)
                clickable.reparentTo(self.render)
                clickable.name='clickable ' + str(side) + "-" + str(n) # change name
                clickable.setTag('click', str(side)+"-"+str(n))
                clickable.hide() # make invisible
                ''' stones '''
                self.stones[side][n] = [] # store stones in dictionary
                for count in range(4):
                    x, y, z = clickable.getPos()
                    stone = self.loader.loadModel('models/misc/sphere')
                    self.stones[side][n].append(stone)
                    # self.stone.subdivideCollisions(4)
                    #stone.setPos(x, y, 5+count*5)
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
            ''' board collisions for goal '''
            segment = self.loader.loadModel("mancala/CollisionAssets/{}-{}.obj".format(side, 7))
            segment.setP(segment, 90)
            segment.reparentTo(self.render)
            segment.hide()
            for model in segment.find_all_matches("**/+GeomNode"):
                model.setCollideMask(BitMasks[side][6])
            self.stones[side][6] = [] # create the array to store stones in goal
            ''' create clickable points '''
            clickable = self.loader.loadModel('models/misc/sphere')
            self.clickables[side][6] = clickable
            if side == 0:
                y_pos = -13.9
            else:
                y_pos = 13.9
            x_pos = 0
            clickable.setPos(x_pos, y_pos, 1)
            clickable.setScale(1.5, 1.5, 1.5)
            clickable.hide()
            clickable.reparentTo(self.render)
            # reverse list so the first stones load on the left
            y_pos_click = list(reversed(y_pos_click))

        ###self.taskMgr.add(self.applyForce, "forceTask")

        '''
        for model in self.collision_board.find_all_matches("**/+GeomNode"):
            model.setCollideMask(BitMask32(0x11))
        '''
            
            #node.node().setIntoCollideMask(BitMask32(2))
        #####board_copy = self.addCollider_from_collision_mesh_from_model(self.board, self.pusher)
        
        ''''''
        #traverser = CollisionTraverser('physics')
        #self.cTrav = traverser # automatically handle physics operations
        #traverser.showCollisions(self.render) # DEBUG
        ''''''
        
        '''
        WORKING
        anp = self.board.attachNewNode(ActorNode('actor'))
        cs = CollisionBox(self.board.getBounds().getCenter(), 10, 1, 10)
        cnodePath = anp.attachNewNode(CollisionNode('cnode'))
        cnodePath.node().addSolid(cs)
        self.pusher.addCollider(cnodePath, anp)
        #traverser.addCollider(cnodePath, self.pusher)
        cnodePath.show()
        '''
        #anp = self.bean.attachNewNode(an)
        '''
        anp = Panp
        cs = CollisionSphere(self.bean.getBounds().getCenter(), 0.5)
        cnodePath = anp.attachNewNode(CollisionNode('cnode'))
        cnodePath.node().addSolid(cs)
        self.pusher.addCollider(cnodePath, anp)
        traverser.addCollider(cnodePath, self.pusher)
        cnodePath.show()
        '''
        self.enableGravity()

        ''''''
        
        # the part that detects collisions
        self.myTraverser = self.cTrav
        ######self.myTraverser.showCollisions(self.render) # DEBUG MODE
        self.myHandler = CollisionHandlerQueue()
        self.pickerNode = CollisionNode('mouseRay')
        # attach collision node to camera
        self.pickerNP = self.camera.attachNewNode(self.pickerNode)
        self.pickerNode.setFromCollideMask(GeomNode.getDefaultCollideMask())
        self.pickerRay = CollisionRay()
        # add the collision ray to the collision node
        self.pickerNode.addSolid(self.pickerRay)
        # detect collisions from pickerNP and handle with myHandler
        self.myTraverser.addCollider(self.pickerNP, self.myHandler)
        
        self.accept('mouse1', self.clicked)
        ''''''


        # Add the spinCameraTask procedure to the task manager.
        '''self.taskMgr.add(self.spinCameraTask, "SpinCameraTask")'''


        # Load and transform the panda actor.

        self.pandaActor = Actor("models/panda-model",

                                {"walk": "models/panda-walk4"})

        self.pandaActor.setScale(0.005, 0.005, 0.005)

        self.pandaActor.reparentTo(self.render)

        # Loop its animation.

        self.pandaActor.loop("walk")


        # Create the four lerp intervals needed for the panda to

        # walk back and forth.

        posInterval1 = self.pandaActor.posInterval(13,

                                                   Point3(0, -10, 0),

                                                   startPos=Point3(0, 10, 0))

        posInterval2 = self.pandaActor.posInterval(13,

                                                   Point3(0, 10, 0),

                                                   startPos=Point3(0, -10, 0))

        hprInterval1 = self.pandaActor.hprInterval(3,

                                                   Point3(180, 0, 0),

                                                   startHpr=Point3(0, 0, 0))

        hprInterval2 = self.pandaActor.hprInterval(3,

                                                   Point3(0, 0, 0),

                                                   startHpr=Point3(180, 0, 0))


        # Create and play the sequence that coordinates the intervals.

        self.pandaPace = Sequence(posInterval1, hprInterval1,

                                  posInterval2, hprInterval2,

                                  name="pandaPace")

        self.pandaPace.loop()
        
    # Define a procedure to move the camera.

    def spinCameraTask(self, task):

        angleDegrees = task.time*3 * 6.0

        angleRadians = angleDegrees * (pi / 180.0)

        self.camera.setPos(20 * sin(angleRadians), -20 * cos(angleRadians), 3)

        self.camera.setHpr(angleDegrees, 0, 0)

        return Task.cont
    def addCollider_from_collision_mesh_from_model(self, loaded_model, collision_handler):
        #https://discourse.panda3d.org/t/collision-mesh-from-loaded-model-for-built-in-collision-system/27102'
        # shallow-copy the model
        model_copy = copy.copy(loaded_model)
        # set the rotation to 0, 0, 0 (as it will align with loaded model when reparented)
        model_copy.setHpr(0, 0, 0)
        model_copy.detach_node()
        model_copy.flatten_light()
        collision_root = NodePath("collision_root")
        collision_root.reparent_to(loaded_model)
        for model in model_copy.find_all_matches("**/+GeomNode"):
            model_node = model.node()
            collision_node = CollisionNode(model_node.name)
            collision_mesh = collision_root.attach_new_node(collision_node)
            # collision nodes are hidden by default
            #collision_mesh.show()

            for geom in model_node.modify_geoms():

                geom.decompose_in_place()
                vertex_data = geom.modify_vertex_data()
                vertex_data.format = GeomVertexFormat.get_v3()
                view = memoryview(vertex_data.arrays[0]).cast("B").cast("f")
                index_list = geom.primitives[0].get_vertex_list()
                index_count = len(index_list)

                for indices in (index_list[i:i+3] for i in range(0, index_count, 3)):
                    points = [Point3(*view[index*3:index*3+3]) for index in indices]
                    coll_poly = CollisionPolygon(*points)
                    collision_node.add_solid(coll_poly)
            #anp = model_copy.attachNewNode(ActorNode('actor'))
            #collision_handler.addCollider(collision_mesh, anp)
        return model_copy
    def applyForce(self, task, stone, go_to: Vec3):
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
    def createStartButton(self, func):
        # Add button
        b = DirectButton(text="START",
                         scale=.05, command=func, frameSize=(-2, 2, -1, 1))
        return b
    def setStationary(self, stone):
        an=stone.getParent().node()
        phyObj = an.getPhysicsObject()

        phyObj.setVelocity(Vec3(0, 0, 0))
    def enableGravity(self):
        gravityFN = ForceNode('world-forces')
        gravityFNP = self.render.attachNewNode(gravityFN)
        gravityForce = LinearVectorForce(0,0,-1) #gravity acceleration
        gravityFN.addForce(gravityForce)

        self.physicsMgr.addLinearForce(gravityForce)
    def clicked(self):
        mpos = base.mouseWatcherNode.getMouse() # get mouse
        # sets collsion ray to start at camera and extend to inf in mouse direction
        self.pickerRay.setFromLens(base.camNode, mpos.getX(), mpos.getY())

        self.myTraverser.traverse(self.render) # detect collisions
        # Assume for simplicity's sake that myHandler is a CollisionHandlerQueue.
        if self.myHandler.getNumEntries() > 0:
            # This is so we get the closest object
            self.myHandler.sortEntries()
            pickedObj = self.myHandler.getEntry(0).getIntoNodePath()
            print("clicked on:", pickedObj)
            print("net", pickedObj.findNetTag('click'))
    def clickedOnClickable(self, func, q):
        mpos = base.mouseWatcherNode.getMouse() # get mouse
        # sets collsion ray to start at camera and extend to inf in mouse direction
        self.pickerRay.setFromLens(base.camNode, mpos.getX(), mpos.getY())

        self.myTraverser.traverse(self.render) # detect collisions
        # Assume for simplicity's sake that myHandler is a CollisionHandlerQueue.
        if self.myHandler.getNumEntries() > 0:
            # This is so we get the closest object
            self.myHandler.sortEntries()
            pickedObj = self.myHandler.getEntry(0).getIntoNodePath()
            pickedObj = pickedObj.findNetTag('click')
            if not pickedObj.isEmpty():
                # clicked on clickable
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
    def get_side_from_name(self, clickable):
        return int(clickable.name[-3:][0])
    def get_n_from_name(self, clickable):
        return int(clickable.name[-3:][-1])

#from time import sleep
import threading, queue
def main(app):
    util = MancalaUtils()
    event = threading.Event()
    q = queue.Queue()
    button = app.createStartButton(event.set)
    event.wait() # wait for click
    event.clear() # reset 'internal flag' (read threading docs)
    button.hide()
    while True:
        app.accept('mouse1', app.clickedOnClickable, extraArgs=[event.set, q])
        event.wait() # wait for click on clickable object
        event.clear()
        app.ignore('mouse1') # remove event listener
        clickedObj = q.get()

        # the side which the pit is selected
        clicked_pit_side = util.get_side_from_name(clickedObj)
        # the nth pit from the left that is selected
        clicked_pit_n = util.get_n_from_name(clickedObj)
        side = clicked_pit_side
        n = clicked_pit_n
        while app.stones[clicked_pit_side][clicked_pit_n] != []:
            currentPit = app.clickables[side][n]
            go_to = currentPit.getPos()+Vec3(0, 0, 5)
            for stone in app.stones[clicked_pit_side][clicked_pit_n]:
                # move above the current pit
                task = app.taskMgr.add(app.applyForce, "forceTask", extraArgs=["forceTask", stone, go_to])
            sleep(1)
            app.taskMgr.removeTasksMatching("forceTask")
            for stone in app.stones[clicked_pit_side][clicked_pit_n]:
                app.setStationary(stone)

            to_side, to_n = util.next_pit(side, n)
            go_to = app.clickables[to_side][to_n].getPos()+Vec3(0, 0, 5)
            for stone in app.stones[clicked_pit_side][clicked_pit_n]:
                # move above the next pit
                task = app.taskMgr.add(app.applyForce, "forceTask", extraArgs=["forceTask", stone, go_to])
            sleep(1)
            app.taskMgr.removeTasksMatching("forceTask")
            for stone in app.stones[clicked_pit_side][clicked_pit_n]:
                app.setStationary(stone)
            droppedStone = app.stones[clicked_pit_side][clicked_pit_n].pop()
            cn = droppedStone.getParent().find('cnode').node()
            cn.setFromCollideMask(BitMasks[to_side][to_n])
            cn.setIntoCollideMask(BitMasks[to_side][to_n])
            app.stones[to_side][to_n].append(droppedStone)
            side, n = to_side, to_n

if __name__ == "__main__":
    app = MyApp()
    
    x = threading.Thread(target=main, args=(app,))
    x.start()
    
    app.run()
