import platform
import subprocess
import re
import nuke

# DEBUGGING FLAGS

debugFlag = None  # turns debug statements off by default

def debugLog(message):
    """
    small function to format and display a debug message to stdout
    only if debugFlag is not set to None
    """
    if debugFlag != None:
        print "#debug: " + str(message)

def openExplorerWithPath(path):
    cmd = "explorer %s, shell=True" % path
    subprocess.Popen("explorer C:\\Nuke_Temp", shell=True)

#def openShell:
#    #find the OS in use
#    #if platform.system() == "Windows":
#        #open explorer at the path intended

def scanForExtremeBBox(maxTolerance):
    """
    <usage: scanForExtremeBBox(maxTolerance<value between 0.1 to 1)>
    parses the bbox area of each node in the script to find where bboxes exceed maxTolerance of the root format area
    will change node colour to the warning colour when positive
    """
    # constant
    warningColor = 3942580479 # yellow

    # find the area of the root.format of the scene
    frameArea = nuke.Root().format().width() * nuke.Root().format().height()
    maxFrameArea = frameArea + (frameArea * maxTolerance)

    for node in nuke.allNodes():
        # if bboxArea exceeds frameArea + tolerance - flag it by setting the node colour to yellow
        nodeBBoxArea = node.bbox().w() * node.bbox().h()
        if nodeBBoxArea > maxFrameArea:
            # set the node colour to yellow
            node["tile_color"].setValue(3942580479)

        elif nodeBBoxArea < maxFrameArea and node["tile_color"].value() == 3942580479:
            # what if node WAS yellow, but adjustments make the bbox ok? Change back to default colour
            # get the default colour by quickly creating a node of the same class, getting the tile_color value,
            # then deleting it

            tmpNode = nuke.createNode(node.Class())
            defaultColour = tmpNode["tile_color"].value()
            node["tile_color"].setValue(defaultColour)

            # now delete the temp node
            nuke.delete(tmpNode)

    return None

def BBoxDimensionString(bboxInfo):
    """
    takes the value of the bbox from a node and displays a string of it's values
    """
    return "%d, %d, %d, %d" % (bboxInfo.x(), bboxInfo.y(), bboxInfo.w(), bboxInfo.h())

def displayBBoxInfoForNode(node):
    """
    takes a node and returns a display string containing its bbox
    """
    return "%s: %s" % (node.name(), BBoxDimensionString(node.bbox()))

def makeLogC():
    """
    changes to colourspace for the selectedNodes to AlexaV3LogC
    """
    counter = 0
    for each in nuke.selectedNodes():
        each["colorspace"].setValue("AlexaV3LogC")
        counter += 1

    print "## changed colourspace for %d nodes" % counter

def lutList():
    """
    returns a list of the LUTS in the Nuke session
    """
    sessionLuts = nuke.Root()["luts"]
    luts = re.findall('[a-zA-Z0-9.*]+', sessionLuts.toScript())
    return luts

def changeColorPanel():
    """
    displays all current read nodes and their existing colorspace
    select a colorspace to change to, and then select the read nodes
    you wish to change, and click OK
    """
    panel = nuke.Panel('Change Colorspace')

    #add pulldown for choice of colorspace
    luts = ' '.join(lutList())
    spaces = panel.addEnumerationPulldown("new colorspace", luts)

    for each in nuke.allNodes("Read"):
        readFileName = each["file"].value().split('/').pop().split('.').pop(0)
        panel.addBooleanCheckBox("%s :[%s]" % (readFileName, each["colorspace"].value()), False)

    ret = panel.show()

    for each in nuke.allNodes("Read"):
        readFileName = each["file"].value().split('/').pop().split('.').pop(0)
        if panel.value("%s :[%s]" % (readFileName, each["colorspace"].value())):
            each["colorspace"].setValue(panel.value("new colorspace"))

def isNodeAGizmo(aNode):
    """
    helper method for replaceGizmos()
    """
    if type(aNode) == 'Gizmo':
        return True
    else:
        return False

def replaceGizmos():
    """
    <usage>: duplicates all gizmos in a script to a group node
    avoids errors with network processing (ie. rendering on a farm)
    where the gizmo is stored locally (ie. $HOME/.nuke)
    preserves existing knob values
    """
    # parse through script

    #make a list of all gizmos
    scriptgizmos = []
    debugLog("number of gizmos in script is: %d" % len(scriptgizmos))
    # print "#debug: number of gizmos in script is: %d" % len(scriptgizmos)

    #find the gizmos
    for each in nuke.allNodes():
        debugLog("testing node %s and type is: %s" % (each.name(), type(each)))
        if type(each) is nuke.Gizmo:

            debugLog("%s is a gizmo." % each.name())
            scriptgizmos.append(each)

    # now we have the gizmos - go through and replace them

    #TODO: implement a try-catch block here
    for gizmo in scriptgizmos:
        convertToGroup(gizmo)

        #TODO: need to delete the original gizmos here
        nuke.delete(gizmo) # note - can be fixed with an undo

def convertToGroup(gizmo):
    """
    <usage>: function takes a gizmo Type and performs copy to group
    while preserving all knob values and input(s)/output(s)
    """

    # copy gizmo to group
    newGrpNode = gizmo.makeGroup()

    # give the group a name to identify it's origins
    newGrpName = gizmo.name() + "_grp"
    newGrpNode.setName(newGrpName)

    # set the new groups position to an offset of it's original gizmo pos
    newGrpNode.setXpos(gizmo.xpos())
    newGrpNode.setYpos(gizmo.ypos())

    #get number of inputs
    numInputs = gizmo.inputs()
    idx = 0

    #iterate through inputs and assign new connections
    while idx < numInputs:
        newGrpNode.setInput(idx, gizmo.input(idx))
        idx += 1

    # do the same for outputs

    outputs = gizmo.dependent()

    debugLog("dependencies for %s are: " % gizmo.name())
    debugLog(outputs)

    #iterate through outputs

    for connNode in outputs:

        #find the input that's connected to the original gizmo

        connectedIdx = whichInput(gizmo, connNode)
        debugLog("connected index is %d" % connectedIdx)
        #connect it to the new Group node
        connNode.setInput(connectedIdx, newGrpNode)

    #get input(s) and output for gizmo and assign to new node

    #TODO: set return type to be a BOOL

def whichInput(input, output):
    """
    helper method for replaceGizmos()
    finds the input index to which the upstream output is connected
    input - upstream node for which we are tracing
    output - the node which is dependent on input
    """
    debugLog("whichInput called to check input: %s and output: %s" % (input.name(), output.name()))
    numInputs = output.inputs()
    idx = 0
    while idx < numInputs:
        # first need to check that name is not None otherwise it will crash
        # this occurs where unconnected inputs > 1 exist ie. a Viewer node
        if output.input(idx) is not None:
            if output.input(idx).name() == input.name():
                return idx
        else:
            idx += 1


    #TODO: write func to display a list of gizmos used in script

