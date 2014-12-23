import platform
import subprocess
import re
import nuke


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
