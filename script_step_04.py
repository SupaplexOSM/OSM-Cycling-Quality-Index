import imp
import time
from typing import Optional, Tuple

from qgis.core import QgsFeature, QgsVectorLayer, edit  # type: ignore

import helper_functions
import script_step_05
import vars_settings

imp.reload(vars_settings)
imp.reload(helper_functions)
imp.reload(script_step_05)


def function_40(
    feature: QgsFeature,
    way_type: str,
    side: str,
    layer: QgsVectorLayer,
    id_proc_oneway: int,
) -> Tuple[str, Optional[str]]:
    """
    Derive oneway status.
    Can be one of the values in oneway_value_list (oneway applies to all vehicles, also for bicycles) or '*_motor_vehicles' (value applies to motor vehicles only)
    """

    oneway_value_list = ['yes', 'no', '-1', 'alternating', 'reversible']
    proc_oneway: Optional[str] = None
    oneway: Optional[str] = feature.attribute('oneway')
    oneway_bicycle: Optional[str] = feature.attribute('oneway:bicycle')
    cycleway_oneway: Optional[str] = feature.attribute('cycleway:oneway')
    if way_type in ['cycle path', 'cycle track', 'shared path', 'segregated path', 'shared footway', 'crossing', 'link', 'cycle lane (advisory)', 'cycle lane (exclusive)', 'cycle lane (protected)', 'cycle lane (central)']:
        if oneway in oneway_value_list:
            proc_oneway = oneway
        elif cycleway_oneway in oneway_value_list:
            proc_oneway = cycleway_oneway
        else:
            if way_type in ['cycle track', 'shared path', 'shared footway'] and side:
                proc_oneway = vars_settings.default_oneway_cycle_track
            elif 'cycle lane' in way_type:
                proc_oneway = vars_settings.default_oneway_cycle_lane
            else:
                proc_oneway = 'no'
        if oneway_bicycle in oneway_value_list:  # usually not the case on cycle ways, but possible: overwrite oneway value with oneway:bicycle
            proc_oneway = oneway_bicycle

    if way_type == 'shared bus lane':
        proc_oneway = 'yes'  # shared bus lanes are represented by own geometry for the lane, and lanes are for oneway use only (usually)

    if way_type in ['shared road', 'shared traffic lane', 'bicycle road', 'track or service']:
        if not oneway_bicycle or oneway == oneway_bicycle:
            if oneway in oneway_value_list:
                proc_oneway = oneway
            else:
                proc_oneway = 'no'
        else:
            if oneway_bicycle and oneway_bicycle == 'no':
                if oneway in oneway_value_list:
                    proc_oneway = oneway + '_motor_vehicles'
                else:
                    proc_oneway = 'no'
            else:
                proc_oneway = 'yes'

    if not proc_oneway:
        proc_oneway = 'unknown'

    layer.changeAttributeValue(feature.id(), id_proc_oneway, proc_oneway)
    return proc_oneway, oneway


