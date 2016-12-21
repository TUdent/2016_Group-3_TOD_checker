# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GetAttributesDockWidget
                                 A QGIS plugin
 test
                             -------------------
        begin                : 2016-12-16
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
from qgis.core import *

from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'get_attributes_dockwidget_base.ui'))


class GetAttributesDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(GetAttributesDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        self.iface = iface
        self.layers = self.iface.legendInterface().layers()
        self.layer_list = []
        for layer in self.layers:
            self.layer_list.append(layer.name())
        self.comboBox.addItems(self.layer_list)

        self.pushButton.clicked.connect(self.yesClicked)
        
    def yesClicked(self, layers):
        self.showAttributes.clear()
        selectedLayerIndex = self.comboBox.currentIndex()
        selectedLayer = self.layers[selectedLayerIndex]
        fields = selectedLayer.pendingFields()
        fieldnames = [field.name() for field in fields]
        self.showAttributes.append('wkt_geom, ' + ', '.join(str(name) for name in fieldnames) + '\n')
        
        for f in selectedLayer.getFeatures():
            if f.geometry().wkbType() == QGis.WKBMultiPoint:
                line = str(f.geometry().asMultiPoint()) + ', ' + ', '.join(str(f[x]) for x in fieldnames) + '\n'
            if f.geometry().wkbType() == QGis.WKBMultiLineString:
                line = str(f.geometry().asMultiPolyline()) + ', ' + ', '.join(str(f[x]) for x in fieldnames) + '\n'
            if f.geometry().wkbType() == QGis.WKBMultiPolygon:
                line = str(f.geometry().asMultiPolygon()) + ', ' + ', '.join(str(f[x]) for x in fieldnames) + '\n'
            if f.geometry().wkbType() == QGis.WKBPoint:
                line = str(f.geometry().asPoint()) + ', ' + ', '.join(str(f[x]) for x in fieldnames) + '\n'
            if f.geometry().wkbType() == QGis.WKBLineString:
                line = str(f.geometry().asPolyline()) + ', ' + ', '.join(str(f[x]) for x in fieldnames) + '\n'
            if f.geometry().wkbType() == QGis.WKBPolygon:
                line = str(f.geometry().asPolygon()) + ', ' + ', '.join(str(f[x]) for x in fieldnames) + '\n'

            #unicode_line = line.encode('utf-8')
            self.showAttributes.append(line)
        

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

