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

# Initialize Qt resources from file resources.py
import resources

import processing
import os
import os.path
import random
import webbrowser
import csv

from . import utility_functions as uf

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

        self.layers = self.iface.legendInterface().layers()
        self.layer_list = []
        for layer in self.layers:
            self.layer_list.append(layer.name())

        self.active_layer = self.iface.activeLayer()
        self.layercrs = layer.crs()

        # set up GUI operation signals

        # canvas
        self.clickTool.canvasClicked.connect(self.yayClicked)
        self.startButton.clicked.connect(self.showShow)
        self.finishButton.clicked.connect(self.stop)
        self.values = []
        #self.clickTool.canvasClicked.connect(self.handleMouseDown)
        
        # data
        self.loadRotterdamButton.clicked.connect(self.warningLoadData)
        #self.createScenarioButton.clicked.connect(self.createScenario)
        #self.scenarioCombo.currentIndexChanged.connect(self.scenarioChanged)
        self.scenarioPath = QgsProject.instance().homePath()
        self.scenarioCombo.clear()
        self.scenarioCombo.addItem('Rotterdam')
        self.scenarioAttributes = {}
        self.subScenario = {}

        # analysis
        self.showCoordinates.setReadOnly(True)
        self.showCoordinates.setFontPointSize(12)

        # visualisation
        #self.displayStyleButton.clicked.connect(self.displayBenchmarkStyle)
        #self.displayRangeButton.clicked.connect(self.displayContinuousStyle)
        #self.updateAttribute.connect(self.plotRadar)
        #self.plotRadar()

        # reporting
        #self.tableView.itemClicked.connect(self.selectFeatureTable)
        #self.statistics2Table.itemClicked.connect(self.selectFeatureTable)
        #self.saveStatisticsButton.clicked.connect(self.saveTable)
        self.neighborhood = ('',False)

        # set current UI restrictions
        
        # add matplotlib Figure to chartFrame
        self.chart_figure = Figure()
        #self.chart_subplot_radar = self.chart_figure.add_subplot(111)
        #self.chart_figure.tight_layout()
        self.chart_canvas = FigureCanvas(self.chart_figure)
        self.chartLayout.addWidget(self.chart_canvas)
        self.plotRadar()

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
            self.canvas.unsetMapTool(self.clickTool)
        except:
            pass

        self.closingPlugin.emit()
        self.canvas.unsetMapTool(self.clickTool)
        event.accept()



#######
#   Data functions
#######
    def getScenarios(self):
        scenarios = [self.scenarioCombo.itemText(i) for i in range(self.scenarioCombo.count())]
        return scenarios

    def updateNodeNetworkScenario(self):
        layers = uf.getLegendLayers(self.iface, 'all', 'all')
        network_text = self.selectNetworkCombo.currentText()
        if network_text == '':
            network_text = 'Road network'
        node_text = self.selectNodeCombo.currentText()
        if node_text == '':
            node_text = 'Nodes'
        self.selectNetworkCombo.clear()
        self.selectNodeCombo.clear()
        if layers:
            layer_names = uf.getLayersListNames(layers)
            self.selectNetworkCombo.addItems(layer_names)
            self.selectNodeCombo.addItems(layer_names)
            if layer_names.__contains__(network_text):
                index = self.selectNetworkCombo.findText(network_text)
                self.selectNetworkCombo.setCurrentIndex(index);
            if layer_names.__contains__(node_text):
                index = self.selectNodeCombo.findText(node_text)
                self.selectNodeCombo.setCurrentIndex(index);

        # remove scenario if deleted
        scenarios = self.getScenarios()
        current_scenario = self.scenarioCombo.currentText()
        self.scenarioCombo.clear()
        index = 0
        for scenario in scenarios:
            root = QgsProject.instance().layerTreeRoot()
            scenario_group = root.findGroup(scenario)
            if scenario_group or scenario == 'Rotterdam':
                self.scenarioCombo.addItem(scenario)
                if scenario == current_scenario:
                    self.scenarioCombo.setCurrentIndex(index)
                index = index + 1
            else:
                self.scenarioAttributes.pop(scenario, None)
                # send this to the table
                self.clearTable()
                self.updateTable1()
                self.updateTable2()

    def getNetworkLayer(self):
        layer_name = self.selectNetworkCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer

    def getBaseNodeLayer(self):
        layer_name = self.selectNodeCombo.currentText()
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer

    def getCurrentNodeLayer(self):
        layer_name = self.scenarioCombo.currentText() + '_nodes'
        layer = uf.getLegendLayerByName(self.iface,layer_name)

        if layer == None:
            layer_name = 'Nodes'
            layer = uf.getLegendLayerByName(self.iface,layer_name)
        return layer

    def loadDataRotterdam(self):
        try:
            data_path = os.path.join(os.path.dirname(__file__), 'sample_data','LayerRotterdam.qgs')
        except:
            self.createScenario()
        self.iface.addProject(data_path)

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


