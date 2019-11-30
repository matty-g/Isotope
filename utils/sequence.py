import os
import glob


def replace_frame_number_by_wildcard(file_path, wildcard='*'):

    """Replace the frame number with a * for globbing."""

    split_path = file_path.split('.')
    if len(split_path) < 3:
        return file_path

    split_path[-2] = wildcard
    return '.'.join(split_path)


def calc_range(template_file):
    '''
    Make a glob of the filename, get the listing
    return the min and max of the values where we expect the frame numbers to be.
    Which should be just before the prefix, eg. foo_bar.0101.exr
    '''
    template_file = os.path.realpath(template_file)
    template_glob=glob_frame_number(template_file)
    if template_glob is None:
        return (None,None)
    file_list=glob.glob(template_glob)
    numbers_list = []
    for curr_file in file_list:
        numbers_list.append(int(curr_file.split('.')[-2]))

    return (min(numbers_list),max(numbers_list))


def glob_frame_number(template_file):
    '''
    Replace the frame number with a * for globbing
    '''
    template_split=template_file.split('.')
    if len(template_split) < 3:
        return None

    template_split[-2] = '*'
    new_file='.'.join(template_split)

    return new_file