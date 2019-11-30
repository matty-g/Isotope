"""
path.py

path-based utilities created by Romain Maurer
"""


import datetime
import glob
import os
import re
import shutil
import uuid
import logging
from operator import attrgetter
from os import stat
from pwd import getpwuid


logger = logging.getLogger(__name__)

re_shot = re.compile(r'.*/shots/(?P<shot>[^/]+)/?.*')
re_version_take = re.compile(r'_v(?P<version>[0-9]+)_t(?P<take>[0-9]+)')
re_take = re.compile(r'_t(?P<take>[0-9]{2,})(?:[_.]|$)')
re_version_take_user = re.compile(r'_v(?P<version>[0-9]+)'
                                  r'(?:_t(?P<take>[0-9]+))?'

                                  # user initials have to be 2 letters and have to either be the end of the string
                                  # or be followed by an underscore or . only. This is to avoid some cases
                                  # where we have renders that have the version number followed by extension: v02_exr

                                  # NOTE: mgreig changing this to accomodate some users that now have 3-digit initals
                                  #       if things break - this is the first place to look!   
                                  r'(?:_    (?P<user>[a-z]{2,3}  (?=([_./]|$))  )  )?',
                                  re.VERBOSE)

re_file_parts = re.compile(r'(?P<basename>[.]?[^.]+)'
                           r'_v(?P<version>[0-9]+)'
                           r'(?:_t(?P<take>[0-9]+))?'
                           # NOTE: user intials patterns also changed below
                           r'(?:_(?P<user>[a-z]{2,3}))?'
                           r'(?:[._](?P<suffix>[^.]+))??'
                           r'([.](?P<frame>[0-9]+))?'
                           r'(?P<extension>[.][a-zA-Z]+)$'
                           , re.VERBOSE)

re_basename_version = re.compile(r'(?P<basename>[.]?[^.]+)_v(?P<version>.+)', re.VERBOSE)


class Version(object):
    """This data object wraps the current idea of a version at CE, which is
    a version number, an optional take and optional user initials.
    """

    def __init__(self, version, take=None, user=None):
        self.version = version
        self.take = take
        self.user = user

    def __eq__(self, other):
        if type(other) != Version:
            return False

        if self.version != other.version:
            return False

        if self.take != other.take:
            return False

        return self.user == other.user

    def __repr__(self):
        if self.take:
            take_msg = ', t=%02d' % self.take
        else:
            take_msg = ''

        if self.user:
            user_msg = ', user=%s' % self.user
        else:
            user_msg = ''

        msg = 'Version(v=%02d%s%s)' % (self.version, take_msg, user_msg)
        return msg

    def __hash__(self):
        if hasattr(self, '_hash'):
            return self._hash
        self._hash = hash('%s_%s_%s' % (self.version, self.take, self.user))
        return self._hash


def version_to_string(v, include_user_initials=False):
    """Utility function that returns a string version of the L{Version} object."""
    msg = 'v%02d' % v.version
    if v.take:
        msg += '_t%02d' % v.take

    if include_user_initials and v.user:
        msg += '_%s' % v.user

    return msg


def find_latest(filepath):
    """Given a file path that contains version and take information, this function
    will find the latest available version for that file.
    That function also supports filepath with wildcards. The comparison is made on the
    version and then on the take to decide which one is latest.

    @type filepath: str
    @return: the filepath that represents the latest version of the given filepath
    @rtype: str
    """

    search_pattern = re_version_take_user.sub('_v*', filepath)

    results = glob.glob(search_pattern)
    # print results
    if not results:
        return None

    path_by_version = {}
    for r in results:
        path_by_version[extract_version(r)] = r

    # sort by version and then by take
    sorted_versions = sorted(path_by_version.iterkeys(), key=attrgetter('version', 'take'))
    return path_by_version[sorted_versions[-1]]


def find_all_versions(filepath):
    """This function will return all the versions that exist for a given filepath.

    @type filepath: str
    @return: all the versions of the input file path indexed by Version object.
    @rtype: dict of {Version: str}
    """

    search_pattern = re_version_take_user.sub('_v*', filepath)
    results = glob.glob(search_pattern)
    if not results:
        return {}

    path_by_version = {}
    for r in results:
        path_by_version[extract_version(r)] = r

    return path_by_version


