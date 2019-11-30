import nuke
import logging
from utils import sequence

logger = logging.getLogger(__name__)


def read_from_write():

    """
    takes the information from a write node and builds a read node.
    """

    # check if it's flat or a deep read

    nodes = nuke.selectedNodes()

    for n in nodes:

        file_path = n['file'].evaluate()
        logger.debug('file path: {}'.format(file_path))
        frame_padding = '%04d'

        node_type = None

        if n.Class() == "DeepWrite":
            node_type = "DeepRead"

        elif n.Class() == "WriteGeo":
            node_type = "ReadGeo"

        else:
            node_type = "Read"

        try:
            # catch the error where no frames at file_path are present
            file_path = sequence.replace_frame_number_by_wildcard(file_path, wildcard=frame_padding)
            frame_range = sequence.calc_range(file_path)
            first = frame_range[0]
            last = frame_range[-1]
            logger.debug("first: {}  - last: {}".format(first, last))

        except ValueError:
            logger.debug("Couldn't find any frames in the render directory. Probably not rendered.")
            nuke.message('No frames found.')
            # qt_mov = True
            return

        logger.debug('creating read node with file path: {}'.format(file_path))

        if first is None:
            read = nuke.createNode(node_type, 'file {'+file_path+'}')

        else:
            read = nuke.createNode(node_type)

        read['file'].setValue(file_path)
        read['xpos'].setValue(n['xpos'].value())
        read['ypos'].setValue(n['ypos'].value() + 100)

        if node_type is not "ReadGeo" and first is not None and '.mov' not in file_path:

            read['first'].setValue(first)
            read['last'].setValue(last)
            read['origfirst'].setValue(first)
            read['origlast'].setValue(last)