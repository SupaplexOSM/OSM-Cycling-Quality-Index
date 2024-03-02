import imp
import time

from qgis.core import NULL, edit

import helper_functions
import script_step_05
import vars_settings

imp.reload(vars_settings)
imp.reload(helper_functions)
imp.reload(script_step_05)


def function_40(
    feature,
    way_type,
    side,
    layer,
    id_proc_oneway,
):
    """
    Derive oneway status.
    Can be one of the values in oneway_value_list (oneway applies to all vehicles, also for bicycles) or '*_motor_vehicles' (value applies to motor vehicles only)
    """

    oneway_value_list = ['yes', 'no', '-1', 'alternating', 'reversible']
    proc_oneway = NULL
    oneway = feature.attribute('oneway')
    oneway_bicycle = feature.attribute('oneway:bicycle')
    cycleway_oneway = feature.attribute('cycleway:oneway')
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
    way_type,
    feature,
    proc_oneway,
    side,
    oneway,
    data_missing,
):
    """
    Derive width.
    Use explicitly tagged attributes, derive from other attributes or use default values.
    """

    proc_width = NULL
    if way_type in ['cycle path', 'cycle track', 'shared path', 'shared footway', 'crossing', 'link', 'cycle lane (advisory)', 'cycle lane (exclusive)', 'cycle lane (protected)', 'cycle lane (central)']:
        # width for cycle lanes and sidewalks have already been derived from original tags when calculating way offsets
        proc_width = helper_functions.cast_to_float(feature.attribute('width'))
        if not proc_width:
            if way_type in ['cycle path', 'shared path', 'cycle lane (protected)']:
                proc_width = vars_settings.default_highway_width_dict['path']
            elif way_type == 'shared footway':
                proc_width = vars_settings.default_highway_width_dict['footway']
            else:
                proc_width = vars_settings.default_highway_width_dict['cycleway']
            if proc_width and proc_oneway == 'no':
                proc_width *= 1.6  # default values are for oneways - if the way isn't a oneway, widen the default
            data_missing = helper_functions.add_delimited_value(data_missing, 'width')
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
                data_missing = helper_functions.add_delimited_value(data_missing, 'width')
        else:
            proc_width = helper_functions.cast_to_float(feature.attribute('width'))
        if not proc_width:
            proc_width = vars_settings.default_highway_width_dict['path']
            if proc_oneway == 'no':
                proc_width *= 1.6
            data_missing = helper_functions.add_delimited_value(data_missing, 'width')
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
                    data_missing = helper_functions.add_delimited_value(data_missing, 'width:lanes')

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
                    parking_right_width = float(parking_right_width) / 2

                if parking_left == 'lane' or parking_left == 'half_on_kerb':
                    if not parking_left_width:
                        if parking_left_orientation == 'diagonal':
                            parking_left_width = vars_settings.default_width_parking_diagonal
                        elif parking_left_orientation == 'perpendicular':
                            parking_left_width = vars_settings.default_width_parking_perpendicular
                        else:
                            parking_left_width = vars_settings.default_width_parking_parallel
                if parking_left == 'half_on_kerb':
                    parking_left_width = float(parking_left_width) / 2
                if not parking_right_width:
                    parking_right_width = 0
                if not parking_left_width:
                    parking_left_width = 0

                # derive cycle lane width
                cycleway = feature.attribute('cycleway')
                cycleway_left = feature.attribute('cycleway:left')
                cycleway_right = feature.attribute('cycleway:right')
                cycleway_both = feature.attribute('cycleway:both')
                cycleway_width = feature.attribute('cycleway:width')
                cycleway_left_width = feature.attribute('cycleway:left:width')
                cycleway_right_width = feature.attribute('cycleway:right:width')
                cycleway_both_width = feature.attribute('cycleway:both:width')
                buffer = 0
                cycleway_right_buffer_left = NULL
                cycleway_right_buffer_right = NULL
                cycleway_left_buffer_left = NULL
                cycleway_left_buffer_right = NULL

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
                    cycleway_right_width = 0
                if not cycleway_left_width:
                    cycleway_left_width = 0
                if not cycleway_right_buffer_left or cycleway_right_buffer_left == 'no' or cycleway_right_buffer_left == 'none':
                    cycleway_right_buffer_left = 0
                if not cycleway_right_buffer_right or cycleway_right_buffer_right == 'no' or cycleway_right_buffer_right == 'none':
                    cycleway_right_buffer_right = 0
                if not cycleway_left_buffer_left or cycleway_left_buffer_left == 'no' or cycleway_left_buffer_left == 'none':
                    cycleway_left_buffer_left = 0
                if not cycleway_left_buffer_right or cycleway_left_buffer_right == 'no' or cycleway_left_buffer_right == 'none':
                    cycleway_left_buffer_right = 0

                # carriageway width: use default road width if no width is specified
                if not width:
                    highway = feature.attribute('highway')
                    width = vars_settings.default_highway_width_dict[highway]

                    # assume that oneway roads are narrower
                    if 'yes' in proc_oneway:
                        width = round(width / 1.6, 1)
                    data_missing = helper_functions.add_delimited_value(data_missing, 'width')

                buffer = helper_functions.cast_to_float(cycleway_right_buffer_left) + helper_functions.cast_to_float(cycleway_right_buffer_right) + helper_functions.cast_to_float(cycleway_left_buffer_left) + helper_functions.cast_to_float(cycleway_left_buffer_right)
                proc_width = width - helper_functions.cast_to_float(cycleway_right_width) - helper_functions.cast_to_float(cycleway_left_width) - buffer

                if parking_right or parking_left:
                    proc_width = proc_width - helper_functions.cast_to_float(parking_right_width) - helper_functions.cast_to_float(parking_left_width)
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
                        data_missing = helper_functions.add_delimited_value(data_missing, 'parking')

                # if width was derived from a default, the result should not be less than the default width of a motorcar lane
                if proc_width < vars_settings.default_width_traffic_lane and 'width' in data_missing:
                    proc_width = vars_settings.default_width_traffic_lane
    if not proc_width:
        proc_width = NULL

    return proc_width


