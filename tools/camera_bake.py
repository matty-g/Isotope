"""
camerabake

concatenates all downstream world-space transforms and bakes it out to a new camera
"""

import nuke


def get_concat_matrices_at_frame(node_list):

    req_matrix = {'TransformGeo': 'matrix', 'Camera2': 'world_matrix', 'Axis2': 'world_matrix', 'Camera': 'world_matrix', 'Axis': 'world_matrix'}
    req_classes = ['TransformGeo', 'Camera2', 'Axis2', 'Camera', 'Axis']

    mat_list = []

    for each in node_list:

        if each.Class() in req_classes:

            this_class = each.Class()
            new_mat = nuke.math.Matrix4()
            for i in range(0, 16):
                new_mat[i] = each[req_matrix[this_class]].valueAt(nuke.frame())[i]
            mat_list.append(new_mat)

            # check if it's transformgeo and if so... get the parent axis world_matrix too
            if this_class == 'TransformGeo':
                # get the axis world_matrix too
                if each.input(1) is not None:
                    in_node = each.input(1)
                    if in_node.Class() == 'Axis2' or in_node.Class() == 'Camera2' or in_node.Class() == 'Camera' or in_node.Class() == 'Axis':
                        axis_mat = nuke.math.Matrix4()

                        for i in range(0, 16):
                            axis_mat[i] = in_node[req_matrix[in_node.Class()]].valueAt(nuke.frame())[i]

                        mat_list.append(axis_mat)

    # # now concatenate them all together to create a new matrix

    i = 0
    result_mat = mat_list[0]
    while (i + 1) < len(mat_list):
        result_mat *= mat_list[i + 1]
        i += 1

    return result_mat


def bake_out_new_cam(sel_node):
    """
        walk back up the tree until you find the camera
        then transform the camera matrix by all the downstream
        4x4 transforms
        place that new matrix into a new camera
    """

    start_node = sel_node
    this_node = start_node
    cam_node = None

    tree_list = []

    while 'Camera' not in this_node.Class():

        tree_list.append(this_node)
        this_node = this_node.input(0)

    if this_node.Class() == 'Camera2' or this_node.Class() == 'Camera':
        cam_node = this_node
        tree_list.append(cam_node)

    if cam_node is None:
        nuke.message("No camera node found - did you select the right tree?")
        return

    concat_cam = _duplicate(cam_node)
    concat_cam['useMatrix'].setValue(True)
    concat_cam['matrix'].setAnimated()

    tree_list.reverse()

    for frame in range(int(nuke.root()['first_frame'].value()), int(nuke.root()['last_frame'].value() + 1)):
        nuke.frame(frame)
        result_mat = get_concat_matrices_at_frame(tree_list)

        for i in range(0, 16):
            concat_cam['matrix'].setValueAt(result_mat[i], nuke.frame(), i)

# helper methods


def _duplicate(node):
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

    idx = ''

    newNodeName = old.name() + '_duplicate' + idx
    new.setName(newNodeName, uncollide=True)

    new.setInput(0, None)

    return new


