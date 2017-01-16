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
        self.plugin_dir = os.path.dirname(__file__)
        # self.touchTool = QgsMapToolTouch(self.canvas)

        # data
        self.loadRotterdamButton.clicked.connect(self.warningLoadData)
        #self.createScenarioButton.clicked.connect(self.createScenario)
        #self.scenarioCombo.currentIndexChanged.connect(self.scenarioChanged)
        #self.scenarioPath = QgsProject.instance().homePath()
        #self.scenarioCombo.clear()
        #self.scenarioCombo.addItem('Rotterdam')
        #self.scenarioAttributes = {}
        #self.subScenario = {}

        self.layers = self.iface.legendInterface().layers()
        self.layer_list = []
        for layer in self.layers:
            self.layer_list.append(layer.name())

        self.values = []
        self.PtR = []
        self.train = []
        self.bus = []
        self.tobesorted = []
        self.coordinates = []
        self.r1 = 800
        self.r2 = 400
        self.r3 = 200
        
        # set up GUI operation signals

        # canvas
        self.clickTool.canvasClicked.connect(self.yayClicked)
        #self.startButton.clicked.connect(self.showWhatever)
        #self.finishButton.clicked.connect(self.stop)
        self.selectionButton.setCheckable(True)
        self.selectionButton.clicked.connect(self.showWhatever)
        self.clearButton.setCheckable(True)
        self.clearButton.clicked.connect(self.selectRemoved)

        #self.clickTool.canvasClicked.connect(self.handleMouseDown)

        # analysis
        #self.showCoordinates.setReadOnly(True)
        #self.showCoordinates.setFontPointSize(12)
        self.showCoordinates.setSelectionMode(1)
        self.showCoordinates.itemDoubleClicked.connect(self.zoomSelected)

        # visualisation
        self.saveChart.clicked.connect(self.saveChartPNG)

        # reporting
        self.saveTable.clicked.connect(self.saveTableCSV)

        # set current UI restrictions
        
        # add matplotlib Figure to chartFrame
        self.chart_figure = Figure()
        self.chart_canvas = FigureCanvas(self.chart_figure)
        self.legend = QtGui.QListWidget()
        self.chartLayout.addWidget(self.chart_canvas)
        self.chartLayout.addWidget(self.legend)
        self.colorList = ['#0101ff', '#01ff01', '#ff0101', '#ffff01', '#ff01ff', '#7f7f7f']
        self.labelList = ['PtR', 'PuS', 'MoU', 'PeS', 'GfR', 'SC', 'IlS', 'RP']

        # initialisation
        #self.updateLayers()

        #run simple tests
        # add button icons
        self.bigiconButton.setIcon(QtGui.QIcon(self.plugin_dir + '/icons/urban-planners-300x150.jpg'))
        self.bigiconButton.clicked.connect(self.openinBrowser)

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
        self.PtR = []
        self.clearTable()
        self.clearCoordinates()
        self.clearChart()
        event.accept()

    def openinBrowser(self):
        webbrowser.open('https://github.com/TUdent/2016_Group-3_TOD_checker/wiki', new=2)



#######
#   Data functions
#######
    def loadDataRotterdam(self):
        try:
            data_path = os.path.join(os.path.dirname(__file__), 'sample_data','Rotterdam_Sample_Data.qgs')
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
        if mapPoint:
            self.x = mapPoint.x()
            self.y = mapPoint.y()
            self.defineName(self.x, self.y)

    def showWhatever(self):
        if self.selectionButton.isChecked():
            point_selected = self.run_mouse()
        else:
            self.stop()

    def run_mouse(self):
        self.canvas.setMapTool(self.clickTool)

    def stop(self):
        self.legend.clear()
        self.selectionButton.setChecked(False)
        self.clearChart()
        self.publicTransport()