def next_available_take(filepath):
    """This function finds the next available take number based on existing file paths.
    Different user initials will not be considered. Only take matters.
    If no matching file path exists, 1 is returned.

    @type filepath: str
    @rtype: int
    """

    search_pattern = re_take.sub('_t*', filepath)
    results = glob.glob(search_pattern)
    if not results:
        return 1

    t = 0
    for r in results:
        re_obj = re_take.search(r)
        if re_obj:
            t = max(t, int(re_obj.group('take'), 10))

    return t + 1


def extract_version(filepath):
    """This function extracts version information from the given filepath.
    @type filepath: str
    @rtype: L{Version}
    """

    re_objs = list(re_version_take_user.finditer(filepath))
    if not re_objs:
        return Version(0, 0)

    version = None
    take = None
    user = None

    for re_obj in re_objs:
        if not version:
            if re_obj.group('version'):
                version = int(re_obj.group('version'), 10)
        if not take:
            if re_obj.group('take'):
                take = int(re_obj.group('take'), 10)
        if not user:
            user = re_obj.group('user')

    return Version(version, take, user)


def extract_basename_label(filename):
    re_obj = re_basename_version.match(filename)
    if not re_obj:
        return None
    else:
        return re_obj.group('basename')


def extract_file_parts(filepath):
    """Given the path to a file, this function will extract
    all relevant information and return a dict that contains
    all the parts of the file path such as the version, basename, extension, frame, ...

    @note: this function will only works with file paths, not folder paths.
    @type filepath: str
    @rtype: str
    """
    re_obj = re_file_parts.match(filepath)
    if not re_obj:
        return {}

    if re_obj.group('take'):
        take = int(re_obj.group('take'), 10)
    else:
        take = None

    if re_obj.group('user'):
        user = re_obj.group('user')
    else:
        user = None

    version = Version(int(re_obj.group('version'), 10), take, user)

    return {
        'basename': re_obj.group('basename'),
        'version': version,
        'extension': re_obj.group('extension'),
        'frame': re_obj.group('frame'),
        'suffix': re_obj.group('suffix')
    }


def extract_shot(filepath):
    """This function extracts shot information from the given filepath.
    @type filepath: str
    @rtype: shotname : str
    """
    if filepath is None:
        return None

    re_obj = re_shot.search(filepath)
    if not re_obj:
        return None

    return re_obj.group('shot')


def update_version(filepath, version):
    """This function takes a file path and updates its version and take information
    with the given version object.
    @type filepath: str
    @type version: L{Version}
    @return: the updated file path
    @rtype: str
    """

    filepath = re_version_take.sub('_v{version:02}_t{take:02}'.format(
        **{
            'version': version.version,
            'take': version.take
        }
    ), filepath)

    return filepath


def unique_id():
    """This function will give you a unique id string that can be used as a suffix for
    files that are automatically generated.
    This unique id starts with a time stamp for easy ordering in the console.
    @rtype: str
    """

    d = datetime.datetime.now()
    msg = '{time}_{uuid}'.format(**{
        'time': d.strftime('%y%m%d_%H%M%S'),
        'uuid': uuid.uuid4()
    })
    return msg


def sanitise_name(name, supported_chars=None):
    """This function will work on a given input name and return a cleaned up version of it.
    It will remove any illegal characters, replace spaces by underscore, and make it lowercase.
    Eg: "lighting (test)" >>> "lighting_test"

    By default, the list of characters supported include a-z, A-Z, 0-9 and _ but you can give it
    extra characters to support either as a list or a string so both are valid to add "-" and '#' as a
    supported character:

        sanitise_name('my-text', '-#')
        sanitise_name('my-text', ['-', '#'])

    @type name: str
    @type supported_chars: str or list of str
    @rtype: str
    """

    supported_chars = supported_chars or ''
    supported_chars = ''.join(['\%s' % c for c in supported_chars])

    pattern = r'[^a-zA-Z0-9_%s]+' % supported_chars
    new_name = re.sub(pattern, '_', name)
    new_name = new_name.lower()
    new_name = new_name.strip('_')
    return new_name


special_extensions = ['.bgeo.sc']


def extract_extension(path):
    """This function will return the extension of the given path.
    In some cases, os.path.splitext() does not give the expected result
    so this function takes care of special cases such as ".bgeo.sc."
    @type path: str
    @rtype: str
    """

    for special_ext in special_extensions:
        if path.endswith(special_ext):
            return special_ext

    return os.path.splitext(path)[-1]


