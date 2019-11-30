"""
chan_export.py

by Matt Greig (mattg.vfx@gmail.com)

v1.0  2018-01-30

adds a context menu option to a knob to facilitate export of a .chan file from a knob's animation
primarily intended for export of retime curves for 3D

Notes: exports animation curves as value @ time for the selected knob only

"""
import nuke
import os


def execute():
    create_chan()


def create_chan():
    sel_knob = nuke.thisKnob()
    fr_range = range_prompt()

    if not fr_range:
        return

    start = int(fr_range.split('-')[0])
    end = int(fr_range.split('-').pop())

    # prompt for location to save (default to camera location)
    # TODO: change this to be configurable
    cam_dir = os.path.join(os.getenv('SHOTDIR'), 'cams/')
    chan_file_path = nuke.getFilename('Select .chan destination', pattern='*.chan', default=cam_dir)

    # sanitise to check that the correct .chan suffix was appended by user
    if chan_file_path:
        if '.chan' not in chan_file_path:
            chan_file_path += '.chan'

        # now proceed
        export_chan_file(start, end, sel_knob, chan_file_path)


def range_prompt():
    """
    creates dialog to get user input for the frame range to export to the .chan file
    """
    first = int(nuke.root().knob('first_frame').value())
    last = int(nuke.root().knob('last_frame').value())

    pnl = nuke.getFramesAndViews('frame range', '{}-{}'.format(first, last))
    try:
        fr_range = pnl[0]
    except TypeError:
        return None

    return fr_range


def export_chan_file(start, end, knob, chan_file):
    """
    .chan format is:
    {frame}\t{value}\n
    """
    idx = start

    with open(chan_file, 'w') as output:
        while idx <= end:
            line = '{}\t{}\n'.format(idx, knob.getValueAt(idx))
            output.write(line)
            idx += 1
    output.close()
