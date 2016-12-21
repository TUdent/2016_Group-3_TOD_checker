# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LoadLayerDockWidget
                                 A QGIS plugin
 test
                             -------------------
        begin                : 2016-12-14
        git sha              : $Format:%H$
        copyright            : (C) 2016 by unknown
        email                : unknown
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic, QtCore

from qgis.core import *
from qgis.networkanalysis import *
from qgis.gui import *

import resources

import processing
import os
import os.path
import random

#from . import utility_functions as uf

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'load_layer_dockwidget_base.ui'))


class LoadLayerDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = QtCore.pyqtSignal()

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(LoadLayerDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        #define globals
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        self.panTool = QgsMapToolPan(self.canvas)
        self.clickTool.canvasClicked.connect(self.yayClicked)
        self.selectPoint.clicked.connect(self.showShow)

        #canvas
        #self.clickTool.canvasClicked.connect(self.yayClicked)

        #load layer
        self.loadRotterdamButton.clicked.connect(self.loadDataRotterdam)

        #show
        #self.showCoordinates.connect(self.showShow)
        self.showCoordinates.setReadOnly(True)

    def yayClicked(self, mapPoint, mouseButton):
        #print str(point.x()) + " , " +str(point.y()) )
        self.canvas.unsetMapTool(self.clickTool)
        if mapPoint:
            x_coor = mapPoint.x()
            y_coor = mapPoint.y()
            self.showCoordinates.append('(' + str(x_coor) + ', ' + str(y_coor) + ')')

    def showShow(self):
        point_selected = self.run_mouse()

    def run_mouse(self):
        self.canvas.setMapTool(self.clickTool)

    def loadDataRotterdam(self):
        try:
            data_path = os.path.join(os.path.dirname(__file__), 'sample_data','LayerRotterdam.qgs')
        except:
            self.createScenario()
        self.iface.addProject(data_path)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

