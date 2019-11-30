"""
node_utils

Matt Greig
mattg.vfx@gmail.com
2019-11-31

description:
a collection of utilities and functions related to operations for the Nuke DAG
"""

import nuke
from utils.node_utils import which_input
import path



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
        node_format_dimensions = node.format().width() * node.format().height()
        max_node_area = node_format_dimensions + (node_format_dimensions * maxTolerance)
        nodeBBoxArea = node.bbox().w() * node.bbox().h()
        if nodeBBoxArea > max_node_area:
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


def displayBBoxInfoForNode(node):
    """
    takes a node and returns a display string containing its bbox
    """
    return "%s: %s" % (node.name(), _BBoxDimensionString(node.bbox()))


def replace_gizmos():
    """
    <usage>: duplicates all gizmos in a script to a group node
    avoids errors with network processing (ie. rendering on a farm)
    where the gizmo is stored locally (ie. $HOME/.nuke)
    preserves existing knob values
    """
    # parse through script

    # make a list of all gizmos
    scriptgizmos = []

    # find the gizmos
    for each in nuke.allNodes():
        if type(each) is nuke.Gizmo:
            scriptgizmos.append(each)

    # now we have the gizmos - go through and replace them
    # TODO: implement a try-catch block here
    for gizmo in scriptgizmos:
        convert_to_group(gizmo)
        nuke.delete(gizmo)  # note - can be fixed with an undo


def convert_to_group(gizmo):
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

    # get number of inputs
    numInputs = gizmo.inputs()
    idx = 0

    # iterate through inputs and assign new connections
    while idx < numInputs:
        newGrpNode.setInput(idx, gizmo.input(idx))
        idx += 1

    # do the same for outputs
    outputs = gizmo.dependent()

    # iterate through outputs
    for connNode in outputs:
        # find the input that's connected to the original gizmo
        connectedIdx = which_input(gizmo, connNode)
        # connect it to the new Group node
        connNode.setInput(connectedIdx, newGrpNode)


def postageStampsToggle():
    for node in nuke.allNodes():
        if node.Class() == "Read":
            if node["postage_stamp"].value():
                node["postage_stamp"].setValue(0)
            else:
                node["postage_stamp"].setValue(1)


def resetNodesToDefaultColours(nodes):
    """
    resets any affected nodes back to their original node colours
    @param nodes: a list of Nuke nodes to change to default colours
    @return: None
    """

    try:
        for node in nodes:
            # apply only to those nodes that are yellow
            if node['tile_color'].value() == 3942580479:
                # get tmp node based on class
                tmpNode = nuke.createNode(node.Class())
                defaultColour = tmpNode["tile_color"].value()
                node["tile_color"].setValue(defaultColour)
                nuke.delete(tmpNode)

    except TypeError:
        print "ERROR! argument must be a list, even if it's a single element"


def deselect_nodes():
    """Utility function that ensures no nodes in the DAG are selected.
    This is important when performing copy/paste and insert operations.
    It returns the list of nodes that were selected before we cleared out the selection.

    @rtype: list of L{nuke.Node}
    """

    selected_nodes = nuke.selectedNodes()

    for each in selected_nodes:
        each.knob('selected').setValue(False)

    return selected_nodes


def replace_node_selection(nodes):
    """This function will replace the current list of selected nodes
    by the ones given.
    It will return the list of nodes that were previously selected.

    @type nodes: list of L{nuke.Node}
    @rtype nodes: list of L{nuke.Node}
    """

    selected_nodes = deselect_nodes()
    for node in nodes:
        node['selected'].setValue(True)
    return selected_nodes


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


def directory_load():

    user_path = nuke.getInput('Path to files:', 'path')

    if user_path:
        results = _parse_dir(user_path)
        _create_reads(results)


# Helper Methods

def _parse_dir(dir_path):

    results = []

    for directory, dirnames, filenames in os.walk(dir_path):
        if filenames:

            results.extend(path.list_path_objects(directory))

    return results


def _create_reads(results):

    movs = ['mov', 'mp4', 'mkv']
    count = 0
    seqs = []
    files = []

    for result in results:

        if result.is_sequence():
            if '.checkpoint' not in result.extension():
                count += 1
                seqs.append(result)

        if result.is_file() and any(ext in result.basename() for ext in movs):
            count += 1
            files.append(result)

    if count > 0:
        if nuke.ask('About to import {} read nodes.'.format(count)):
            # proceed
            for task in seqs:
                new_read = nuke.createNode('Read')
                new_read.knob('file').setValue(task.pattern(frame_pattern='%04d'))
                new_read.knob('first').setValue(task.start_frame())
                new_read.knob('last').setValue(task.end_frame())

            for task in files:
                new_read = nuke.createNode('Read')
                new_read.knob('file').fromUserText(task.reference_path())

    else:
        nuke.message('No sequences found to import.')


def _BBoxDimensionString(bboxInfo):
    """
    takes the value of the bbox from a node and displays a string of it's values
    """
    return "%d, %d, %d, %d" % (bboxInfo.x(), bboxInfo.y(), bboxInfo.w(), bboxInfo.h())