def function_41(
    way_type: str,
    feature: QgsFeature,
    proc_oneway: str,
    side: str,
    oneway: Optional[str],
    missing_data: str,
) -> Tuple[Optional[float], str]:
    """
    Derive width.
    Use explicitly tagged attributes, derive from other attributes or use default values.
    """

    proc_width: Optional[float] = None
    if way_type in ['cycle path', 'cycle track', 'shared path', 'shared footway', 'crossing', 'link', 'cycle lane (advisory)', 'cycle lane (exclusive)', 'cycle lane (protected)', 'cycle lane (central)']:
        # width for cycle lanes and sidewalks have already been derived from original tags when calculating way offsets
        proc_width = helper_functions.cast_to_float(feature.attribute('width'))
        if not proc_width:
            if way_type in ['cycle path', 'shared path', 'cycle lane (protected)']:
                proc_width = vars_settings.default_highway_width_defaultdict['path']
            elif way_type == 'shared footway':
                proc_width = vars_settings.default_highway_width_defaultdict['footway']
            else:
                proc_width = vars_settings.default_highway_width_defaultdict['cycleway']
            if proc_width and proc_oneway == 'no':
                proc_width *= 1.6  # default values are for oneways - if the way isn't a oneway, widen the default
            missing_data = helper_functions.add_delimited_value(missing_data, 'width')

    if way_type == 'segregated path':
        highway = feature.attribute('highway')
        if highway == 'path':
            proc_width = helper_functions.cast_to_float(feature.attribute('cycleway:width'))
            if not proc_width:
                width = helper_functions.cast_to_float(feature.attribute('width'))
                footway_width = helper_functions.cast_to_float(feature.attribute('footway:width'))
                if width:
                    if footway_width:
                        proc_width = width - footway_width
                    else:
                        proc_width = width / 2
                missing_data = helper_functions.add_delimited_value(missing_data, 'width')
        else:
            proc_width = helper_functions.cast_to_float(feature.attribute('width'))
        if not proc_width:
            proc_width = vars_settings.default_highway_width_defaultdict['path']
            if proc_oneway == 'no':
                proc_width *= 1.6
            missing_data = helper_functions.add_delimited_value(missing_data, 'width')

    if way_type in ['shared road', 'shared traffic lane', 'shared bus lane', 'bicycle road', 'track or service']:
        # on shared traffic or bus lanes, use a width value based on lane width, not on carriageway width
        if way_type in ['shared traffic lane', 'shared bus lane']:
            width_lanes = feature.attribute('width:lanes')
            width_lanes_forward = feature.attribute('width:lanes:forward')
            width_lanes_backward = feature.attribute('width:lanes:backward')
            if ('yes' in proc_oneway or way_type != 'shared bus lane') and width_lanes and '|' in width_lanes:
                # TODO: at the moment, forward/backward can only be processed for shared bus lanes, since there are no separate geometries for shared road lanes
                # TODO: for bus lanes, currently only assuming that the right lane is the bus lane. Instead derive lane position from "psv:lanes" or "bus:lanes", if specified
                proc_width = helper_functions.cast_to_float(width_lanes[width_lanes.rfind('|') + 1:])
            elif (way_type == 'shared bus lane' and 'yes' not in proc_oneway) and side == 'right' and width_lanes_forward and '|' in width_lanes_forward:
                proc_width = helper_functions.cast_to_float(width_lanes_forward[width_lanes_forward.rfind('|') + 1:])
            elif (way_type == 'shared bus lane' and 'yes' not in proc_oneway) and side == 'left' and width_lanes_backward and '|' in width_lanes_backward:
                proc_width = helper_functions.cast_to_float(width_lanes_backward[width_lanes_backward.rfind('|') + 1:])
            else:
                if way_type == 'shared bus lane':
                    proc_width = vars_settings.default_width_bus_lane
                else:
                    proc_width = vars_settings.default_width_traffic_lane
                    missing_data = helper_functions.add_delimited_value(missing_data, 'width:lanes')

        if not proc_width:
            # effective width (usable width of a road for flowing traffic) can be mapped explicitly
            proc_width = helper_functions.cast_to_float(feature.attribute('width:effective'))
            # try to use lane count and a default lane width if no width and no width:effective is mapped
            # (usually, this means, there are lane markings (see above), but sometimes "lane" tag is misused or "lane_markings" isn't mapped)
            if not proc_width:
                width = helper_functions.cast_to_float(feature.attribute('width'))
                if not width:
                    lanes = helper_functions.cast_to_float(feature.attribute('lanes'))
                    if lanes:
                        proc_width = lanes * vars_settings.default_width_traffic_lane
                        # TODO: take width:lanes into account, if mapped
            # derive effective road width from road width, parking and cycle lane information
            # subtract parking and cycle lane width from carriageway width to get effective width (usable width for driving)
            if not proc_width:
                # derive parking lane width
                parking_left = feature.attribute('parking:left')
                parking_left_orientation = feature.attribute('parking:left:orientation')
                parking_left_width = helper_functions.cast_to_float(feature.attribute('parking:left:width'))
                parking_right = feature.attribute('parking:right')
                parking_right_orientation = feature.attribute('parking:right:orientation')
                parking_right_width = helper_functions.cast_to_float(feature.attribute('parking:right:width'))
                parking_both = feature.attribute('parking:both')
                parking_both_orientation = feature.attribute('parking:both:orientation')
                parking_both_width = helper_functions.cast_to_float(feature.attribute('parking:both:width'))

                # split parking:both-keys into left and right values
                if parking_both:
                    if not parking_right:
                        parking_right = parking_both
                    if not parking_left:
                        parking_left = parking_both
                if parking_both_orientation:
                    if not parking_right_orientation:
                        parking_right_orientation = parking_both_orientation
                    if not parking_left_orientation:
                        parking_left_orientation = parking_both_orientation
                if parking_both_width:
                    if not parking_right_width:
                        parking_right_width = parking_both_width
                    if not parking_left_width:
                        parking_left_width = parking_both_width

                if parking_right == 'lane' or parking_right == 'half_on_kerb':
                    if not parking_right_width:
                        if parking_right_orientation == 'diagonal':
                            parking_right_width = vars_settings.default_width_parking_diagonal
                        elif parking_right_orientation == 'perpendicular':
                            parking_right_width = vars_settings.default_width_parking_perpendicular
                        else:
                            parking_right_width = vars_settings.default_width_parking_parallel
                if parking_right == 'half_on_kerb':
                    parking_right_width = helper_functions.cast_to_float(parking_right_width) / 2

                if parking_left == 'lane' or parking_left == 'half_on_kerb':
                    if not parking_left_width:
                        if parking_left_orientation == 'diagonal':
                            parking_left_width = vars_settings.default_width_parking_diagonal
                        elif parking_left_orientation == 'perpendicular':
                            parking_left_width = vars_settings.default_width_parking_perpendicular
                        else:
                            parking_left_width = vars_settings.default_width_parking_parallel
                if parking_left == 'half_on_kerb':
                    parking_left_width = helper_functions.cast_to_float(parking_left_width) / 2
                if not parking_right_width:
                    parking_right_width = 0.0
                if not parking_left_width:
                    parking_left_width = 0.0

                # derive cycle lane width
                cycleway: Optional[str] = feature.attribute('cycleway')
                cycleway_left: Optional[str] = feature.attribute('cycleway:left')
                cycleway_right: Optional[str] = feature.attribute('cycleway:right')
                cycleway_both: Optional[str] = feature.attribute('cycleway:both')
                cycleway_width: Optional[float] = helper_functions.cast_to_float(feature.attribute('cycleway:width'))
                cycleway_left_width: Optional[float] = helper_functions.cast_to_float(feature.attribute('cycleway:left:width'))
                cycleway_right_width: Optional[float] = helper_functions.cast_to_float(feature.attribute('cycleway:right:width'))
                cycleway_both_width: Optional[float] = helper_functions.cast_to_float(feature.attribute('cycleway:both:width'))
                buffer = 0.0
                cycleway_right_buffer_left = None
                cycleway_right_buffer_right = None
                cycleway_left_buffer_left = None
                cycleway_left_buffer_right = None

                # split cycleway:both-keys into left and right values
                if cycleway:
                    if not cycleway_right:
                        cycleway_right = cycleway
                    if not cycleway_left and (not oneway or oneway == 'no'):
                        cycleway_left = cycleway
                if cycleway_both:
                    if not cycleway_right:
                        cycleway_right = cycleway_both
                    if not cycleway_left:
                        cycleway_left = cycleway_both
                if cycleway_right == 'lane' or cycleway_left == 'lane':
                    if cycleway_width:
                        if not cycleway_right_width:
                            cycleway_right_width = cycleway_width
                        if not cycleway_left_width and (not oneway or oneway == 'no'):
                            cycleway_left_width = cycleway_width
                    if cycleway_both_width:
                        if not cycleway_right_width:
                            cycleway_right_width = cycleway_both_width
                        if not cycleway_left_width:
                            cycleway_left_width = cycleway_both_width

                    # cycleway buffers must also be subtracted from the road width
                    cycleway_buffer = feature.attribute('cycleway:buffer')
                    cycleway_left_buffer = feature.attribute('cycleway:left:buffer')
                    cycleway_right_buffer = feature.attribute('cycleway:right:buffer')
                    cycleway_both_buffer = feature.attribute('cycleway:both:buffer')
                    cycleway_buffer_left = feature.attribute('cycleway:buffer:left')
                    cycleway_left_buffer_left = feature.attribute('cycleway:left:buffer:left')
                    cycleway_right_buffer_left = feature.attribute('cycleway:right:buffer:left')
                    cycleway_both_buffer_left = feature.attribute('cycleway:both:buffer:left')
                    cycleway_buffer_right = feature.attribute('cycleway:buffer:right')
                    cycleway_left_buffer_right = feature.attribute('cycleway:left:buffer:right')
                    cycleway_right_buffer_right = feature.attribute('cycleway:right:buffer:right')
                    cycleway_both_buffer_right = feature.attribute('cycleway:both:buffer:right')
                    cycleway_buffer_both = feature.attribute('cycleway:buffer:both')
                    cycleway_left_buffer_both = feature.attribute('cycleway:left:buffer:both')
                    cycleway_right_buffer_both = feature.attribute('cycleway:right:buffer:both')
                    cycleway_both_buffer_both = feature.attribute('cycleway:both:buffer:both')

                    if cycleway_right == 'lane':
                        if not cycleway_right_width:
                            cycleway_right_width = vars_settings.default_width_cycle_lane
                        for buffer_tag in [cycleway_right_buffer_left, cycleway_right_buffer_both, cycleway_right_buffer, cycleway_both_buffer_left, cycleway_both_buffer_both, cycleway_both_buffer, cycleway_buffer_left, cycleway_buffer_both, cycleway_buffer]:
                            if not cycleway_right_buffer_left:
                                cycleway_right_buffer_left = buffer_tag
                            else:
                                break
                        for buffer_tag in [cycleway_right_buffer_right, cycleway_right_buffer_both, cycleway_right_buffer, cycleway_both_buffer_right, cycleway_both_buffer_both, cycleway_both_buffer, cycleway_buffer_right, cycleway_buffer_both, cycleway_buffer]:
                            if not cycleway_right_buffer_right:
                                cycleway_right_buffer_right = buffer_tag
                            else:
                                break
                    if cycleway_left == 'lane':
                        if not cycleway_left_width:
                            cycleway_left_width = vars_settings.default_width_cycle_lane
                        for buffer_tag in [cycleway_left_buffer_left, cycleway_left_buffer_both, cycleway_left_buffer, cycleway_both_buffer_left, cycleway_both_buffer_both, cycleway_both_buffer, cycleway_buffer_left, cycleway_buffer_both, cycleway_buffer]:
                            if not cycleway_left_buffer_left:
                                cycleway_left_buffer_left = buffer_tag
                            else:
                                break
                        for buffer_tag in [cycleway_left_buffer_right, cycleway_left_buffer_both, cycleway_left_buffer, cycleway_both_buffer_right, cycleway_both_buffer_both, cycleway_both_buffer, cycleway_buffer_right, cycleway_buffer_both, cycleway_buffer]:
                            if not cycleway_left_buffer_right:
                                cycleway_left_buffer_right = buffer_tag
                            else:
                                break
                if not cycleway_right_width:
                    cycleway_right_width = 0.0
                if not cycleway_left_width:
                    cycleway_left_width = 0.0
                if not cycleway_right_buffer_left or cycleway_right_buffer_left == 'no' or cycleway_right_buffer_left == 'none':
                    cycleway_right_buffer_left = 0.0
                if not cycleway_right_buffer_right or cycleway_right_buffer_right == 'no' or cycleway_right_buffer_right == 'none':
                    cycleway_right_buffer_right = 0
                if not cycleway_left_buffer_left or cycleway_left_buffer_left == 'no' or cycleway_left_buffer_left == 'none':
                    cycleway_left_buffer_left = 0
                if not cycleway_left_buffer_right or cycleway_left_buffer_right == 'no' or cycleway_left_buffer_right == 'none':
                    cycleway_left_buffer_right = 0

                # carriageway width: use default road width if no width is specified
                if not width:
                    highway = feature.attribute('highway')
                    width = vars_settings.default_highway_width_defaultdict[highway]

                    # assume that oneway roads are narrower
                    if 'yes' in proc_oneway:
                        width = round(width / 1.6, 1)
                    missing_data = helper_functions.add_delimited_value(missing_data, 'width')

                buffer = (
                    float(cycleway_right_buffer_left)
                    + float(cycleway_right_buffer_right)
                    + float(cycleway_left_buffer_left)
                    + float(cycleway_left_buffer_right)
                )
                proc_width = width - float(cycleway_right_width) - float(cycleway_left_width) - buffer

                if parking_right or parking_left:
                    proc_width -= parking_right_width - parking_left_width
                # if parking isn't mapped on regular shared roads, reduce width if it's above a threshold (assuming there might be unmapped parking)
                else:
                    if way_type == 'shared road':
                        if 'yes' not in proc_oneway:
                            # assume that 5.5m of a regular unmarked carriageway are used for driving, other space for parking...
                            proc_width = min(proc_width, 5.5)
                        else:
                            # resp. 4m in oneway roads
                            proc_width = min(proc_width, 4)
                        # mark "parking" as a missing value if there are no parking tags on regular roads
                        # TODO: Differentiate between inner and outer urban areas/city limits - out of cities, there is usually no need to map street parking
                        missing_data = helper_functions.add_delimited_value(missing_data, 'parking')

                # if width was derived from a default, the result should not be less than the default width of a motorcar lane
                if proc_width < vars_settings.default_width_traffic_lane and 'width' in missing_data:
                    proc_width = vars_settings.default_width_traffic_lane
    if not proc_width:
        proc_width = None

    return proc_width, missing_data


