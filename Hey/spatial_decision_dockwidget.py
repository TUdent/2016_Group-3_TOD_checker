# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SpatialDecisionDockWidget
                                 A QGIS plugin
 This is a SDSS template for the GEO1005 course
                             -------------------
        begin                : 2015-11-02
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Jorge Gil, TU Delft
        email                : j.a.lopesgil@tudelft.nl
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

from PyQt4 import QtGui, QtCore, uic
from qgis.core import *
from qgis.networkanalysis import *
from qgis.gui import *

#for visualisation
import numpy
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import math as m

# Initialize Qt resources from file resources.py
import resources

import processing
import os
import os.path
import random
import webbrowser
import csv

from . import utility_functions as uf
#import mpl_toolkits.basemap.pyproj as pyproj

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'spatial_decision_dockwidget_base.ui'))


class SpatialDecisionDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = QtCore.pyqtSignal()
    #custom signals
    updateAttribute = QtCore.pyqtSignal(str)

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(SpatialDecisionDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        # define globals
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        self.clickTool = QgsMapToolEmitPoint(self.canvas)
        self.panTool = QgsMapToolPan(self.canvas)
        # self.touchTool = QgsMapToolTouch(self.canvas)

        # data
        self.loadRotterdamButton.clicked.connect(self.warningLoadData)
        #self.createScenarioButton.clicked.connect(self.createScenario)
        #self.scenarioCombo.currentIndexChanged.connect(self.scenarioChanged)
        self.scenarioPath = QgsProject.instance().homePath()
        self.scenarioCombo.clear()
        self.scenarioCombo.addItem('Rotterdam')
        self.scenarioAttributes = {}
        self.subScenario = {}

        self.layers = self.iface.legendInterface().layers()
        self.layer_list = []
        for layer in self.layers:
            self.layer_list.append(layer.name())


        # set up GUI operation signals

        # canvas
        self.clickTool.canvasClicked.connect(self.yayClicked)
        self.startButton.clicked.connect(self.showShow)
        self.finishButton.clicked.connect(self.stop)
        self.values = []
        self.attributes = []
        #self.clickTool.canvasClicked.connect(self.handleMouseDown)

        # analysis
        self.showCoordinates.setReadOnly(True)
        self.showCoordinates.setFontPointSize(12)

        # visualisation


        # reporting

        # set current UI restrictions
        
        # add matplotlib Figure to chartFrame
        self.chart_figure = Figure()
        self.chart_canvas = FigureCanvas(self.chart_figure)
        self.chartLayout.addWidget(self.chart_canvas)

        # initialisation
        #self.updateLayers()

        #run simple tests

    def closeEvent(self, event):
        # disconnect interface signals
        try:
            self.iface.projectRead.disconnect(self.updateLayers)
            self.iface.newProjectCreated.disconnect(self.updateLayers)
            self.iface.legendInterface().itemRemoved.disconnect(self.updateLayers)
            self.iface.legendInterface().itemAdded.disconnect(self.updateLayers)
        except:
            pass

        self.closingPlugin.emit()
        self.canvas.unsetMapTool(self.clickTool)
        self.lyrs = self.iface.legendInterface().layers()
        for lyr in self.lyrs:
            if lyr.name() == 'Walking Range':
                QgsMapLayerRegistry.instance().removeMapLayer(lyr)
        self.values = []
        self.attributes = []
        self.clearTable()
        self.clearCoordinates()
        self.clearChart()
        event.accept()



#######
#   Data functions
#######
    def loadDataRotterdam(self):
        try:
            data_path = os.path.join(os.path.dirname(__file__), 'sample_data','LayerRotterdam.qgs')
        except:
            self.errorOccurs()
        self.iface.addProject(data_path)
        self.updateLayers()

        # initialize
        #self.baseAttributes()
        #self.sliderInit()

    def baseAttributes(self):
        # get summary of the attribute
        layer = uf.getLegendLayerByName(self.iface, "Rotterdam_gridStatistics")
        summary = []
        # only use the first attribute in the list
##        for feature in layer.getFeatures():
##            summary.append(feature)#, feature.attribute(attribute)))
        self.scenarioAttributes["Rotterdam"] = summary
        # send this to the table
        self.clearTable()
        self.updateTable()

    def updateLayers(self):
        self.layers = self.iface.legendInterface().layers()
        self.layer_list = []
        for layer in self.layers:
            self.layer_list.append(layer.name())

    def errorOccurs(self):
        msgBox = QtGui.QMessageBox()
        msgBox.setText("Oopsy it's not there!")
        msgBox.setStandardButtons(QtGui.QMessageBox.Yes)
        msgBox.setDefaultButton(QtGui.QMessageBox.Yes)


#######
#    Analysis functions
#######

    def yayClicked(self, mapPoint, mouseButton):
        r = 800
        if mapPoint:
            if self.iface.activeLayer() not in self.layers:
                self.iface.setActiveLayer(self.layers[0])
            self.active_layer = self.iface.activeLayer()
            self.layercrs = self.active_layer.crs()
            if self.active_layer != None:
                x = mapPoint.x()
                y = mapPoint.y()
                self.showCoordinates.append('(' + str(x) + ', ' + str(y) + ')')
                self.values.append((x, y))
                self.attributes.append(self.within_range(x, y, r, self.active_layer))
        self.buffersize = r
        self.outputlayername = 'Walking Range'
        #Create the memory layer for the result
        layeruri = 'Polygon?'
        #CRS needs to be specified
        crstext = 'PROJ4:%s' % self.layercrs.toProj4()
        layeruri = layeruri + 'crs=' + crstext
        memresult = QgsVectorLayer(layeruri, self.outputlayername, 'memory')
        outbuffername = 'Walking Distance.shp'
        #bufflayer = QgsVectorLayer(outbuffername, '800m', 'ogr')
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPoint(QgsPoint(x, y)).buffer(r, 50))
        provider = memresult.dataProvider()
        memresult.startEditing()
        provider.addFeatures([feature])
        memresult.setLayerTransparency(70)
        memresult.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayers([memresult])

    def showShow(self):
        point_selected = self.run_mouse()

    def run_mouse(self):
        self.canvas.setMapTool(self.clickTool)

    def stop(self):
        self.canvas.unsetMapTool(self.clickTool)
        if len(self.values) > 2:
            self.updateTable(self.values, self.attributes)
            self.clearChart()
        elif len(self.values) == 1:
            self.plotRadar(self.attributes[0])
        else:
            self.plotRadar(self.attributes[0])
            self.plotRadar(self.attributes[1], 'g')

    def within_range(self, x, y, r, layer):
        i = 0
        for f in layer.getFeatures():
            if f.geometry().wkbType() == QGis.WKBMultiPoint:
                geom = f.geometry().asMultiPoint()
                xf = geom[0][0]
                yf = geom[0][1]
                if m.sqrt((x-xf)**2+(y-yf)**2) <= r:
                    i += 1
            elif f.geometry().wkbType() == QGis.WKBPoint:
                geom = f.geometry().asPoint()
                xf = geom[0]
                yf = geom[1]
                if m.sqrt((x-xf)**2+(y-yf)**2) <= r:
                    i += 1
        return i

    def clearCoordinates(self):
        self.showCoordinates.clear()

    def warningLoadData(self):
        msgBox = QtGui.QMessageBox()
        msgBox.setText("This will delete all current layers, continue?")
        msgBox.setStandardButtons(QtGui.QMessageBox.Yes)
        msgBox.addButton(QtGui.QMessageBox.No)
        msgBox.setDefaultButton(QtGui.QMessageBox.No)
        if msgBox.exec_() == QtGui.QMessageBox.Yes:
            self.loadDataRotterdam()