#        for i in range(len(self.values)):
#            self.attributes.append(self.train[i]+self.bus[i]*0.1)
        self.canvas.unsetMapTool(self.clickTool)
        #self.showCoordinates.append(str(self.train) + ',' + str(self.bus) + ',' + str(self.attributes) + ',' +str(self.values))
        self.updateTable(self.values, self.PtR, self.coordinates)
        if len(self.values) <= 5:
            for i in range(len(self.tobesorted)):
                brush = QtGui.QBrush()
                color = QtGui.QColor()
                color.setNamedColor(self.colorList[i])
                brush.setColor(color)
                self.plotRadar(self.tobesorted[i][0], self.colorList[i])
                self.legend.addItem(self.tobesorted[i][1])
                self.legend.item(i).setForeground(brush)
        else:
            for i in range(5):
                brush = QtGui.QBrush()
                color = QtGui.QColor()
                color.setNamedColor(self.colorList[i])
                brush.setColor(color)
                self.plotRadar(self.tobesorted[i][0], self.colorList[i])
                self.legend.addItem(self.tobesorted[i][1])
                self.legend.item(i).setForeground(brush)
            for i in range(5, len(self.tobesorted)):
                self.plotRadar(self.tobesorted[i][0], self.colorList[5])
            brush = QtGui.QBrush()
            color = QtGui.QColor()
            color.setNamedColor(self.colorList[5])
            brush.setColor(color)
            self.legend.addItem('Others')
            self.legend.item(i).setForeground(brush)
            #self.clearChart()
        self.PtR = []
        self.tobesorted = []
        self.showCoordinates.setSelectionMode(1)

    def transportCalculation(self, x, y):
        self.trainLayer = None
        self.busLayer = None
        for layer in self.layers:
            if 'train_stations' in layer.name():
                self.trainLayer = layer
            if 'bus_stops' in layer.name():
                self.busLayer = layer
        if self.trainLayer != None:
            self.countTrain = self.within_range(x, y, self.r1, self.trainLayer)
        if self.busLayer != None:
            self.countBus = self.within_range(x, y, self.r1, self.busLayer)
        self.train.append(self.countTrain)
        self.bus.append(self.countBus)

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

    def defineName(self, x, y):
        msgBox = QtGui.QInputDialog()
        text, ok = msgBox.getText(self, 'Name the Location', 'Please name the location you choose:')
        if ok:
            self.showCoordinates.addItem(text + ': (' + str(x) + ', ' + str(y) + ')')            
            self.coordinates.append((x, y))
            self.countTrain = 0
            self.countBus = 0
            self.values.append(text)
            self.transportCalculation(x, y)
            self.addLayer(x, y, text)

    def addLayer(self, x, y, text):
        self.active_layer = self.iface.activeLayer()
        if self.active_layer != None:
            self.layercrs = self.active_layer.crs()
        else:
            self.layercrs = self.layers[0].crs()
        self.buffersize = self.r1
        self.outputlayername = text
        #Create the memory layer for the result
        layeruri = 'Polygon?'
        #CRS needs to be specified
        crstext = 'PROJ4:%s' % self.layercrs.toProj4()
        layeruri = layeruri + 'crs=' + crstext
        memresult = QgsVectorLayer(layeruri, self.outputlayername, 'memory')
        outbuffername = 'Walking Distance.shp'
        #bufflayer = QgsVectorLayer(outbuffername, '800m', 'ogr')
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPoint(QgsPoint(x, y)).buffer(self.r1, 50))
        provider = memresult.dataProvider()
        memresult.startEditing()
        provider.addFeatures([feature])
        memresult.setLayerTransparency(70)
        memresult.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayers([memresult])

    def addFeature(self, x, y, text):
        pass

    def zoomSelected(self):
        if self.selectionButton.isChecked():
            self.stop()
        tobezoomed = self.showCoordinates.selectedItems()
        name = tobezoomed[0].text().split(':')[0]
        current_layers = self.iface.legendInterface().layers()
        for layer in current_layers:
            if layer.name() == name:
                layer.select(1)
                self.iface.setActiveLayer(layer)
                self.canvas.zoomToSelected()
                layer.deselect(1)
                

    def selectRemoved(self):
        if self.selectionButton.isChecked():
            self.clearButton.setChecked(False)
        else:
            if self.clearButton.isChecked():
                self.showCoordinates.setSelectionMode(3)
            else:
                self.removeSelected()
            #self.showItemTest()
            #self.showCoordinates.itemClicked.connect(self.showItemTest)
        #else:

    def removeSelected(self):
        self.current_layers = self.iface.legendInterface().layers()
        toberemoved = self.showCoordinates.selectedItems()
        toberemoved_list = []
        self.PtR = []
        self.tobesorted = []
        for item in toberemoved:
            toberemoved_list.append(item.text().split(':')[0])
            item.setHidden(True)
        for layer in self.current_layers:
            if layer.name() in toberemoved_list:
                QgsMapLayerRegistry.instance().removeMapLayer(layer)
        for i in toberemoved_list:
            if i in self.values:
                row = self.values.index(i)
                del self.values[row]
                del self.train[row]
                del self.bus[row]
                del self.coordinates[row]
        self.stop()

    def publicTransport(self):
        for i in range(len(self.values)):
            if len(self.values) <= 80:
                self.PtR.append(self.train[i]+self.bus[i]*0.1)
            else:
                self.PtR.append(self.train[i]+8)