def remove_extension(path):
    """This function will return the path without its extension.
    In some cases, os.path.splitext() does not give the expected result
    so this function takes care of special cases such as ".bgeo.sc."
    @type path: str
    @rtype: str
    """

    for special_ext in special_extensions:
        if path.endswith(special_ext):
            return path[:-len(special_ext)]

    return os.path.splitext(path)[0]


def size_anything_in_megabytes(path):
    return size_anything_in_bytes(path) / 1024.0 / 1024.0


def size_anything_in_bytes(path):
    """
    Takes a source directory and returns the entire size of all of it's
    content(s) in bytes.

    The function returns None if the size can't be properly calculated.
    """
    if not os.path.exists(path):
        return 0

    try:
        if os.path.isfile(path):
            return os.path.getsize(path)

    except (OSError, IOError):
        return 0

    if os.path.isdir(path):
        return sum(size_anything_in_bytes(os.path.join(path, name)) for name in os.listdir(path))

    return 0


class PathInterface(object):
    """Base class for L{File} and L{Sequence} classes."""

    @staticmethod
    def is_sequence():
        return False

    @staticmethod
    def is_file():
        return False

    def owner(self):

        """Returns the owner of the path.
        @return: the login of the user who owns the path.
        @rtype: str
        """

        raise NotImplementedError()

    def exists(self):
        raise RuntimeError()

    def exists_locally(self):
        return self.exists()

    def exists_on_remote_site(self):
        return self.exists_on_site(self._default_remote_site())

    def exists_on_site(self, site):
        po = self.__class__(site_path(self.reference_path(), site))
        return po.exists()

    def sync_locally(self):
        raise RuntimeError()

    def sync_to_remote_site(self):
        raise RuntimeError()

    def _default_remote_site(self):
        """Internal method to figure out what the remote site is."""
        location = os.getenv('CE_LOCATION')
        remotes = {'syd': 'bne', 'bne': 'syd'}
        remote = remotes.get(location.lower())
        if remote is None:
            raise RuntimeError('Cannot determine your location. Make sure CE_LOCATION environment variable is set.')
        return remote

    def reference_path(self):

        """The path that we be used to represent that file path or sequence in systems such as the publishing system."""

        raise RuntimeError()

    def reference_name(self):
        return os.path.basename(self.reference_path())

    def basename(self):
        raise NotImplementedError()

    def to_sync_path(self):
        raise NotImplementedError()

    def __hash__(self):
        if not hasattr(self, '__hash'):
            self.__hash = hash(self.reference_path())
        return self.__hash

    def __eq__(self, other):
        if not type(other) == self.__class__:
            return False
        return self.reference_path() == other.reference_path()

    def paths(self):
        return []

    def copy(self, path):

        """Copies all files from the current path object to the new given path."""

        raise NotImplementedError()

    def copy_basepath(self, path):

        """Copies all files from the current path object to the new given basename."""

        raise NotImplementedError()

    def _copy(self, src_path, dest_path):
        try:
            shutil.copy2(src_path, dest_path)
        except IOError as e:
            logger.error('Error during file copy: %s' % str(e))
            return False
        return True

    def size_in_megabytes(self):
        raise NotImplementedError()

    def info_dict(self):
        return {}