def function_42(
    feature,
    way_type,
    data_missing,
):
    """
    Derive surface and smoothness.
    """

    proc_surface = None
    proc_smoothness = NULL

    # in rare cases, surface or smoothness is explicitly tagged for bicycles - check that first
    surface_bicycle: str = feature.attribute('surface:bicycle')
    smoothness_bicycle = feature.attribute('smoothness:bicycle')
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
                    highway = feature.attribute('highway')
                    if highway in vars_settings.default_highway_surface_dict:
                        proc_surface = vars_settings.default_highway_surface_dict[highway]
                    else:
                        proc_surface = vars_settings.default_highway_surface_dict['path']
                    data_missing = helper_functions.add_delimited_value(data_missing, 'surface')
            if not proc_smoothness:
                proc_smoothness = feature.attribute('cycleway:smoothness')
                if not proc_smoothness:
                    smoothness = feature.attribute('smoothness')
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
                    if tracktype in vars_settings.default_track_surface_dict:
                        proc_surface = vars_settings.default_track_surface_dict[tracktype]
                    else:
                        proc_surface = vars_settings.default_track_surface_dict['grade3']
                else:
                    highway = feature.attribute('highway')
                    if highway in vars_settings.default_highway_surface_dict:
                        proc_surface = vars_settings.default_highway_surface_dict[highway]
                    else:
                        proc_surface = vars_settings.default_highway_surface_dict['path']
                data_missing = helper_functions.add_delimited_value(data_missing, 'surface')
            if not proc_smoothness:
                proc_smoothness = feature.attribute('smoothness')
                if not proc_smoothness:
                    data_missing = helper_functions.add_delimited_value(data_missing, 'smoothness')

    # if more than one surface value is tagged (delimited by a semicolon), use the weakest one
    if ';' in proc_surface:
        proc_surface = helper_functions.get_weakest_surface_value(proc_surface.split(';'))
    if proc_surface not in vars_settings.surface_factor_dict:
        proc_surface = NULL
    if proc_smoothness not in vars_settings.smoothness_factor_dict:
        proc_smoothness = NULL
    return proc_surface, proc_smoothness


def function_43(
    way_type,
    feature,
    is_sidepath,
    side,
):
    """
    Derive (physical) separation and buffer.
    """

    traffic_mode_left = NULL
    traffic_mode_right = NULL
    separation_left = NULL
    separation_right = NULL
    buffer_left = NULL
    buffer_right = NULL

    if way_type == 'cycle lane (central)':
        traffic_mode_left = 'motor_vehicle'
        traffic_mode_right = 'motor_vehicle'
    else:
        # derive traffic modes for both sides of the way (default: motor vehicles on the left and foot on the right on cycleways)
        traffic_mode_left = feature.attribute('traffic_mode:left')
        traffic_mode_right = feature.attribute('traffic_mode:right')
        traffic_mode_both = feature.attribute('traffic_mode:both')
        # if there are parking lanes, assume they are next to the cycle way if no traffic modes are specified
        parking_right = feature.attribute('parking:right')
        parking_left = feature.attribute('parking:left')
        parking_both = feature.attribute('parking:both')
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
        separation_left = feature.attribute('separation:left')
        separation_right = feature.attribute('separation:right')
        separation_both = feature.attribute('separation:both')
        separation = feature.attribute('separation')
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
    feature,
    way_type,
    proc_oneway,
    is_sidepath,
):
    """
    Derive mandatory use as an extra information (not used for index calculation).
    """
    proc_mandatory = NULL
    proc_traffic_sign = NULL

    cycleway = feature.attribute('cycleway')
    cycleway_both = feature.attribute('cycleway:both')
    cycleway_left = feature.attribute('cycleway:left')
    cycleway_right = feature.attribute('cycleway:right')
    bicycle = feature.attribute('bicycle')
    traffic_sign: str = feature.attribute('traffic_sign')
    proc_traffic_sign = traffic_sign

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
                traffic_sign = traffic_sign.split(',;')
                for sign in traffic_sign:
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

    return proc_mandatory, proc_traffic_sign, cycleway, cycleway_both, cycleway_left, cycleway_right, bicycle


def step_04(
    layer,
    id_proc_oneway,
    id_proc_width,
    id_proc_surface,
    id_proc_smoothness,
    id_proc_traffic_mode_left,
    id_proc_traffic_mode_right,
    id_proc_separation_left,
    id_proc_separation_right,
    id_proc_buffer_left,
    id_proc_buffer_right,
    id_proc_mandatory,
    id_proc_traffic_sign,
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
    id_data_bonus,
    id_data_malus,
    id_data_incompleteness,
    id_fac_protection_level,
    id_prot_level_separation_left,
    id_prot_level_separation_right,
    id_prot_level_buffer_left,
    id_prot_level_buffer_right,
    id_prot_level_left,
    id_prot_level_right,
) -> None:
    """
    4: Derive relevant attributes for index and factors
    """

    print(time.strftime('%H:%M:%S', time.localtime()), 'Derive attributes...')
    with edit(layer):
        for feature in layer.getFeatures():
            way_type = feature.attribute('way_type')
            side = feature.attribute('side')
            is_sidepath = feature.attribute('proc_sidepath')
            data_missing = ''

            proc_oneway, oneway = function_40(
                feature,
                way_type,
                side,
                layer,
                id_proc_oneway,
            )

            proc_width = function_41(
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