#######
#    Visualisation functions
#######
    def plotRadar(self, attribute, color = 'b'):
        labels = numpy.array(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
        datalength = 8
        standard = numpy.array([10]*8)
        data = numpy.array([attribute, 2, 3, 4, 5, 6, 7, 8])
        angles = numpy.linspace(0, 2*numpy.pi, datalength, endpoint = False)
        standard = numpy.concatenate((standard, [standard[0]]))
        data = numpy.concatenate((data, [data[0]]))
        angles = numpy.concatenate((angles, [angles[0]]))
        #fig = plt.figure()
        self.ax = self.chart_figure.add_subplot(111, polar = True)
        self.ax.plot(angles, standard, 'r', linewidth = 2)
        self.ax.fill(angles, standard, 'r', alpha = 0.2)
        self.ax.plot(angles, data, color, linewidth = 2)
        self.ax.fill(angles, data, color, alpha = 0.2)
        self.ax.set_thetagrids(angles*180/numpy.pi, labels)
        self.ax.set_title('TOD')
        #self.ax.grid = True
        self.chart_canvas.draw()
##            else:
##                self.clearChart()

    def clearChart(self):
        #self.ax.grid = False
        self.chart_figure.clear()
        self.chart_canvas.draw()



#######
#    Reporting functions
#######
    # table window functions
    def updateTable(self, values, attributes):
        tobesorted = []
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(['Coordinates', 'Train Stations'])
        self.tableWidget.setRowCount(len(values))
        for i in range(len(values)):
            tobesorted.append((attributes[i], values[i]))
        tobesorted.sort(reverse = True)
        for i in range(len(tobesorted)):
            self.tableWidget.setItem(i, 0, QtGui.QTableWidgetItem(unicode(tobesorted[i][1])))
            self.tableWidget.setItem(i, 1, QtGui.QTableWidgetItem(unicode(tobesorted[i][0])))
        self.tableWidget.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.tableWidget.resizeRowsToContents()

    def clearTable(self):
        self.tableWidget.clear()
