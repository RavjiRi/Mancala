from panda3d.core import *
from panda3d.physics import *

# This is a sort-of template that explains how to make a game mode
# it might be easier to read the classic gamemode though...

class Template():
    ''' functions that are required and called by the main code '''
    def __init__(self, app):
        '''
            Setup the class variables, these variables are required as they are
            used by the main looping function get if a pit is clickable or has
            stones
        '''
        self.app = app # store app for use outside init function
        self.stones = {} # dictionary to store stones
        self.clickables = {} # dictionary to store clickables
        self.hoverables = {} # dictionary to store hoverables
        self.stonesPerPit = 4
    def load(self):
        '''
            required function that is called to load and setup the board
        '''
        app = self.app # save space by dropping self

        # this is so the main code can tell what objects can be clicked on
        app.clickableTag = "clickable"
        
        # recommended to setup the camera here using app.camera

        # debug but NOT recommended because of how much the program slows down
        # traverser.showCollisions(app.render)
        
        # recommended to set lights here if required
        
        # setup the visible mancala board here and reparent to app.render
    
        # loop through the board parts
        # two sides because of two players
        for side in range(2):
            self.stones[side] = {}
            self.clickables[side] = {}
            self.hoverables[side] = {}
            # clickable obj nth from left
            for n in range(6):
                # create board collisions for each pit
                # or use the whole board
                
                # create clickable points
                # the clickable points should have a tag of name app.clickableTag
                # this is so the main code can tell what objects can be clicked
                # they should also have a side and nth from left tag so the main code
                # can tell where it is
                '''
                clickable.setTag(app.clickableTag, "True") # this is how we will tell if we clicked the clickable
                clickable.setTag('hover', "True") # it is hoverable
                clickable.setTag('side', str(side)) # it is on the side of player 0/1
                clickable.setTag('n', str(n)) # nth from the left
                '''

                # stones
                self.stones[side][n] = [] # store stones in array in dictionaries
                for count in range(self.stonesPerPit):
                    # load stone and set properties here then add to array
                    '''
                    self.stones[side][n].append(stone)
                    '''
                    
                    # start physics logic (very important for collisions)
                    '''
                    node = NodePath("PhysicsNode")
                    node.reparentTo(app.render)
                    an = ActorNode("stone-physics")
                    Panp=node.attachNewNode(an)
                    app.physicsMgr.attachPhysicalNode(an)
                    stone.reparentTo(Panp)
                    
                    # create a collision sphere which will set how the stone looks to the collision system
                    cs = CollisionSphere(stone.getBounds().getCenter(), 0.35)
                    cn = CollisionNode('cnode')

                    cnodePath = Panp.attachNewNode(cn)
                    cnodePath.node().addSolid(cs) # attach collision sphere
                    app.pusher.addCollider(cnodePath, Panp) # add to physics pusher which keeps it out of other objects
                    app.cTrav.addCollider(cnodePath, app.pusher) # add to traverser which handles physics
                    # show collision objects for debugging
                    # cnodePath.show() 
                    '''
            # board collisions for the mancala
            # (where the stones go, not the board itself)

            # create a hoverable point here and add tags

        # backup collsion 'floor' in case the stones fall through the model
        '''
        plane = CollisionPlane(Plane(Vec3(0, 0, 1), Point3(0, 0, -0.5)))
        cn = CollisionNode('plane')
        np = app.render.attachNewNode(cn)
        np.node().addSolid(plane)
        '''

        self.turn = 0 # player 0 goes first
        self.gameComplete = False
    def clickedPit(self, clicked_side, clicked_n):
        '''
            a required function that is called when a pit is clicked for the next turn
            this should handle all the visual effects such as moving the stones
            this should also check for when the game finishes at the end
            
            clicked_side: the side that was clicked
            clicked_n: the nth from left clicked
        '''
    def getTurn(self):
        '''
            a required function called by the main code
        '''
        return self.turn
    def isGameComplete(self):
        '''
            a required function called by the main code
        '''
        return self.gameComplete
    def getWinner(self):
        '''
            a required function called by the main code
        '''
        return self.winner
    ''' code used by the this class only can go after this '''
