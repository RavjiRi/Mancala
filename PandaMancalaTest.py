from math import pi, sin, cos
import copy
from panda3d.core import loadPrcFileData, Material, DirectionalLight
loadPrcFileData("", "load-file-type p3assimp") # load objs
from direct.showbase.ShowBase import ShowBase

from direct.task import Task

from direct.actor.Actor import Actor

from direct.interval.IntervalGlobal import Sequence

from panda3d.core import PointLight, AmbientLight, NodePath, Point3
from panda3d.core import *
from panda3d.physics import *


BitMasks = {
        '0': {
            '0': BitMask32(0x1), # 0000 0000 0000 0000 0000 0000 0000 0001
            '1': BitMask32(0x2), # 0000 ... 0010
            '2': BitMask32(0x4), # 0000 ... 0100
            '3': BitMask32(0x8),
            '4': BitMask32(0x10),
            '5': BitMask32(0x20)
            },
        '1': {
            '0': BitMask32(0x40), # 0000 0000 0000 0000 0000 0000 0100 0000
            '1': BitMask32(0x80), # 0000 ... 1000 0000
            '2': BitMask32(0x100), # 0000 ... 0001 0000 0000
            '3': BitMask32(0x200),
            '4': BitMask32(0x400),
            '5': BitMask32(0x800)
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
        self.clickable_points = {}
        ''' loop through board parts '''
        for side in range(2):
            self.clickable_points[side] = {}
            # clickable obj nth from left
            for n in range(6):
                ''' create board collisions '''
                self.segment = self.loader.loadModel("mancala/CollisionAssets/{}-{}.obj".format(side, n+1))
                self.segment.setP(self.segment, 90)
                self.segment.reparentTo(self.render)
                self.segment.hide()
                for model in self.segment.find_all_matches("**/+GeomNode"):
                    model.setCollideMask(BitMasks[str(side)][str(n)])
                ''' create clickable points '''
                clickable = self.loader.loadModel('models/misc/sphere')
                y_pos = y_pos_click[n]
                # x value: turn 0 -> -1, 1 -> 1, then *2
                clickable.setPos(2*(2*side-1), y_pos, 1)
                clickable.setScale(1.5, 1.5, 1.5)
                clickable.reparentTo(self.render)
                clickable.name='clickable ' + str(side) + "-" + str(n) # change name
                clickable.setTag('click', str(side)+"-"+str(n))
                clickable.hide() # make invisible
                self.clickable_points[side][n] = clickable
                ''' stones '''
                for count in range(4):
                    x, y, z = clickable.getPos()
                    self.stone = self.loader.loadModel('models/misc/sphere')
                    self.stone.subdivideCollisions(4)
                    self.stone.setPos(x, y, 5+count*5)
                    self.stone.setScale(0.35, 0.35, 0.35)
                    self.stone.setColor(0, 1, 0, 0)
                    if side == 0:
                        self.stone.setColor(0, 0, 1, 0)
                    self.stone.reparentTo(self.render)
                    # start physics logic
                    node = NodePath("PhysicsNode")
                    node.reparentTo(self.render)
                    an = ActorNode("stone-physics")
                    Panp=node.attachNewNode(an)
                    self.physicsMgr.attachPhysicalNode(an)
                    self.stone.reparentTo(Panp)
                    # create a collision sphere which will set how the stone looks to the collision system
                    cs = CollisionSphere(self.stone.getBounds().getCenter(), 0.35)
                    cn = CollisionNode('cnode')
                    cn.setFromCollideMask(BitMasks[str(side)][str(n)])
                    cn.setIntoCollideMask(BitMasks[str(side)][str(n)])
                    cnodePath = Panp.attachNewNode(cn)
                    ###cnodePath.setCollideMask(BitMask32(0x10+count))
                    #cnodePath = Panp.attachNewNode(CollisionNode('cnode'))
                    cnodePath.node().addSolid(cs)
                    self.pusher.addCollider(cnodePath, Panp)
                    traverser.addCollider(cnodePath, self.pusher)
                    # cnodePath.show() # DEBUG
            y_pos_click = list(reversed(y_pos_click))
                

        ''' create clickable points '''
        '''
        # the y positions of the invisible clickable objects (looks like x pos changed from viewpoint)
        y_pos_click = [-9.8, -5.8, -1.9, 1.9, 5.8, 9.8]
        y_pos_click = list(reversed(y_pos_click))
        self.clickable_points = {}
        for side in range(2):
            self.clickable_points[side] = {}
            for n, y_pos in enumerate(y_pos_click):
                # index, value for loop
                # clickable obj nth from left
                clickable = self.loader.loadModel('models/misc/sphere')
                # x value: turn 0 -> -1, 1 -> 1, then *2
                clickable.setPos(2*(2*side-1), y_pos, 1)
                clickable.setScale(1.5, 1.5, 1.5)
                clickable.reparentTo(self.render)
                clickable.name='clickable ' + str(side) + "-" + str(n) # change name
                clickable.setTag('click', str(side)+"-"+str(n))
                clickable.hide() # make invisible
                self.clickable_points[side][n] = clickable
            y_pos_click = list(reversed(y_pos_click))
        '''
        
        '''
        FROM objects are the 'moving' objs
        INTO objects are the non moving 'walls'
        '''
        ''' create stones '''
        '''
        for k, side in self.clickable_points.items():
            for k2, point in side.items():
                for count in range(4):
                    x, y, z = point.getPos()
                    self.stone = self.loader.loadModel('models/misc/sphere')
                    self.stone.subdivideCollisions(4)
                    self.stone.setPos(x, y, 5+count*5)
                    self.stone.setScale(0.5, 0.5, 0.5)
                    self.stone.setColor(0, 1, 0, 0)
                    if k == 0:
                        self.stone.setColor(0, 0, 1, 0)
                    self.stone.reparentTo(self.render)
                    # start physics logic
                    node = NodePath("PhysicsNode")
                    node.reparentTo(self.render)
                    an = ActorNode("stone-physics")
                    Panp=node.attachNewNode(an)
                    self.physicsMgr.attachPhysicalNode(an)
                    self.stone.reparentTo(Panp)
                    # create a collision sphere which will set how the stone looks to the collision system
                    cs = CollisionSphere(self.stone.getBounds().getCenter(), 0.5)
                    cn = CollisionNode('cnode')
                    cn.setFromCollideMask(BitMasks[str(k)][str(k2)])
                    cn.setIntoCollideMask(BitMasks[str(k)][str(k2)])
                    cnodePath = Panp.attachNewNode(cn)
                    ###cnodePath.setCollideMask(BitMask32(0x10+count))
                    #cnodePath = Panp.attachNewNode(CollisionNode('cnode'))
                    cnodePath.node().addSolid(cs)
                    self.pusher.addCollider(cnodePath, Panp)
                    traverser.addCollider(cnodePath, self.pusher)
                    # cnodePath.show() # DEBUG
        '''
        '''
        self.bean = self.loader.loadModel('models/misc/sphere')
        self.bean.setPos(2, 2, 5)
        self.bean.setScale(0.5, 0.5, 0.5)
        self.bean.setColor(0, 1, 0, 0)


        node = NodePath("PhysicsNode")
        node.reparentTo(self.render)
        an = ActorNode("bean-physics")
        Panp=node.attachNewNode(an)
        self.physicsMgr.attachPhysicalNode(an)
        self.bean.reparentTo(Panp)
        '''
        # physics handler
        #self.pusher=PhysicsCollisionHandler()#CollisionHandlerPusher()
        #self.pusher.setDynamicFrictionCoef(1) # add friction
        # the new copy

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


app = MyApp()

app.run()