#######
#    Analysis functions
#######

    def yayClicked(self, mapPoint, mouseButton):
        if mapPoint:
            r = 800
            x = mapPoint.x()
            y = mapPoint.y()
            self.showCoordinates.append('(' + str(x) + ', ' + str(y) + ')')
            self.values.append((x, y))
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
        self.updateTable(self.values)
        
    # route functions
    def getNetwork(self):
        roads_layer = self.getSelectedLayer()
        if roads_layer:
##            # see if there is an obstacles layer to subtract roads from the network
##            obstacles_layer = uf.getLegendLayerByName(self.iface, "Obstacles")
##            if obstacles_layer:
##                # retrieve roads outside obstacles (inside = False)
##                features = uf.getFeaturesByIntersection(roads_layer, obstacles_layer, False)
##                # add these roads to a new temporary layer
##                road_network = uf.createTempLayer('Temp_Network','LINESTRING',roads_layer.crs().postgisSrid(),[],[])
##                road_network.dataProvider().addFeatures(features)
##            else:
##                road_network = roads_layer
##            return road_network
            return roads_layer
        else:
            return

##    def buildNetwork(self):
##        self.network_layer = self.getNetwork()
##        if self.network_layer:
##            # get the points to be used as origin and destination
##            # in this case gets the centroid of the selected features
##            selected_sources = self.getSelectedLayer().selectedFeatures()
##            source_points = [feature.geometry().centroid().asPoint() for feature in selected_sources]
##            # build the graph including these points
##            if len(source_points) > 1:
##                self.graph, self.tied_points = uf.makeUndirectedGraph(self.network_layer, source_points)
##                # the tied points are the new source_points on the graph
##                if self.graph and self.tied_points:
##                    text = "network is built for %s points" % len(self.tied_points)
##                    self.insertReport(text)
##        return

    def calculateRoute(self):
        # origin and destination must be in the set of tied_points
        options = len(self.tied_points)
        if options > 1:
            # origin and destination are given as an index in the tied_points list
            origin = 0
            destination = random.randint(1,options-1)
            # calculate the shortest path for the given origin and destination
            path = uf.calculateRouteDijkstra(self.graph, self.tied_points, origin, destination)
            # store the route results in temporary layer called "Routes"
            routes_layer = uf.getLegendLayerByName(self.iface, "Routes")
            # create one if it doesn't exist
            if not routes_layer:
                attribs = ['id']
                types = [QtCore.QVariant.String]
                routes_layer = uf.createTempLayer('Routes','LINESTRING',self.network_layer.crs().postgisSrid(), attribs, types)
                uf.loadTempLayer(routes_layer)
            # insert route line
            for route in routes_layer.getFeatures():
                print route.id()
            uf.insertTempFeatures(routes_layer, [path], [['testing',100.00]])
            buffer = processing.runandload('qgis:fixeddistancebuffer',routes_layer,10.0,5,False,None)
            #self.refreshCanvas(routes_layer)

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
    def plotRadar(self):
