"""
netcopy/netpaste

copies the selected nodes to a network share so other artists can then selct and paste the buffer
"""

import nuke
import os
import Qt.QtGui as QtGui
from Qt.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel, QPushButton, QListWidgetItem
from nukescripts import panels

net_copy_dir = "add/custom/dir/here"


def netcopy():
    # get selected nodes and write them to disk using a predefined, $USER-centric name
    if not nuke.selectedNodes():
        nuke.message("No nodes selected for copying")
        return
    path = os.path.join(net_copy_dir, build_filename())
    nuke.nodeCopy(path)


def netpaste(buffer_name):
    nuke.nodePaste(buffer_name)


def build_filename():
    # build filename from username
    user = os.getenv('USER')
    filename = '{}_copy.nkcp'.format(user)

    return filename


def get_list_of_copy_files():
    # sort by modification time
    mtime = lambda x: os.stat(os.path.join(net_copy_dir, x)).st_mtime
    return list(sorted(os.listdir(net_copy_dir), key=mtime, reverse=True))


class NetPasteWidget(QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        # create the main widget window
        self.setLayout(QVBoxLayout())

        # create the List Widget
        self.myList = QListWidget()
        self.update()
        self.myList.setWindowTitle("NetPaste Buffer Select")
        self.myList.itemClicked.connect(self.clicked)

        # create the display label
        self.list_label = QLabel("Available NetPaste Buffers")

        # create the button to refresh
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh)

        # add the widgets
        self.layout().addWidget(self.list_label)
        self.layout().addWidget(self.myList)
        self.layout().addWidget(self.refresh_btn)

    def refresh(self):
        # remove all existing items in the list
        self.myList.clear()
        # add everything in the netpaste loc dir
        self.update()

    def clicked(self, item):
        netpaste(os.path.join(net_copy_dir, item.text()))

    def update(self):
        idx = 1
        for each in get_list_of_copy_files():
            new_item = QListWidgetItem()
            new_item.setText(each)
            if idx % 2 == 0:
                # give bg a slightly different shade
                new_item.setBackground(QtGui.QColor('#222222'))
            idx += 1
            self.myList.addItem(new_item)

    def closeEvent(self, event):
        global np
        if np is not None:
            np = None


# standard Nuke-fu to persist the window
np = None

moduleName = __name__
if moduleName == '__main__':
    moduleName = ''
else:
    moduleName += '.'

panels.registerWidgetAsPanel(moduleName + 'NetPasteWidget', 'NetPaste Browser', 'com.mattgreig.NetPasteWidget')


def display_netpaste_buffer():
    global np

    # try and make this sucker a singleton so we don't clutter up the screen with windows!
    if np is None:
        np = NetPasteWidget()
        np.show()

    else:
        np.activateWindow()