def function_42(
    feature: QgsFeature,
    way_type: str,
    data_missing: str,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Derive surface and smoothness.
    """

    proc_surface: Optional[str] = None
    proc_smoothness: Optional[str] = None

    # in rare cases, surface or smoothness is explicitly tagged for bicycles - check that first
    surface_bicycle: str = feature.attribute('surface:bicycle')
    smoothness_bicycle: str = feature.attribute('smoothness:bicycle')
    if surface_bicycle:
        if surface_bicycle in vars_settings.surface_factor_dict:
            proc_surface = surface_bicycle
        elif ';' in surface_bicycle:
            proc_surface = helper_functions.get_weakest_surface_value(surface_bicycle.split(';'))
    if smoothness_bicycle and smoothness_bicycle in vars_settings.smoothness_factor_dict:
        proc_smoothness = smoothness_bicycle

    if not proc_surface:
        if way_type == 'segregated path':
            proc_surface = feature.attribute('cycleway:surface')
            if not proc_surface:
                surface = feature.attribute('surface')
                if surface:
                    proc_surface = surface
                else:
                    proc_surface = vars_settings.default_highway_surface_defaultdict[feature.attribute('highway')]
                    data_missing = helper_functions.add_delimited_value(data_missing, 'surface')
            if not proc_smoothness:
                proc_smoothness = feature.attribute('cycleway:smoothness')
                if not proc_smoothness:
                    smoothness: Optional[str] = feature.attribute('smoothness')
                    if smoothness:
                        proc_smoothness = smoothness
                    else:
                        data_missing = helper_functions.add_delimited_value(data_missing, 'smoothness')
        else:
            # surface and smoothness for cycle lanes and sidewalks have already been derived from original tags when calculating way offsets
            proc_surface = feature.attribute('surface')
            if not proc_surface:
                if way_type in ['cycle lane (advisory)', 'cycle lane (exclusive)', 'cycle lane (protected)', 'cycle lane (central)']:
                    proc_surface = vars_settings.default_cycleway_surface_lanes
                elif way_type == 'cycle track':
                    proc_surface = vars_settings.default_cycleway_surface_tracks
                elif way_type == 'track or service':
                    tracktype = feature.attribute('tracktype')
                    proc_surface = vars_settings.default_track_surface_defaultdict[tracktype]
                else:
                    proc_surface = vars_settings.default_highway_surface_defaultdict[feature.attribute('highway')]
                data_missing = helper_functions.add_delimited_value(data_missing, 'surface')
            if not proc_smoothness:
                proc_smoothness = feature.attribute('smoothness')
                if not proc_smoothness:
                    data_missing = helper_functions.add_delimited_value(data_missing, 'smoothness')

    # if more than one surface value is tagged (delimited by a semicolon), use the weakest one
    if proc_surface is not None and ';' in proc_surface:
        proc_surface = helper_functions.get_weakest_surface_value(proc_surface.split(';'))
    if proc_surface not in vars_settings.surface_factor_dict:
        proc_surface = None
    if proc_smoothness not in vars_settings.smoothness_factor_dict:
        proc_smoothness = None

    return proc_surface, proc_smoothness


def function_43(
    way_type: str,
    feature: QgsFeature,
    is_sidepath: Optional[str],
    side: str,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[float], Optional[float]]:
    """
    Derive (physical) separation and buffer.
    """

    if way_type == 'cycle lane (central)':
        return 'motor_vehicle', 'motor_vehicle', None, None, None, None

    # derive traffic modes for both sides of the way (default: motor vehicles on the left and foot on the right on cycleways)
    traffic_mode_left: Optional[str] = feature.attribute('traffic_mode:left')
    traffic_mode_right: Optional[str] = feature.attribute('traffic_mode:right')
    traffic_mode_both: Optional[str] = feature.attribute('traffic_mode:both')
    # if there are parking lanes, assume they are next to the cycle way if no traffic modes are specified
    parking_right: Optional[str] = feature.attribute('parking:right')
    parking_left: Optional[str] = feature.attribute('parking:left')
    parking_both: Optional[str] = feature.attribute('parking:both')
    # TODO: check for existence of sidewalks to derive whether traffic mode on the right is foot or no traffic for default
    if parking_both:
        if not parking_left:
            parking_left = parking_both
        if not parking_right:
            parking_right = parking_both
    if traffic_mode_both:
        if not traffic_mode_left:
            traffic_mode_left = traffic_mode_both
        if not traffic_mode_right:
            traffic_mode_right = traffic_mode_both
    if not traffic_mode_left:
        if way_type == 'cycle path':
            traffic_mode_left = 'no'
        elif way_type in ['cycle track', 'shared path', 'segregated path', 'shared footway'] and is_sidepath == 'yes':
            if ((side == 'right' and parking_right and parking_right != 'no') or (side == 'left' and parking_left and parking_left != 'no')) and traffic_mode_right != 'parking':
                traffic_mode_left = 'parking'
            else:
                traffic_mode_left = 'motor_vehicle'
        elif 'cycle lane' in way_type or way_type in ['shared road', 'shared traffic lane', 'shared bus lane', 'crossing']:
            traffic_mode_left = 'motor_vehicle'
    if not traffic_mode_right:
        if way_type == 'cycle path':
            traffic_mode_right = 'no'
        elif way_type == 'crossing':
            traffic_mode_right = 'motor_vehicle'
        elif 'cycle lane' in way_type:
            if ((side == 'right' and parking_right and parking_right != 'no') or (side == 'left' and parking_left and parking_left != 'no')) and traffic_mode_left != 'parking':
                traffic_mode_right = 'parking'
            else:
                traffic_mode_right = 'foot'
        elif way_type in ['cycle track', 'shared path', 'segregated path', 'shared footway'] and is_sidepath == 'yes':
            traffic_mode_right = 'foot'
    separation_left: Optional[str] = feature.attribute('separation:left')
    separation_right: Optional[str] = feature.attribute('separation:right')
    separation_both: Optional[str] = feature.attribute('separation:both')
    separation: Optional[str] = feature.attribute('separation')
    if separation_both:
        if not separation_left:
            separation_left = separation_both
        if not separation_right:
            separation_right = separation_both
    if separation:
        # in case of separation, a key without side suffix only refers to the side with vehicle traffic
        if vars_settings.right_hand_traffic:
            if traffic_mode_left in ['motor_vehicle', 'psv', 'parking']:
                if not separation_left:
                    separation_left = separation
            else:
                if traffic_mode_right == 'motor_vehicle' and not separation_right:
                    separation_right = separation
        else:
            if traffic_mode_right in ['motor_vehicle', 'psv', 'parking']:
                if not separation_right:
                    separation_right = separation
            else:
                if traffic_mode_left == 'motor_vehicle' and not separation_left:
                    separation_left = separation
    if not separation_left:
        separation_left = 'no'
    if not separation_right:
        separation_right = 'no'

    buffer_left = helper_functions.cast_to_float(feature.attribute('buffer:left'))
    buffer_right = helper_functions.cast_to_float(feature.attribute('buffer:right'))
    buffer_both = helper_functions.cast_to_float(feature.attribute('buffer:both'))
    buffer = helper_functions.cast_to_float(feature.attribute('buffer'))
    if buffer_both:
        if not buffer_left:
            buffer_left = buffer_both
        if not buffer_right:
            buffer_right = buffer_both
    if buffer:
        # in case of buffer, a key without side suffix only refers to the side with vehicle traffic
        if vars_settings.right_hand_traffic:
            if traffic_mode_left in ['motor_vehicle', 'psv', 'parking']:
                if not buffer_left:
                    buffer_left = buffer
            else:
                if traffic_mode_right == 'motor_vehicle' and not buffer_right:
                    buffer_right = buffer
        else:
            if traffic_mode_right in ['motor_vehicle', 'psv', 'parking']:
                if not buffer_right:
                    buffer_right = buffer
            else:
                if traffic_mode_left == 'motor_vehicle' and not buffer_left:
                    buffer_left = buffer

    return traffic_mode_left, traffic_mode_right, separation_left, separation_right, buffer_left, buffer_right


def function_44(
    feature: QgsFeature,
    way_type: str,
    proc_oneway: str,
    is_sidepath: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Derive mandatory use as an extra information (not used for index calculation).
    """
    proc_mandatory: Optional[str] = None

    cycleway: Optional[str] = feature.attribute('cycleway')
    cycleway_both: Optional[str] = feature.attribute('cycleway:both')
    cycleway_left: Optional[str] = feature.attribute('cycleway:left')
    cycleway_right: Optional[str] = feature.attribute('cycleway:right')
    bicycle: Optional[str] = feature.attribute('bicycle')
    traffic_sign: Optional[str] = feature.attribute('traffic_sign')

    if way_type in ['bicycle road', 'shared road', 'shared traffic lane', 'track or service']:
        # if cycle lanes are present, mark center line as "use sidepath"
        if cycleway in ['lane', 'share_busway'] or cycleway_both in ['lane', 'share_busway'] or ('yes' in proc_oneway and cycleway_right in ['lane', 'share_busway']):
            proc_mandatory = 'use_sidepath'
        # if tracks are present, mark center line as "optional sidepath" - as well as if "bicycle" is explicitly tagged as "optional_sidepath"
        elif cycleway == 'track' or cycleway_both == 'track' or ('yes' in proc_oneway and cycleway_right == 'track'):
            proc_mandatory = 'optional_sidepath'
        if bicycle in ['use_sidepath', 'optional_sidepath']:
            proc_mandatory = bicycle
    else:
        if is_sidepath == 'yes':
            # derive mandatory use from the presence of traffic signs
            if traffic_sign:
                for sign in traffic_sign.split(',;'):
                    for mandatory_sign in vars_settings.not_mandatory_traffic_sign_list:
                        if mandatory_sign in sign:
                            proc_mandatory = 'no'
                    for mandatory_sign in vars_settings.mandatory_traffic_sign_list:
                        if mandatory_sign in sign:
                            proc_mandatory = 'yes'

    # mark cycle prohibitions
    highway = feature.attribute('highway')
    if highway in vars_settings.cycling_highway_prohibition_list or bicycle == 'no':
        proc_mandatory = 'prohibited'

    return proc_mandatory, traffic_sign, cycleway, cycleway_both, cycleway_left, cycleway_right, bicycle


def step_04(
    layer: QgsVectorLayer,
    id_proc_oneway: int,
    id_proc_width: int,
    id_proc_surface: int,
    id_proc_smoothness: int,
    id_proc_traffic_mode_left: int,
    id_proc_traffic_mode_right: int,
    id_proc_separation_left: int,
    id_proc_separation_right: int,
    id_proc_buffer_left: int,
    id_proc_buffer_right: int,
    id_proc_mandatory: int,
    id_proc_traffic_sign: int,
    id_base_index: int,
    id_fac_width: int,
    id_fac_surface: int,
    id_fac_highway: int,
    id_fac_maxspeed: int,
    id_fac_1: int,
    id_fac_2: int,
    id_fac_3: int,
    id_fac_4: int,
    id_index: int,
    id_data_missing: int,
    id_data_bonus: int,
    id_data_malus: int,
    id_data_incompleteness: int,
    id_fac_protection_level: int,
    id_prot_level_separation_left: int,
    id_prot_level_separation_right: int,
    id_prot_level_buffer_left: int,
    id_prot_level_buffer_right: int,
    id_prot_level_left: int,
    id_prot_level_right: int,
) -> None:
    """
    4: Derive relevant attributes for index and factors
    """

    print(time.strftime('%H:%M:%S', time.localtime()), 'Derive attributes...')
    with edit(layer):
        for feature in layer.getFeatures():
            way_type: str = str(feature.attribute('way_type'))
            side: str = str(feature.attribute('side'))
            is_sidepath: Optional[str] = feature.attribute('proc_sidepath')
            data_missing: str = ''

            proc_oneway, oneway = function_40(
                feature,
                way_type,
                side,
                layer,
                id_proc_oneway,
            )

            proc_width, data_missing = function_41(
                way_type,
                feature,
                proc_oneway,
                side,
                oneway,
                data_missing,
            )

            layer.changeAttributeValue(feature.id(), id_proc_width, proc_width)

            proc_surface, proc_smoothness = function_42(
                feature,
                way_type,
                data_missing,
            )

            layer.changeAttributeValue(feature.id(), id_proc_surface, proc_surface)
            layer.changeAttributeValue(feature.id(), id_proc_smoothness, proc_smoothness)

            traffic_mode_left, traffic_mode_right, separation_left, separation_right, buffer_left, buffer_right = function_43(
                way_type,
                feature,
                is_sidepath,
                side,
            )

            layer.changeAttributeValue(feature.id(), id_proc_traffic_mode_left, traffic_mode_left)
            layer.changeAttributeValue(feature.id(), id_proc_traffic_mode_right, traffic_mode_right)
            layer.changeAttributeValue(feature.id(), id_proc_separation_left, separation_left)
            layer.changeAttributeValue(feature.id(), id_proc_separation_right, separation_right)
            layer.changeAttributeValue(feature.id(), id_proc_buffer_left, buffer_left)
            layer.changeAttributeValue(feature.id(), id_proc_buffer_right, buffer_right)

            proc_mandatory, proc_traffic_sign, cycleway, cycleway_both, cycleway_left, cycleway_right, bicycle = function_44(
                feature,
                way_type,
                proc_oneway,
                is_sidepath,
            )

            layer.changeAttributeValue(feature.id(), id_proc_mandatory, proc_mandatory)
            layer.changeAttributeValue(feature.id(), id_proc_traffic_sign, proc_traffic_sign)

            script_step_05.step_05(
                layer,
                id_base_index,
                id_fac_width,
                id_fac_surface,
                id_fac_highway,
                id_fac_maxspeed,
                id_fac_1,
                id_fac_2,
                id_fac_3,
                id_fac_4,
                id_index,
                id_data_missing,
                data_missing,
                id_data_bonus,
                id_data_malus,
                id_data_incompleteness,
                way_type,
                feature,
                proc_width,
                proc_oneway,
                proc_smoothness,
                proc_surface,
                is_sidepath,
                cycleway,
                cycleway_both,
                cycleway_left,
                cycleway_right,
                traffic_mode_left,
                traffic_mode_right,
                buffer_left,
                buffer_right,
                bicycle,
                id_fac_protection_level,
                id_prot_level_separation_left,
                id_prot_level_separation_right,
                id_prot_level_buffer_left,
                id_prot_level_buffer_right,
                id_prot_level_left,
                id_prot_level_right,
                separation_right,
                separation_left,
            )

        layer.updateFields()