class Sequence(PathInterface):
    """Foundation class that provides methods to work with file sequences."""

    RePattern = re.compile('(?P<base>.*)'
                           '[.]'
                           '(?P<frame_pattern>'
                           '  [#]+'  # hashes
                           '| %\d\dd'  # %04d
                           '| \$F\d'  # $F4  - houdini
                           '| @+'  # @@@@
                           '| \d+-\d+\#'  # @@@@
                           '| \d+'  # 1034 or any frame number
                           '| \*'  # *
                           ') '
                           '(?P<ext>[.][^/]*)',  # .exr
                           re.VERBOSE)

    RePatternFrameNumberOnly = re.compile('(?P<base>.*)'
                                          '[.]'
                                          '(?P<frame_number>'
                                          '\d+'  # 1034 or any frame number
                                          ') '
                                          '(?P<ext>[.][^/]*)',  # .exr
                                          re.VERBOSE)

    # Special list of extensions that should not be treated as sequences.
    NonSequenceExtensions = ['.mov', '.mp4']

    @staticmethod
    def is_sequence():
        return True

    def __init__(self, path):

        """@type path: str"""

        self._path = path
        self._basepath = None
        self._extension = None
        self._frame_pattern = None
        self._padding = 0
        self._process_path()
        self._filepaths = []
        self._frames = []
        self._disk_checked = False

    def is_valid(self):
        return self._basepath is not None

    def _process_path(self):
        re_obj = self.RePattern.match(self._path)
        if not re_obj:
            return

        self._extension = re_obj.group('ext')
        if self._extension in self.NonSequenceExtensions:
            return

        self._basepath = re_obj.group('base')
        self._frame_pattern = re_obj.group('frame_pattern')
        self._padding = len(self._frame_pattern)

    def _process_disk(self):
        self._disk_checked = True

        # import time
        # start = time.time()
        self._filepaths = glob.glob(self.to_sync_path())
        # total = time.time() - start
        # if total > 0.01:
        #     print '%.03fs glob.' % total, self._path

        self._filepaths.sort()

        self._frames = []
        paddings = set()
        for f in self._filepaths:
            re_obj = self.RePatternFrameNumberOnly.match(f)
            if not re_obj:
                continue
            frame_number_group = re_obj.group('frame_number')
            self._frames.append(int(frame_number_group, 10))
            paddings.add(len(frame_number_group))
        self._frames.sort()

        if not paddings:
            return

        if len(paddings) > 1:
            logger.error('Multiple padding detected on sequence %s.' % self._path)

        self._padding = list(paddings)[0]

    def pattern(self, frame_pattern=None):
        if isinstance(frame_pattern, int):
            frame_pattern = ('{0:0%d}' % self._padding).format(frame_pattern)

        frame_pattern = frame_pattern or self._frame_pattern
        return '{base}.{frame_pattern}{ext}'.format(**{
            'base': self._basepath,
            'frame_pattern': frame_pattern,
            'ext': self._extension
        })

    def padding(self):
        if not self._disk_checked:
            self._process_disk()
        return self._padding

    def set_padding(self, padding):
        self._padding = padding

    def to_sync_path(self):
        return self.pattern('*')

    def basepath(self):

        """Returns the whole sequence path up to the frame number.

        eg. /a/b/c.0001.exr -> /a/b/c
        """
        return self._basepath

    def basename(self):

        """Returns the name of the sequence up to the frame number.

        eg. /a/b/c.0001.exr -> c
        """

        if not self._basepath:
            return None

        return os.path.basename(self._basepath)

    def frame_pattern(self):
        return self._frame_pattern

    def extension(self):
        return self._extension

    def start_frame(self):
        if not self._disk_checked:
            self._process_disk()
        if not self._frames:
            return None
        return self._frames[0]

    def end_frame(self):
        if not self._disk_checked:
            self._process_disk()
        if not self._frames:
            return None
        return self._frames[-1]

    def framerange(self):
        if not self._disk_checked:
            self._process_disk()
        return self._frames

    def names(self):
        if not self._disk_checked:
            self._process_disk()
        return [os.path.basename(p) for p in self._filepaths]

    def paths(self):
        if not self._disk_checked:
            self._process_disk()
        return self._filepaths

    def owner(self):
        paths = self.paths()
        if not paths:
            return None

        return File(paths[0]).owner()

    def exists(self):
        paths = self.paths()
        return bool(paths)

    def sync_to_remote_site(self):
        from ce_core import remote
        p = self.pattern('*')
        remote.put_file(p)

    def sync_locally(self):
        from ce_core import remote
        p = self.pattern('*')
        remote.get_file(p)
        self._disk_checked = False

    def reference_path(self):
        return os.path.normpath(self.pattern('#'))

    def info_dict(self):

        """Returns a dict of information about the sequence that contains information such as
           online status, start and end frame, missing frames, etc.
        """

        paths = self.paths()
        if not paths:
            return {
                'reference_path': self.reference_path(),
                'online': False,
                'nb_frames_available': 0,
                'is_sequence': True,
            }

        nb_frames = len(paths)
        missing_frames = []

        all_frames = set(self._frames)
        for frame in range(self.start_frame(), self.end_frame()):
            if frame not in all_frames:
                missing_frames.append(frame)

        seq_label = '%s.[%s-%s]%s' % (
            self.basename(),
            self.start_frame(),
            self.end_frame(),
            self.extension()
        )

        return {
            'reference_path': self.reference_path(),
            'online': True,
            'start_frame': self.start_frame(),
            'end_frame': self.end_frame(),
            'nb_frames_available': nb_frames,
            'nb_missing_frames': len(missing_frames),
            'missing_frames': missing_frames,
            'available_frames': list(all_frames - set(missing_frames)),
            'is_sequence': True,
            'label': seq_label
        }

    def copy(self, path):

        """Copies all files from the current path object to the new given path."""

        new_seq = Sequence(path)
        if not new_seq.is_valid():
            logger.error('Invalid sequence path: "%s". No copy has been made.' % path)
            return False

        for frame in self.framerange():
            src_path = self.pattern(frame)
            dest_path = new_seq.pattern(frame)

            if not self._copy(src_path, dest_path):
                return False

        return True

    def copy_basepath(self, path):
        for frame in self.framerange():
            frame_pattern = ('{0:0%d}' % self._padding).format(frame)
            src_path = self.pattern(frame_pattern)
            dest_path = '{base}.{frame_pattern}{ext}'.format(**{
                'base': path,
                'frame_pattern': frame_pattern,
                'ext': self._extension
            })

            if not self._copy(src_path, dest_path):
                return False

        return True

    def size_in_megabytes(self):
        total = sum([size_anything_in_bytes(p) for p in self.paths()])
        return total / 1024.0 / 1024.0


