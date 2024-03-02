import imp
import time
from collections import defaultdict

import qgis.processing as processing
from qgis import *
from qgis.core import *
from qgis.PyQt.QtCore import *

import vars_settings

imp.reload(vars_settings)
import helper_functions

imp.reload(helper_functions)

def step_02(
    layer,
    id_offset_cycleway_left,
    id_offset_cycleway_right,
    id_offset_sidewalk_left,
    id_offset_sidewalk_right,
    id_offset,
    id_type,
    id_side,
    id_proc_sidepath,
    id_proc_highway,
    id_proc_maxspeed,
):
    """
    2: Split and shift attributes/geometries for sidepath mapped on the centerline
    """

    print(time.strftime('%H:%M:%S', time.localtime()), 'Split line bundles...')
    offset_layer_dict = defaultdict(lambda: defaultdict(dict))
    with edit(layer):
        for feature in layer.getFeatures():
            highway = feature.attribute('highway')
            cycleway = feature.attribute('cycleway')
            cycleway_both = feature.attribute('cycleway:both')
            cycleway_left = feature.attribute('cycleway:left')
            cycleway_right = feature.attribute('cycleway:right')
            sidewalk_bicycle = feature.attribute('sidewalk:bicycle')
            sidewalk_both_bicycle = feature.attribute('sidewalk:both:bicycle')
            sidewalk_left_bicycle = feature.attribute('sidewalk:left:bicycle')
            sidewalk_right_bicycle = feature.attribute('sidewalk:right:bicycle')

            offset_cycleway_left = offset_cycleway_right = offset_sidewalk_left = offset_sidewalk_right = 0
            side = NULL

            #TODO: more precise offset calculation taking "parking:", "placement", "width:lanes" and other Tags into account
            if vars_settings.offset_distance == 'realistic':
                #use road width as offset for the new geometry
                width = helper_functions.getNumber(feature.attribute('width'))

                #use default road width if width isn't specified
                if not width:
                    width = vars_settings.default_highway_width_dict[highway]

            #offset for cycleways
            if highway != 'cycleway':
                #offset for left cycleways
                if cycleway in ['lane', 'track', 'share_busway'] or cycleway_both in ['lane', 'track', 'share_busway'] or cycleway_left in ['lane', 'track', 'share_busway']:
                    #option 1: offset of sidepath lines according to real distances on the ground
                    if vars_settings.offset_distance == 'realistic':
                        offset_cycleway_left = width / 2
                    #option 2: static offset as defined in the variable
                    else:
                        offset_cycleway_left = helper_functions.getNumber(vars_settings.offset_distance)
                    layer.changeAttributeValue(feature.id(), id_offset_cycleway_left, offset_cycleway_left)

                #offset for right cycleways
                if cycleway in ['lane', 'track', 'share_busway'] or cycleway_both in ['lane', 'track', 'share_busway'] or cycleway_right in ['lane', 'track', 'share_busway']:
                    if vars_settings.offset_distance == 'realistic':
                        offset_cycleway_right = width / 2
                    else:
                        offset_cycleway_right = helper_functions.getNumber(vars_settings.offset_distance)
                    layer.changeAttributeValue(feature.id(), id_offset_cycleway_right, offset_cycleway_right)

            #offset for shared footways
            #offset for left sidewalks
            if sidewalk_bicycle in ['yes', 'designated', 'permissive'] or sidewalk_both_bicycle in ['yes', 'designated', 'permissive'] or sidewalk_left_bicycle in ['yes', 'designated', 'permissive']:
                if vars_settings.offset_distance == 'realistic':
                    #use larger offset than for cycleways to get nearby, parallel lines in case both (cycleway and sidewalk) exist
                    offset_sidewalk_left = width / 2 + 2
                else:
                    #TODO: double offset if cycleway exists on same side
                    offset_sidewalk_left = helper_functions.getNumber(vars_settings.offset_distance)
                layer.changeAttributeValue(feature.id(), id_offset_sidewalk_left, offset_sidewalk_left)

            #offset for right sidewalks
            if sidewalk_bicycle in ['yes', 'designated', 'permissive'] or sidewalk_both_bicycle in ['yes', 'designated', 'permissive'] or sidewalk_right_bicycle in ['yes', 'designated', 'permissive']:
                if vars_settings.offset_distance == 'realistic':
                    offset_sidewalk_right = width / 2 + 2
                else:
                    offset_sidewalk_right = helper_functions.getNumber(vars_settings.offset_distance)
                layer.changeAttributeValue(feature.id(), id_offset_sidewalk_right, offset_sidewalk_right)

        processing.run('qgis:selectbyexpression', {'INPUT' : layer, 'EXPRESSION' : '\"offset_cycleway_left\" IS NOT NULL'})
        offset_layer_dict["cycleway"]["left"] = processing.run('native:offsetline', {'INPUT': QgsProcessingFeatureSourceDefinition(layer.id(), selectedFeaturesOnly=True), 'DISTANCE': QgsProperty.fromExpression('"offset_cycleway_left"'), 'OUTPUT': 'memory:'})['OUTPUT']
        processing.run('qgis:selectbyexpression', {'INPUT' : layer, 'EXPRESSION' : '\"offset_cycleway_right\" IS NOT NULL'})
        offset_layer_dict["cycleway"]["right"] = processing.run('native:offsetline', {'INPUT': QgsProcessingFeatureSourceDefinition(layer.id(), selectedFeaturesOnly=True), 'DISTANCE': QgsProperty.fromExpression('-"offset_cycleway_right"'), 'OUTPUT': 'memory:'})['OUTPUT']
        processing.run('qgis:selectbyexpression', {'INPUT' : layer, 'EXPRESSION' : '\"offset_sidewalk_left\" IS NOT NULL'})
        offset_layer_dict["sidewalk"]["left"] = processing.run('native:offsetline', {'INPUT': QgsProcessingFeatureSourceDefinition(layer.id(), selectedFeaturesOnly=True), 'DISTANCE': QgsProperty.fromExpression('"offset_sidewalk_left"'), 'OUTPUT': 'memory:'})['OUTPUT']
        processing.run('qgis:selectbyexpression', {'INPUT' : layer, 'EXPRESSION' : '\"offset_sidewalk_right\" IS NOT NULL'})
        offset_layer_dict["sidewalk"]["right"] = processing.run('native:offsetline', {'INPUT': QgsProcessingFeatureSourceDefinition(layer.id(), selectedFeaturesOnly=True), 'DISTANCE': QgsProperty.fromExpression('-"offset_sidewalk_right"'), 'OUTPUT': 'memory:'})['OUTPUT']

        #TODO: offset als Attribut überschreiben
        #eigenständige Attribute ableiten

        layer.updateFields()

    #derive attributes for offset ways
    for side in ['left', 'right']:
        for way_type in ['cycleway', 'sidewalk']:
            offset_layer = offset_layer_dict[way_type][side]
            with edit(offset_layer):
                for feature in offset_layer.getFeatures():
                    offset_layer.changeAttributeValue(feature.id(), id_offset, feature.attribute('offset_' + way_type + '_' + side))
                    offset_layer.changeAttributeValue(feature.id(), id_type, way_type)
                    offset_layer.changeAttributeValue(feature.id(), id_side, side)
                    #this offset geometries are sidepath
                    offset_layer.changeAttributeValue(feature.id(), id_proc_sidepath, 'yes')
                    offset_layer.changeAttributeValue(feature.id(), id_proc_highway, feature.attribute('highway'))
                    offset_layer.changeAttributeValue(feature.id(), id_proc_maxspeed, feature.attribute('maxspeed'))

                    offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('width'), helper_functions.deriveAttribute(feature, 'width', way_type, side, 'float'))
                    offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('oneway'), helper_functions.deriveAttribute(feature, 'oneway', way_type, side, 'str'))
                    offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('oneway:bicycle'), helper_functions.deriveAttribute(feature, 'oneway:bicycle', way_type, side, 'str'))
                    offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('traffic_sign'), helper_functions.deriveAttribute(feature, 'traffic_sign', way_type, side, 'str'))

                    #surface and smoothness of cycle lanes are usually the same as on the road (if not explicitly tagged)
                    if way_type != 'cycleway' or (way_type == 'cycleway' and ((feature.attribute('cycleway:' + side) == 'track' or feature.attribute('cycleway:both') == 'track' or feature.attribute('cycleway') == 'track') or feature.attribute(way_type + ':' + side + ':surface') != NULL or feature.attribute(way_type + ':both:surface') != NULL or feature.attribute(way_type + ':surface') != NULL)):
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('surface'), helper_functions.deriveAttribute(feature, 'surface', way_type, side, 'str'))
                    if way_type != 'cycleway' or (way_type == 'cycleway' and ((feature.attribute('cycleway:' + side) == 'track' or feature.attribute('cycleway:both') == 'track' or feature.attribute('cycleway') == 'track') or feature.attribute(way_type + ':' + side + ':smoothness') != NULL or feature.attribute(way_type + ':both:smoothness') != NULL or feature.attribute(way_type + ':smoothness') != NULL)):
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('smoothness'), helper_functions.deriveAttribute(feature, 'smoothness', way_type, side, 'str'))

                    if way_type == 'cycleway':
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('separation'), helper_functions.deriveAttribute(feature, 'separation', way_type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('separation:both'), helper_functions.deriveAttribute(feature, 'separation:both', way_type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('separation:left'), helper_functions.deriveAttribute(feature, 'separation:left', way_type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('separation:right'), helper_functions.deriveAttribute(feature, 'separation:right', way_type, side, 'str'))

                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('buffer'), helper_functions.deriveAttribute(feature, 'buffer', way_type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('buffer:both'), helper_functions.deriveAttribute(feature, 'buffer:both', way_type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('buffer:left'), helper_functions.deriveAttribute(feature, 'buffer:left', way_type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('buffer:right'), helper_functions.deriveAttribute(feature, 'buffer:right', way_type, side, 'str'))

                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('traffic_mode:both'), helper_functions.deriveAttribute(feature, 'traffic_mode:both', way_type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('traffic_mode:left'), helper_functions.deriveAttribute(feature, 'traffic_mode:left', way_type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('traffic_mode:right'), helper_functions.deriveAttribute(feature, 'traffic_mode:right', way_type, side, 'str'))

                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('surface:colour'), helper_functions.deriveAttribute(feature, 'surface:colour', way_type, side, 'str'))

    #TODO: Attribute mit "both" auf left und right aufteilen?

    #TODO: clean up offset layers

    #merge vanilla and offset layers
    layer = processing.run(
        'native:mergevectorlayers',
        {
            'LAYERS': [
                layer,
                offset_layer_dict["cycleway"]["left"],
                offset_layer_dict["cycleway"]["right"],
                offset_layer_dict["sidewalk"]["left"],
                offset_layer_dict["sidewalk"]["right"],
            ],
            'OUTPUT': 'memory:'
        }
    )['OUTPUT']
