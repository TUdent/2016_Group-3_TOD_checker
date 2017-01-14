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
        self.startButton.clicked.connect(self.showWhatever)
        self.finishButton.clicked.connect(self.stop)
        self.values = []
        self.attributes = []
        self.train = []
        self.bus = []
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
        self.colorList = ['#0101ff', '#01ff01', '#ff0101', '#ffff01', '#ff01ff', '#01ffff', '#7f0101', '#017f01', '#7f017f', '#7f7f01', '#7f7f7f']
        self.tobesorted = []

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
##        for lyr in self.lyrs:
##            if lyr.name() == 'Walking Range':
##                QgsMapLayerRegistry.instance().removeMapLayer(lyr)
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
        r = 1200
        if mapPoint:
            trainLayer = None
            busLayer = None
            self.x = mapPoint.x()
            self.y = mapPoint.y()
            #self.values.append((self.x, self.y))
            self.showCoordinates.append('(' + str(self.x) + ', ' + str(self.y) + ')')
            countTrain = 0
            countBus = 0
            name = self.defineName()
            self.values.append(name)
            for layer in self.layers:
                if 'train_stations' in layer.name():
                    trainLayer = layer
                if 'bus_stops' in layer.name():
                    busLayer = layer
            self.active_layer = self.iface.activeLayer()
            self.layercrs = self.active_layer.crs()
            if trainLayer != None:
                countTrain = self.within_range(self.x, self.y, r, trainLayer)
            if busLayer != None:
                countBus = self.within_range(self.x, self.y, r, busLayer)
            self.train.append(countTrain)
            self.bus.append(countBus)
            #self.attributes.append(self.within_range(x, y, r, self.active_layer))
        self.buffersize = r
        self.outputlayername = name
        #Create the memory layer for the result
        layeruri = 'Polygon?'
        #CRS needs to be specified
        crstext = 'PROJ4:%s' % self.layercrs.toProj4()
        layeruri = layeruri + 'crs=' + crstext
        memresult = QgsVectorLayer(layeruri, self.outputlayername, 'memory')
        outbuffername = 'Walking Distance.shp'
        #bufflayer = QgsVectorLayer(outbuffername, '800m', 'ogr')
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPoint(QgsPoint(self.x, self.y)).buffer(r, 50))
        provider = memresult.dataProvider()
        memresult.startEditing()
        provider.addFeatures([feature])
        memresult.setLayerTransparency(70)
        memresult.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayers([memresult])

    def showWhatever(self):
        point_selected = self.run_mouse()

    def run_mouse(self):
        self.canvas.setMapTool(self.clickTool)

    def stop(self):
        for i in range(len(self.values)):
            self.attributes.append(self.train[i]+self.bus[i]*0.1)
        self.canvas.unsetMapTool(self.clickTool)
        self.showCoordinates.append(str(self.train) + ',' + str(self.bus) + ',' + str(self.attributes) + ',' +str(self.values))
        self.updateTable(self.values, self.attributes)
            #self.clearChart()
##        if len(self.values) == 1:
##            self.plotRadar(self.attributes[0])
##        else:
##            self.plotRadar(self.attributes[0])
##            self.plotRadar(self.attributes[1], 'g')
        if len(self.values) <= 10:
            for i in range(len(self.tobesorted)):
                self.plotRadar(self.tobesorted[i][0], self.colorList[i])
        else:
            for i in range(10):
                self.plotRadar(self.tobesorted[i][0], self.colorList[i])
            for i in range(10, len(self.tobesorted)):
                self.plotRadar(self.tobesorted[i][0], self.colorList[10])
        self.attributes = []
        self.tobesorted = []

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

    def defineName(self):
        msgBox = QtGui.QInputDialog()
        text, ok = msgBox.getText(self, 'Name the Location', 'Please name the location you choose:')
        if ok:
            return text



#######
#    Visualisation functions
#######
    def plotRadar(self, attribute, color = 'b'):
        labels = numpy.array(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
        datalength = 8
        #standard = numpy.array([10]*8)
        data = numpy.array([attribute, 2, 3, 4, 5, 6, 7, 8])
        angles = numpy.linspace(0, 2*numpy.pi, datalength, endpoint = False)
        #standard = numpy.concatenate((standard, [standard[0]]))
        data = numpy.concatenate((data, [data[0]]))
        angles = numpy.concatenate((angles, [angles[0]]))
        #fig = plt.figure()
        self.ax = self.chart_figure.add_subplot(111, polar = True)
        #self.ax.plot(angles, standard, 'r', linewidth = 2)
        #self.ax.fill(angles, standard, 'r', alpha = 0.2)
        self.ax.plot(angles, data, color, linewidth = 2)
        self.ax.fill(angles, data, color, alpha = 0.2)
        self.ax.set_thetagrids(angles*180/numpy.pi, labels)
        self.ax.set_title('TOD\n')
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
        self.tableWidget.setColumnCount(9)
        self.tableWidget.setHorizontalHeaderLabels(['Locations', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
        self.tableWidget.setRowCount(len(values))
        for i in range(len(values)):
            self.tobesorted.append((attributes[i], values[i]))
        self.tobesorted.sort(reverse = True)
        for i in range(len(self.tobesorted)):
            self.tableWidget.setItem(i, 0, QtGui.QTableWidgetItem(unicode(self.tobesorted[i][1])))
            self.tableWidget.setItem(i, 1, QtGui.QTableWidgetItem(unicode(self.tobesorted[i][0])))
        self.tableWidget.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.tableWidget.resizeRowsToContents()

    def clearTable(self):
        self.tableWidget.clear()