class File(PathInterface):
    """Foundation class that provides methods to work with simple files."""

    @staticmethod
    def is_file():
        return True

    def __init__(self, path):

        """@type path: str"""

        self._path = path

    def path(self):
        return self._path

    def paths(self):
        return [self._path]

    def to_sync_path(self):
        return self._path

    def name(self):
        return os.path.basename(self._path)

    def basename(self):
        return remove_extension(os.path.basename(self._path))

    def owner(self):
        id_ = stat(self._path).st_uid
        try:
            return getpwuid(id_).pw_name
        except KeyError:
            return str(id_)

    def exists(self):
        return os.path.exists(self._path)

    def sync_to_remote_site(self):
        from ce_core import remote
        remote.put_file(self._path)

    def sync_locally(self):
        from ce_core import remote
        remote.get_file(self._path)

    def reference_path(self):
        return os.path.normpath(self.path())

    def __repr__(self):
        return 'File(%s)' % self._path

    def info_dict(self):

        """Returns a dict of information about the file that contains information such as
           online status.
        """

        return {
            'reference_path': self.reference_path(),
            'online': self.exists_locally(),
            'is_sequence': False,
            'label': self.basename(),
        }

    def copy(self, path):

        """Copies all files from the current path object to the new given path."""

        return self._copy(self._path, path)

    def copy_basepath(self, path):

        """Copies all files from the current path object to the new given basename."""

        new_path = path + extract_extension(self.path())
        return self._copy(self._path, new_path)

    def size_in_megabytes(self):
        return size_anything_in_megabytes(self.path())

    def extension(self):
        return extract_extension(self.path())


def path_object(path):
    """Returns a L{Sequence} or L{File} based on the input.

    @type path: str
    @rtype: L{PathInterface}
    """

    path_obj = Sequence(path)
    if not path_obj.is_valid():
        path_obj = File(path)
    return path_obj


def list_path_objects(folder):
    """
    Given a folder, this function will return the folder content as
    L{PathInterface} objects, so either a L{File} or a L{Sequence}.

    @rtype: list of L{PathInterface}
    """

    obj_by_reference_path = {}
    for name in os.listdir(folder):
        obj = path_object(os.path.join(folder, name))
        obj_by_reference_path.setdefault(obj.reference_path(), obj)

    return obj_by_reference_path.values()


def ensure_folder_exists(folder):
    try:
        os.makedirs(folder)
    except OSError as e:
        # Folder Exists is errno 17. Reraise anything else.
        if e.errno != 17:
            raise


def site_path(path, site):
    """Converts a path to the given site version of the path so

        site_path('/prod/vfx/pipedev3', 'bne') -> /bne_prod/vfx/pipedev3

    """

    parts = path.split('/')
    parts[1] = '{site}_{silo}'.format(site=site, silo=parts[1])
    return '/'.join(parts)