#    def showItemTest(self):
#        self.showCoordinates.addItem(str(self.showCoordinates.currentRow()))


#######
#    Visualisation functions
#######
    def plotRadar(self, PtR, color = 'b'):
        labels = numpy.array(self.labelList)
        datalength = 8
        #standard = numpy.array([10]*8)
        data = numpy.array([PtR, 2, 3, 4, 5, 6, 7, 8])
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
        #self.ax.legend(name)
        #self.ax.grid = True
        self.chart_canvas.draw()
##            else:
##                self.clearChart()

    def saveChartPNG(self):
        path = QtGui.QFileDialog.getSaveFileName(self, 'Save Chart', 'Result', '.png')
        self.pixmap = QtGui.QPixmap()
        self.saved_legend = self.pixmap.grabWidget(self.legend)
        if path:
            self.chart_figure.savefig(path)
            path_legend = QtGui.QFileDialog.getSaveFileName(self, 'Save Legend', 'Result Legend', '.png')
            #if the chart is not saved, don't even bother saving the legend
            if path_legend:
                self.saved_legend.save(path_legend, 'png')

    def clearChart(self):
        #self.ax.grid = False
        self.chart_figure.clear()
        self.chart_canvas.draw()



#######
#    Reporting functions
#######
    # table window functions
    def updateTable(self, values, PtR, coordinates):
        self.tableWidget.setColumnCount(10)
        self.tableWidget.setHorizontalHeaderLabels(['Locations'] + self.labelList + ['Coordinates'])
        self.tableWidget.setRowCount(len(values))
        for i in range(len(values)):
            self.tobesorted.append((PtR[i], values[i], coordinates[i]))
        self.tobesorted.sort(reverse = True)
        for i in range(len(self.tobesorted)):
            self.tableWidget.setItem(i, 0, QtGui.QTableWidgetItem(unicode(self.tobesorted[i][1])))
            self.tableWidget.setItem(i, 1, QtGui.QTableWidgetItem(unicode(self.tobesorted[i][0])))
            self.tableWidget.setItem(i, 9, QtGui.QTableWidgetItem(unicode(self.tobesorted[i][2])))
        self.tableWidget.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.tableWidget.resizeRowsToContents()

    def saveTableCSV(self):
        path = QtGui.QFileDialog.getSaveFileName(self, 'Save File', 'Result', 'CSV(*.csv)')
        if path:
            with open(unicode(path), 'wb') as stream:
                # open csv file for writing
                writer = csv.writer(stream)
                # write header
                header = []
                for column in range(self.tableWidget.columnCount()):
                    item = self.tableWidget.horizontalHeaderItem(column)
                    header.append(unicode(item.text()).encode('utf8'))
#                header.append(unicode('Coordinates').encode('utf8'))
                writer.writerow(header)
                # write data
                for row in range(self.tableWidget.rowCount()):
                    rowdata = []
                    for column in range(self.tableWidget.columnCount()):
                        item = self.tableWidget.item(row, column)
                        if item is not None:
                            rowdata.append(
                                unicode(item.text()).encode('utf8'))
                        else:
                            rowdata.append('')
                    writer.writerow(rowdata)

    def clearTable(self):
        self.tableWidget.clear()
