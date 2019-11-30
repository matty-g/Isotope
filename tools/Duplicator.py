import nuke

class Duplicator():
    """
    A class with methods to manage straight duplication of existing nodes
    and to concatenate world-space matrices into local-space matrices
    """

    def duplicateNode(self):
        """ duplicates an exact copy of the selected node, including all animations """

        try:
            self.__duplicate(nuke.selectedNode())
        except:
            nuke.message("Error - no node selected")

    def bakeCameraSpace(self):
        """
        takes a camera that has had it's position altered (typically by an axis) and bakes it's altered world
        space into a new camera node
        """

        try:
            if nuke.selectedNode().Class() == "Camera2":
                self.__bakeWorldSpace(nuke.selectedNode())
            else:
                nuke.message("Selected node must be a Camera node")
        except:
            nuke.message("Error - no node selected.")

    # "private" methods

    def __duplicate(self, node):

        old = node
        new = nuke.createNode(old.Class())

        # duplicate all knobs
        newKnobs = new.knobs()
        oldKnobs = old.knobs()

        for knob in newKnobs:
            # get the same knob and copy values across
            new[knob].fromScript(old[knob].toScript())

        # set new DAG position for Node
        new.setXpos(old.xpos() - 200)
        new.setYpos(old.ypos())

        newNodeName = old.name() + '_duplicate'
        new['name'].setValue(newNodeName)
        new.setInput(0, None)

        return new

    def __bakeWorldSpace(self, camNode):
        # takes a camera and bake a new local matrix
        newCam = self.__duplicate(camNode)
        newCam["useMatrix"].setValue(True)
        newCam["matrix"].setExpression("%s.world_matrix" % camNode.name())
        return
