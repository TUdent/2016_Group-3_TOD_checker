# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SelectRangeDockWidget
                                 A QGIS plugin
 test
                             -------------------
        begin                : 2016-12-21
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

from PyQt4 import QtGui, QtCore, uic
from PyQt4.QtCore import pyqtSignal
from qgis.core import *
from qgis.gui import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'select_range_dockwidget_base.ui'))


class SelectRangeDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(SelectRangeDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.iface = iface
        #get all layers
        self.layers = self.iface.legendInterface().layers()
        self.layer_list = []
        for layer in self.layers:
            self.layer_list.append(layer.name())
            if 'landcover' in layer.name():
                self.layercrs = layer.crs()

        #canvas tool
        self.canvas = self.iface.mapCanvas()
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        self.clickTool.canvasClicked.connect(self.goClicked)
        self.selectRange.clicked.connect(self.selection)

    def goClicked(self, mapPoint, mouseButton):
        self.canvas.unsetMapTool(self.clickTool)
        if mapPoint:
            r = 800
            x = mapPoint.x()
            y = mapPoint.y()
        self.buffersize = r
        self.outputlayername = 'Walking Range'
        #Create the memory layer for the result
        layeruri = 'Polygon?'
        #CRS needs to be specified
        crstext = 'PROJ4:%s' % self.layercrs.toProj4()
        layeruri = layeruri + 'crs=' + crstext
        memresult = QgsVectorLayer(layeruri, self.outputlayername, 'memory')
        outbuffername = 'Walking Distance.shp'
        bufflayer = QgsVectorLayer(outbuffername, '800m', 'ogr')
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPoint(QgsPoint(x, y)).buffer(r, 5))
        provider = memresult.dataProvider()
        memresult.startEditing()
        provider.addFeatures([feature])
        memresult.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayers([memresult])
        

    def selection(self):
        point_selected = self.run_mouse()

    def run_mouse(self):
        self.canvas.setMapTool(self.clickTool)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