##        plot_layer = self.getSelectedLayer()
##        if plot_layer:
##            attribute = self.getSelectedAttribute()
##            if attribute:
##        numeric_fields = uf.getNumericFieldNames(plot_layer)
        labels = numpy.array(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'])
        #self.chart_figure.cla()
        datalength = 8
        standard = numpy.array([10]*8)
        data = numpy.array([1, 2, 3, 4, 5, 6, 7, 8])
        angles = numpy.linspace(0, 2*numpy.pi, datalength, endpoint = False)
        standard = numpy.concatenate((standard, [standard[0]]))
        data = numpy.concatenate((data, [data[0]]))
        angles = numpy.concatenate((angles, [angles[0]]))
        #fig = plt.figure()
        ax = self.chart_figure.add_subplot(111, polar = True)
        ax.plot(angles, standard, 'r', linewidth = 2)
        ax.fill(angles, standard, 'r', alpha = 0.2)
        ax.plot(angles, data, 'bo-', linewidth = 2)
        ax.fill(angles, data, 'b', alpha = 0.2)
        ax.set_thetagrids(angles*180/numpy.pi, labels)
        ax.set_title('TOD')
        ax.grid = True
        self.chart_canvas.draw()
##            else:
##                self.clearChart()

    def clearChart(self):
        self.chart_figure.cla()
        self.chart_canvas.draw()



#######
#    Reporting functions
#######
##        # run SAGA processing algorithm
##        processing.runalg("saga:gridstatisticsforpolygons",pathGrid, neigh, False, False, True, False, False, True, False, False, 0, pathStat)
##        polyStat = QgsVectorLayer(pathStat, layer_name, 'ogr')
##        QgsMapLayerRegistry.instance().addMapLayer(polyStat, False)
##        root = QgsProject.instance().layerTreeRoot()
##        scenario_group = root.findGroup(current_scenario)
##        scenario_group.insertLayer(2, polyStat)
##        legend = self.iface.legendInterface()
##        legend.setLayerVisible(polyStat, False)
##
##        layer = QgsMapCanvasLayer(polyStat)
##        layer.setVisible(False)
##
##        # get statistics in table
##        self.extractAttributeSummary(layer_name, current_scenario)

    def extractAttributeSummary(self, layer_name, scenario):
        # get summary of the attribute
        layer = uf.getLegendLayerByName(self.iface,layer_name)
        summary = []
        # only use the first attribute in the list
        for feature in layer.getFeatures():
            summary.append(feature)#, feature.attribute(attribute)))

        self.scenarioAttributes[scenario] = summary
        # send this to the table
        self.clearTable()
        self.updateTable()

    # table window functions
    def updateTable(self, values):
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(['Coordinates', 'Ehh...'])
        self.tableWidget.setRowCount(len(values))
        for i in range(len(values)):
            self.tableWidget.setItem(i, 0, QtGui.QTableWidgetItem(unicode(values[i])))
            self.tableWidget.setItem(i, 1, QtGui.QTableWidgetItem(unicode(i+1)))
        self.tableWidget.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        self.tableWidget.horizontalHeader().setResizeMode(1, QtGui.QHeaderView.Stretch)
        self.tableWidget.resizeRowsToContents()

    def clearTable(self):
        self.tableWidget.clear()

#    def openinBrowser(self):
#        webbrowser.open('https://github.com/SimonGriffioen/pascal/wiki', new=2)

    def selectFeatureTable(self, item):
        if item.row() == self.neighborhood[0] and self.neighborhood[1] is True:
            for a in self.iface.attributesToolBar().actions():
                if a.objectName() == 'mActionDeselectAll':
                    a.trigger()
                    break
            self.neighborhood = (item.row(),False)
            return
        neighborhood = item.text()
        print item.row()
        print item.column()
        layer = uf.getLegendLayerByName(self.iface, "Neighborhoods")
        fids = [item.row()]
        request = QgsFeatureRequest().setFilterFids(fids)
        it = layer.getFeatures( request )
        ids = [i.id() for i in it]
        layer.setSelectedFeatures(ids)

        # zoom to feature
        self.canvas.zoomToSelected(layer)
        # deselect feature
        self.neighborhood = (item.row(),True)

