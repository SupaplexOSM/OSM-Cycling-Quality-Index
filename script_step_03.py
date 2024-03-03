import imp
import time

from qgis.core import NULL, QgsVectorLayer, edit  # type: ignore

import helper_functions
import vars_settings

imp.reload(vars_settings)
imp.reload(helper_functions)


def step_03(
    layer: QgsVectorLayer,
    id_way_type: int,
) -> None:
    """
    3: Determine way type for every way segment
    """

    print(time.strftime('%H:%M:%S', time.localtime()), 'Determine way type...')
    with edit(layer):
        for feature in layer.getFeatures():

            # exclude segments with no public bicycle access
            if helper_functions.get_access(feature, 'bicycle') and helper_functions.get_access(feature, 'bicycle') not in ['yes', 'permissive', 'designated', 'use_sidepath', 'optional_sidepath', 'discouraged']:
                layer.deleteFeature(feature.id())

            # exclude informal paths without explicit bicycle access
            if feature.attribute('highway') == 'path' and feature.attribute('informal') == 'yes' and feature.attribute('bicycle') == NULL:
                layer.deleteFeature(feature.id())

            way_type = ''
            highway = feature.attribute('highway')
            segregated = feature.attribute('segregated')

            bicycle = feature.attribute('bicycle')
            foot = feature.attribute('foot')
            # vehicle = feature.attribute('vehicle')  # TODO: remove this line, variable is unused
            is_sidepath = feature.attribute('is_sidepath')

            # before determining the way type according to highway tagging, first check for some specific way types that are tagged independent from "highway":
            if feature.attribute('bicycle_road') == 'yes':
                # features with a "side" attribute are representing a cycleway or footway adjacent to the road with offset geometry - treat them as separate path, not as a bicycle road
                side = feature.attribute('side')
                if not side:
                    way_type = 'bicycle road'
            if feature.attribute('footway') == 'link' or feature.attribute('cycleway') == 'link' or feature.attribute('path') == 'link' or feature.attribute('bridleway') == 'link':
                way_type = 'link'
            if feature.attribute('footway') == 'crossing' or feature.attribute('cycleway') == 'crossing' or feature.attribute('path') == 'crossing' or feature.attribute('bridleway') == 'crossing':
                way_type = 'crossing'

            # for all other cases: derive way type according to their primary "highway" tagging:
            if way_type == '':
                # for footways (with bicycle access):
                if highway in ['footway', 'pedestrian', 'bridleway', 'steps']:
                    if bicycle in ['yes', 'designated', 'permissive']:
                        way_type = 'shared footway'
                    else:
                        layer.deleteFeature(feature.id())  # don't process ways with restricted bicycle access

                # for path:
                elif highway == 'path':
                    if foot == 'designated' and bicycle != 'designated':
                        way_type = 'shared footway'
                    else:
                        if segregated == 'yes':
                            way_type = 'segregated path'
                        else:
                            way_type = 'shared path'

                # for cycleways:
                elif highway == 'cycleway':
                    if foot in ['yes', 'designated', 'permissive']:
                        way_type = 'shared path'
                    else:
                        separation_foot = helper_functions.derive_separation(feature, 'foot')
                        if separation_foot == 'no':
                            way_type = 'segregated path'
                        else:
                            if is_sidepath not in ['yes', 'no']:
                                # Use the geometrically determined sidepath value, if is_sidepath isn't specified
                                if feature.attribute('proc_sidepath') == 'yes':
                                    way_type = 'cycle track'
                                else:
                                    way_type = 'cycle path'
                                    if not feature.attribute('proc_sidepath') in ['yes', 'no']:
                                        print(feature.attribute('id'))

                            elif is_sidepath == 'yes':
                                separation_motor_vehicle = helper_functions.derive_separation(feature, 'motor_vehicle')
                                if separation_motor_vehicle not in [None, NULL, 'no', 'none']:
                                    if 'kerb' in separation_motor_vehicle or 'tree_row' in separation_motor_vehicle:
                                        way_type = 'cycle track'
                                    else:
                                        way_type = 'cycle lane (protected)'
                                else:
                                    way_type = 'cycle track'
                            else:
                                way_type = 'cycle path'

                # for service roads/tracks:
                elif highway == 'service' or highway == 'track':
                    way_type = 'track or service'

                # for regular roads:
                else:
                    cycleway = feature.attribute('cycleway')
                    cycleway_both = feature.attribute('cycleway:both')
                    cycleway_left = feature.attribute('cycleway:left')
                    cycleway_right = feature.attribute('cycleway:right')
                    bicycle = feature.attribute('bicycle')
                    side = feature.attribute('side')  # features with a "side" attribute are representing a cycleway or footway adjacent to the road with offset geometry
                    # if this feature don't represent a cycle lane, it's a center line representing the shared road
                    if not side:
                        # distinguish shared roads (without lane markings) and shared traffic lanes (with lane markings)
                        # (assume that there are lane markings on primary and secondary roads, even if not tagged explicitly)
                        lane_markings = feature.attribute('lane_markings')
                        if lane_markings == 'yes' or (lane_markings != 'yes' and highway in ['motorway', 'trunk', 'primary', 'secondary']):
                            way_type = 'shared traffic lane'
                        else:
                            way_type = 'shared road'
                    else:
                        way_type = feature.attribute('type')
                        if way_type == 'sidewalk':
                            way_type = 'shared footway'
                        else:
                            # for cycle lanes
                            if cycleway == 'lane' or cycleway_both == 'lane' or (side == 'right' and cycleway_right == 'lane') or (side == 'left' and cycleway_left == 'lane'):
                                cycleway_lanes = feature.attribute('cycleway:lanes')
                                if cycleway_lanes and 'no|lane|no' in cycleway_lanes:
                                    way_type = 'cycle lane (central)'
                                else:
                                    separation_motor_vehicle = helper_functions.derive_separation(feature, 'motor_vehicle')
                                    if separation_motor_vehicle not in [NULL, 'no', 'none']:
                                        way_type = 'cycle lane (protected)'
                                    else:
                                        cycleway_lane = feature.attribute('cycleway:lane')
                                        cycleway_both_lane = feature.attribute('cycleway:both:lane')
                                        cycleway_left_lane = feature.attribute('cycleway:left:lane')
                                        cycleway_right_lane = feature.attribute('cycleway:right:lane')
                                        if cycleway_lane == 'exclusive' or cycleway_both_lane == 'exclusive' or (side == 'right' and cycleway_right_lane == 'exclusive') or (side == 'left' and cycleway_left_lane == 'exclusive'):
                                            way_type = 'cycle lane (exclusive)'
                                        else:
                                            way_type = 'cycle lane (advisory)'
                            # for cycle tracks
                            elif cycleway == 'track' or cycleway_both == 'track' or (side == 'right' and cycleway_right == 'track') or (side == 'left' and cycleway_left == 'track'):
                                cycleway_foot = feature.attribute('cycleway:foot')
                                cycleway_both_foot = feature.attribute('cycleway:both:foot')
                                cycleway_left_foot = feature.attribute('cycleway:left:foot')
                                cycleway_right_foot = feature.attribute('cycleway:right:foot')
                                if (
                                    cycleway_foot in ['yes', 'designated', 'permissive']
                                    or cycleway_both_foot in ['yes', 'designated', 'permissive']
                                    or (side == 'right' and cycleway_right_foot in ['yes', 'designated', 'permissive'])
                                    or (side == 'left' and cycleway_left_foot in ['yes', 'designated', 'permissive'])
                                ):
                                    way_type = 'shared path'
                                else:
                                    cycleway_segregated = feature.attribute('cycleway:segregated')
                                    cycleway_both_segregated = feature.attribute('cycleway:both:segregated')
                                    cycleway_left_segregated = feature.attribute('cycleway:left:segregated')
                                    cycleway_right_segregated = feature.attribute('cycleway:right:segregated')
                                    if cycleway_segregated == 'yes' or cycleway_both_segregated == 'yes' or (side == 'right' and cycleway_right_segregated == 'yes') or (side == 'left' and cycleway_left_segregated == 'yes'):
                                        way_type = 'segregated path'
                                    elif cycleway_segregated == 'no' or cycleway_both_segregated == 'no' or (side == 'right' and cycleway_right_segregated == 'no') or (side == 'left' and cycleway_left_segregated == 'no'):
                                        way_type = 'shared path'
                                    else:
                                        separation_foot = helper_functions.derive_separation(feature, 'foot')
                                        if separation_foot == 'no':
                                            way_type = 'segregated path'
                                        else:
                                            separation_motor_vehicle = helper_functions.derive_separation(feature, 'motor_vehicle')
                                            if separation_motor_vehicle not in [NULL, 'no', 'none']:
                                                if 'kerb' in separation_motor_vehicle or 'tree_row' in separation_motor_vehicle:
                                                    way_type = 'cycle track'
                                                else:
                                                    way_type = 'cycle lane (protected)'
                                            else:
                                                way_type = 'cycle track'
                            # for shared bus lanes
                            elif cycleway == 'share_busway' or cycleway_both == 'share_busway' or (side == 'right' and cycleway_right == 'share_busway') or (side == 'left' and cycleway_left == 'share_busway'):
                                way_type = 'shared bus lane'
                            # for other vales - no cycle way
                            else:
                                sidewalk_bicycle = feature.attribute('sidewalk:bicycle')
                                sidewalk_both_bicycle = feature.attribute('sidewalk:both:bicycle')
                                sidewalk_left_bicycle = feature.attribute('sidewalk:left:bicycle')
                                sidewalk_right_bicycle = feature.attribute('sidewalk:right:bicycle')
                                if sidewalk_bicycle == 'yes' or sidewalk_both_bicycle == 'yes' or (side == 'right' and sidewalk_right_bicycle == 'yes') or (side == 'left' and sidewalk_left_bicycle == 'yes'):
                                    way_type = 'shared footway'
                                else:
                                    lane_markings = feature.attribute('lane_markings')
                                    if lane_markings == 'yes' or (lane_markings != 'yes' and highway in ['primary', 'secondary']):
                                        way_type = 'shared traffic lane'
                                    else:
                                        way_type = 'shared road'
            if way_type == '':
                way_type = NULL
            else:
                layer.changeAttributeValue(feature.id(), id_way_type, way_type)

        layer.updateFields()
