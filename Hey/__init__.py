# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SpatialDecision
                                 A QGIS plugin
 test
                             -------------------
        begin                : 2016-12-13
        copyright            : (C) 2016 by unknown
        email                : unknown
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SpatialDecision class from file SpatialDecision.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .spatial_decision import SpatialDecision
    return SpatialDecision(iface)
