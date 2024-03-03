import imp
import time
from collections import defaultdict
from typing import DefaultDict, Dict, TypedDict, Union

import qgis.processing as processing  # type: ignore
from qgis.core import (  # type: ignore
    NULL, QgsFeature, QgsProcessingFeatureSourceDefinition, QgsProject,
    QgsVectorLayer, edit
)
from qgis.PyQt.QtCore import QVariant  # type: ignore

import helper_functions
import vars_settings

imp.reload(vars_settings)
imp.reload(helper_functions)


def step_01(
    layer: QgsVectorLayer,
    id_proc_highway: int,
    id_proc_maxspeed: int,
    id_proc_sidepath: int,
) -> None:
    """
    Check paths whether they are sidepath (a path along a road)
    """
    sidepath_buffer_size = 22  # check for adjacent roads for ... meters around a way
    sidepath_buffer_distance = 100  # do checks for adjacent roads every ... meters along a way

    print(time.strftime('%H:%M:%S', time.localtime()), 'Sidepath check...')
    print(time.strftime('%H:%M:%S', time.localtime()), '   Create way layers...')
    # create path layer: check all path, footways or cycleways for their sidepath status
    layer_path = processing.run(
        'qgis:extractbyexpression',
        {
            'INPUT': layer,
            'EXPRESSION': """"highway" IS 'cycleway' OR "highway" IS 'footway' OR "highway" IS 'path' OR "highway" IS 'bridleway' OR "highway" IS 'steps'""",
            'OUTPUT': 'memory:'
        }
    )['OUTPUT']
    # create road layer: extract all other highway types (except tracks)
    layer_roads: QgsVectorLayer = processing.run(
        'qgis:extractbyexpression',
        {
            'INPUT': layer,
            'EXPRESSION': """"highway" IS NOT 'cycleway' AND "highway" IS NOT 'footway' AND "highway" IS NOT 'path' AND "highway" IS NOT 'bridleway' AND "highway" IS NOT 'steps' AND "highway" IS NOT 'track'""",
            'OUTPUT': 'memory:'
        }
    )['OUTPUT']
    print(time.strftime('%H:%M:%S', time.localtime()), '   Create check points...')

    # create "check points" along each segment (to check for near/parallel highways at every checkpoint)
    layer_path_points = processing.run(
        'native:pointsalonglines',
        {
            'INPUT': layer_path,
            'DISTANCE': sidepath_buffer_distance,
            'OUTPUT': 'memory:'
        }
    )['OUTPUT']
    layer_path_points_endpoints = processing.run(
        'native:extractspecificvertices',
        {
            'INPUT': layer_path,
            'VERTICES': '-1',
            'OUTPUT': 'memory:'
        }
    )['OUTPUT']
    layer_path_points = processing.run(
        'native:mergevectorlayers',
        {
            'LAYERS': [layer_path_points, layer_path_points_endpoints],
            'OUTPUT': 'memory:'
        }
    )['OUTPUT']

    # create "check buffers" (to check for near/parallel highways with in the given distance)
    layer_path_points_buffers: QgsVectorLayer = processing.run(
        'native:buffer',
        {
            'INPUT': layer_path_points,
            'DISTANCE': sidepath_buffer_size,
            'OUTPUT': 'memory:'
        }
    )['OUTPUT']
    QgsProject.instance().addMapLayer(layer_path_points_buffers, False)

    print(time.strftime('%H:%M:%S', time.localtime()), '   Check for adjacent roads...')

    # for all check points: Save nearby road id's, names and highway classes in a dict
    class typed_dict_of_int_or_defaultdict_of_int_or_float(TypedDict):
        checks: int
        id: DefaultDict[QVariant, int]
        highway: DefaultDict[QVariant, int]
        name: DefaultDict[QVariant, int]
        maxspeed: DefaultDict[QVariant, float]

        # Dict[str, Union[int, DefaultDict[QVariant, Union[int, float]]]]

    sidepath_dict: Dict[QVariant, typed_dict_of_int_or_defaultdict_of_int_or_float] = {}
    for buffer in layer_path_points_buffers.getFeatures():
        buffer_id: QVariant = buffer.attribute('id')
        if buffer_id not in sidepath_dict:
            sidepath_dict[buffer_id] = {
                'checks': 1,
                'id': defaultdict(lambda: 1),
                'highway': defaultdict(lambda: 1),
                'name': defaultdict(lambda: 1),
                'maxspeed': defaultdict(lambda: -1.0),
            }
        else:
            sidepath_dict[buffer_id]['checks'] += 1  # type: ignore
        layer_path_points_buffers.removeSelection()
        layer_path_points_buffers.select(buffer.id())
        processing.run(
            'native:selectbylocation',
            {
                'INPUT': layer_roads,
                'INTERSECT': QgsProcessingFeatureSourceDefinition(layer_path_points_buffers.id(), selectedFeaturesOnly=True),
                'METHOD': 0,
                'PREDICATE': [0, 6]
            }
        )

        id_list = []
        highway_list = []
        name_list = []
        maxspeed_dict: Dict[QVariant, Union[QVariant, float]] = {}
        road: QgsFeature
        for road in layer_roads.selectedFeatures():
            if buffer.attribute('layer') != road.attribute('layer'):
                # only consider geometries in the same layer
                continue

            road_id: QVariant = road.attribute('id')
            road_highway: QVariant = road.attribute('highway')
            road_name: QVariant = road.attribute('name')
            road_maxspeed = helper_functions.cast_to_float(road.attribute('maxspeed'))  # TODO: check if road actually has the attribute maxspeed?!

            if road_id not in id_list:
                id_list.append(road_id)
            if road_highway not in highway_list:
                highway_list.append(road_highway)
            if road_highway not in maxspeed_dict or maxspeed_dict[road_highway] < road_maxspeed:
                maxspeed_dict[road_highway] = road_maxspeed
            if road_name not in name_list:
                name_list.append(road_name)

        for road_id in id_list:
            sidepath_dict[buffer_id]['id'][road_id] += 1

        for road_highway in highway_list:
            sidepath_dict[buffer_id]['highway'][road_highway] += 1

        for road_name in name_list:
            sidepath_dict[buffer_id]['name'][road_name] += 1

        for highway in maxspeed_dict.keys():
            if highway not in sidepath_dict[buffer_id]['maxspeed'] or sidepath_dict[buffer_id]['maxspeed'][highway] < maxspeed_dict[highway]:
                sidepath_dict[buffer_id]['maxspeed'][highway] = maxspeed_dict[highway]

    highway_class_list = ['motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link', 'unclassified', 'residential', 'road', 'living_street', 'service', 'pedestrian', NULL]

    # a path is considered a sidepath if at least two thirds of its check points are found to be close to road segments with the same OSM ID, highway class or street name
    with edit(layer):
        for feature in layer.getFeatures():
            hw = feature.attribute('highway')
            maxspeed: QVariant = feature.attribute('maxspeed')
            if maxspeed == 'walk':
                maxspeed = 10
            else:
                maxspeed = helper_functions.cast_to_float(maxspeed)
            if hw not in ['cycleway', 'footway', 'path', 'bridleway', 'steps']:
                layer.changeAttributeValue(feature.id(), id_proc_highway, hw)
                layer.changeAttributeValue(feature.id(), id_proc_maxspeed, maxspeed)
                continue
            id = feature.attribute('id')
            is_sidepath: QVariant = feature.attribute('is_sidepath')
            if feature.attribute('footway') == 'sidewalk':
                is_sidepath = 'yes'
            is_sidepath_of: QVariant = feature.attribute('is_sidepath:of')
            checks = sidepath_dict[id]['checks']

            if not is_sidepath:
                is_sidepath = 'no'

                for road_id in sidepath_dict[id]['id'].keys():
                    if checks <= 2:
                        if sidepath_dict[id]['id'][road_id] == checks:
                            is_sidepath = 'yes'
                    else:
                        if sidepath_dict[id]['id'][road_id] >= checks * 0.66:
                            is_sidepath = 'yes'

                if is_sidepath != 'yes':
                    for highway in sidepath_dict[id]['highway'].keys():
                        if checks <= 2:
                            if sidepath_dict[id]['highway'][highway] == checks:
                                is_sidepath = 'yes'
                        else:
                            if sidepath_dict[id]['highway'][highway] >= checks * 0.66:
                                is_sidepath = 'yes'

                if is_sidepath != 'yes':
                    for name in sidepath_dict[id]['name'].keys():
                        if checks <= 2:
                            if sidepath_dict[id]['name'][name] == checks:
                                is_sidepath = 'yes'
                        else:
                            if sidepath_dict[id]['name'][name] >= checks * 0.66:
                                is_sidepath = 'yes'

            layer.changeAttributeValue(feature.id(), id_proc_sidepath, is_sidepath)

            # derive the highway class of the associated road
            if not is_sidepath_of and is_sidepath == 'yes':
                if len(sidepath_dict[id]['highway']):
                    max_value = max(sidepath_dict[id]['highway'].values())
                    max_keys = [key for key, value in sidepath_dict[id]['highway'].items() if value == max_value]
                    min_index = len(highway_class_list) - 1
                    for key in max_keys:
                        if highway_class_list.index(key) < min_index:
                            min_index = highway_class_list.index(key)
                    is_sidepath_of = highway_class_list[min_index]

            layer.changeAttributeValue(feature.id(), id_proc_highway, is_sidepath_of)

            if is_sidepath == 'yes' and is_sidepath_of and is_sidepath_of in sidepath_dict[id]['maxspeed']:
                maxspeed = sidepath_dict[id]['maxspeed'][is_sidepath_of]
                if maxspeed:
                    layer.changeAttributeValue(feature.id(), id_proc_maxspeed, maxspeed)
            # transfer names to sidepath
            if is_sidepath == 'yes' and len(sidepath_dict[id]['name']):
                name = max(sidepath_dict[id]['name'], key=lambda k: sidepath_dict[id]['name'][k])  # the most frequent name in the surrounding
                if name:
                    layer.changeAttributeValue(feature.id(), layer.fields().indexOf('name'), name)
