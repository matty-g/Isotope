"""
node_utils

Matt Greig
mattg.vfx@gmail.com
2016-12-21

description:
a collection of utilities and functions related to operations on Nuke Node class
"""

import nuke
import logging

logger = logging.getLogger(__name__)


def which_input(inputNode, outputNode):
    """
    given two nodes, it will return the index of outputNode.inputs()
    to which the inputNode is connected
    @param inputNode: the node for which outputNode is a dependent
    @param outputNode: the node for which inputNode is immediately upstream
    @return: None
    """
    numInputs = outputNode.inputs()
    idx = 0
    while idx < numInputs:
        # first need to check that name is not None otherwise it will crash
        # this occurs where unconnected inputs > 1 exist ie. a Viewer node
        if outputNode.input(idx) is not None:
            if outputNode.input(idx).name() == inputNode.name():
                return idx
        else:
            idx += 1


def is_nuke_node(text):
    """
    parses text (usually from clipboard buffer) for signatures unique to Nuke nodes
    @param text: str from clipboard buffer or mimeType passed in
    @return: bool
    """
    if 'tile_color' in text or 'xpos' in text:
        # it's a nuke node!
        return True

    return False


def _is_node_a_gizmo(node):
    """
    helper method for replaceGizmos()
    """
    if type(node) == 'Gizmo':
        return True
    else:
        return False


def layout_nodes(node_list, origin, label=None):

    buffer = 110
    idx = 1
    last_idx = len(node_list)
    co_ords = {}
    for node in node_list:
        node.setXYpos(origin[0] + (idx * buffer), origin[1])
        if idx == 1:
            co_ords['first'] = (node.xpos(), node.ypos())
        elif idx == last_idx:
            co_ords['last'] = (node.xpos(), node.ypos())

        idx += 1

    # now put a backdrop around them

    bdX = co_ords['first'][0]
    bdY = co_ords['first'][1]
    bdW = (co_ords['last'][0] + node.screenWidth()) - bdX
    bdH = (co_ords['first'][1] + node.screenHeight()) - bdY

    left, top, right, bottom = (-10, -80, 10, 10)

    bdX += left
    bdY += top
    bdW += (right-left)
    bdH += (bottom-top)

    bd = nuke.nodes.BackdropNode(xpos=bdX,
                                 bdwidth=bdW,
                                 ypos=bdY,
                                 bdheight=bdH+30,
                                 note_font_size=42
                                 )
    if label is not None:
        bd.knob('label').setValue(label)


    # add the label


def has_knob(node, knob_name):
    """Utility function that will return whether a given nuke node
    has a knob that has the given name.

    @type node: L{nuke.Node}
    @type knob_name: str
    @rtype: bool
    """

    try:
        node[knob_name]
        return True
    except NameError:
        return False