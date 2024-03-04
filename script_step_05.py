import imp
import math
from typing import Optional, Tuple

from qgis.core import NULL  # type: ignore
from qgis.core import QgsFeature, QgsVectorLayer

import helper_functions
import vars_settings

imp.reload(vars_settings)
imp.reload(helper_functions)


def function_50(
    way_type: str,
    feature: QgsFeature,
    layer: QgsVectorLayer,
    id_base_index: int,
    bonus_data: str,
) -> Tuple[Optional[str], int, str]:
    """
    Set base index according to way type
    """

    base_index = vars_settings.base_index_defaultdict[way_type]

    motor_vehicle_access = None  # TODO: set sensible default, idk if this works

    # on roads with restricted motor vehicle access, overwrite the base index with a access-specific base index
    if way_type in ['bicycle road', 'shared road', 'shared traffic lane', 'track or service']:
        motor_vehicle_access = helper_functions.get_access(feature, 'motor_vehicle')
        if motor_vehicle_access in vars_settings.motor_vehicle_access_index_dict:
            base_index = vars_settings.motor_vehicle_access_index_dict[motor_vehicle_access]
            bonus_data = helper_functions.add_delimited_value(bonus_data, 'motor vehicle restricted')
    layer.changeAttributeValue(feature.id(), id_base_index, base_index)

    return motor_vehicle_access, base_index, bonus_data


def function_51(
    way_type: str,
    proc_width: Optional[float],
    proc_oneway: str,
    feature: QgsFeature,
    layer: QgsVectorLayer,
    motor_vehicle_access: Optional[str],
    id_fac_width: int,
    malus_data: str,
    bonus_data: str,
) -> Tuple[float, str, str]:
    """
    Calculate width factor according to way type
    """

    calc_width = NULL
    minimum_factor = 0.0
    # for dedicated ways for cycling
    if way_type not in ['bicycle road', 'shared road', 'shared traffic lane', 'shared bus lane', 'track or service'] or helper_functions.get_access(feature, 'motor_vehicle') == 'no':
        calc_width = proc_width
        # calculated width depends on the width/space per driving direction
        if calc_width and 'yes' not in proc_oneway:
            calc_width /= 1.6

    # for shared roads and lanes
    else:
        calc_width = proc_width
        minimum_factor = 0.25  # on shared roads, there is a minimum width factor, because in case of doubt, other vehicles have to pass careful or can't overtake
        if calc_width:
            if way_type == 'shared traffic lane':
                calc_width = max(calc_width - 2 + ((4.5 - calc_width) / 3), 0)
            elif way_type == 'shared bus lane':
                calc_width = max(calc_width - 3 + ((5.5 - calc_width) / 3), 0)
            else:
                if 'yes' not in proc_oneway:
                    calc_width /= 1.6

                # TODO: Use a global 'optimum road width' variable for this?

                calc_width -= 2
                # on motor vehicle roads, optimum width is 2m for a car + 1m for bicycle + 1.5m safety distance -> exactly 2m more than the optimum width on cycleways.
                # Simply subtract 2m from the processed width to get a comparable width value that can be used with the following width factor formula

    fac_width: float = 0.0  # TODO: check if this is a correct fallback value

    # Calculate width factor (logistic regression)
    if calc_width:
        # factor should not be negative and not 0, since the following logistic regression isn't working for 0
        calc_width = max(0.001, calc_width)
        # regular formula
        if calc_width <= 3 or way_type in ['bicycle road', 'shared road', 'shared traffic lane', 'shared bus lane', 'track or service']:
            fac_width = 1.1 / (1 + 20 * math.e ** (-2.1 * calc_width))
        # formula for extra wide ways (not used for shared roads and lanes)
        else:
            fac_width = 2 / (1 + 1.8 * math.e ** (-0.24 * calc_width))

        # on roads with restricted motor vehicle access, the width factor has a lower weight, because it can be assumed that there is less traffic that shares the road width
        if way_type in ['bicycle road', 'shared road', 'shared traffic lane', 'track or service'] and motor_vehicle_access in vars_settings.motor_vehicle_access_index_dict:
            fac_width = fac_width + ((1 - fac_width) / 2)

        fac_width = round(max(minimum_factor, fac_width), 3)

    layer.changeAttributeValue(feature.id(), id_fac_width, fac_width)

    if fac_width > 1.0:
        bonus_data = helper_functions.add_delimited_value(bonus_data, 'wide width')
    elif fac_width <= 0.5:
        malus_data = helper_functions.add_delimited_value(malus_data, 'narrow width')

    return fac_width, bonus_data, malus_data


def function_52(
    proc_smoothness: Optional[str],
    proc_surface: Optional[str],
    feature: QgsFeature,
    id_fac_surface: int,
    layer: QgsVectorLayer,
    bonus_data: str,
    malus_data: str,
) -> Tuple[float, str, str]:
    """
    Calculate surface and smoothness factor
    """

    fac_surface: float = 0.0  # TODO:check if default of 0 is correct
    if proc_smoothness and proc_smoothness in vars_settings.smoothness_factor_dict:
        fac_surface = vars_settings.smoothness_factor_dict[proc_smoothness]
    elif proc_surface and proc_surface in vars_settings.surface_factor_dict:
        fac_surface = vars_settings.surface_factor_dict[proc_surface]

    layer.changeAttributeValue(feature.id(), id_fac_surface, fac_surface)

    if fac_surface > 1:
        bonus_data = helper_functions.add_delimited_value(bonus_data, 'excellent surface')
    if fac_surface and fac_surface <= 0.5:
        malus_data = helper_functions.add_delimited_value(malus_data, 'bad surface')

    return fac_surface, bonus_data, malus_data


def function_53(
    feature: QgsFeature,
) -> Tuple[float, float]:
    """
    Calculate highway (sidepath) and maxspeed factor
    """

    proc_maxspeed: Optional[int] = feature.attribute('proc_maxspeed')

    fac_maxspeed = 1.0
    fac_highway = vars_settings.highway_factor_dict.get(feature.attribute('proc_highway'), 1.0)

    if proc_maxspeed:
        # TODO: the order of keys in a dictionary is not guaranteed! should they be ascending/descending?
        # if so, sorting the resulting list of strings is better and if one >= maxspeed is found, you can break out of the loop
        for maxspeed in vars_settings.maxspeed_factor_dict.keys():
            if proc_maxspeed >= maxspeed:
                fac_maxspeed = vars_settings.maxspeed_factor_dict[maxspeed]

    return fac_highway, fac_maxspeed


def function_54(
    is_sidepath: Optional[str],
    traffic_mode_left: Optional[str],
    traffic_mode_right: Optional[str],
    layer: QgsVectorLayer,
    buffer_left: Optional[float],
    buffer_right: Optional[float],
    feature: QgsFeature,
    id_prot_level_separation_left: int,
    id_prot_level_separation_right: int,
    id_prot_level_buffer_left: int,
    id_prot_level_buffer_right: int,
    id_prot_level_left: int,
    id_prot_level_right: int,
    separation_right: str,
    separation_left: str,
) -> float:
    """
    Calculate (physical) separation and buffer factor
    """

    # not (is_sidepath == 'yes' and (traffic_mode_left or traffic_mode_right))
    # is_sidepath != 'yes' or not (traffic_mode_left or traffic_mode_right))
    # is_sidepath != 'yes' or (not traffic_mode_left and not traffic_mode_right))
    if is_sidepath != 'yes' or (not traffic_mode_left and not traffic_mode_right):  # only for sidepath geometries
        return 0.0

    # get the "strongest" separation value for each side and derive a protection level from that
    prot_level_separation_left = 0.0
    if separation_left:
        for separation in separation_left.split(';'):
            prot_level = vars_settings.separation_level_defaultdict[separation]
            prot_level_separation_left = max(prot_level_separation_left, prot_level)
    prot_level_separation_right = 0.0
    if separation_right:
        for separation in separation_right.split(';'):
            prot_level = vars_settings.separation_level_defaultdict[separation]
            prot_level_separation_right = max(prot_level_separation_right, prot_level)

    # derive protection level indicated by a buffer zone (a value from 0 to 1, half of the buffer width)
    prot_level_buffer_left: float = min(buffer_left / 2, 1)
    prot_level_buffer_right = min(buffer_right / 2, 1)

    # derive a total protection level per side (separation has a stronger weight, because it results in more (perception of) safeness)
    prot_level_left = (prot_level_separation_left * 2 + prot_level_buffer_left) / 3
    prot_level_right = (prot_level_separation_right * 2 + prot_level_buffer_right) / 3

    layer.changeAttributeValue(feature.id(), id_prot_level_separation_left, round(prot_level_separation_left, 3))
    layer.changeAttributeValue(feature.id(), id_prot_level_separation_right, round(prot_level_separation_right, 3))
    layer.changeAttributeValue(feature.id(), id_prot_level_buffer_left, round(prot_level_buffer_left, 3))
    layer.changeAttributeValue(feature.id(), id_prot_level_buffer_right, round(prot_level_buffer_right, 3))
    layer.changeAttributeValue(feature.id(), id_prot_level_left, round(prot_level_left, 3))
    layer.changeAttributeValue(feature.id(), id_prot_level_right, round(prot_level_right, 3))

    # derive a factor from that protection level values (0.9: no protection, 1.4: high protection)
    # if there is motor vehicle traffic on one side and foot (or bicycle) traffic on the other, the factor is composed of 75% motor vehicle side and 25% of the other side.
    if traffic_mode_left in ['motor_vehicle', 'psv', 'parking'] and traffic_mode_right in ['foot', 'bicycle']:
        prot_level = prot_level_left * 0.75 + prot_level_right * 0.25
    if traffic_mode_left in ['foot', 'bicycle'] and traffic_mode_right in ['motor_vehicle', 'psv', 'parking']:
        prot_level = prot_level_left * 0.25 + prot_level_right * 0.75
    # same traffic mode on both sides: protection level is the average of both sides levels
    if (traffic_mode_left in ['motor_vehicle', 'psv', 'parking'] and traffic_mode_right in ['motor_vehicle', 'psv', 'parking']) or (traffic_mode_left in ['foot', 'bicycle'] and traffic_mode_right in ['foot', 'bicycle']):
        prot_level = (prot_level_left + prot_level_right) / 2
    # no traffic on a side: only the other side with traffic counts.
    if traffic_mode_right == 'no' and traffic_mode_left != 'no':
        prot_level = prot_level_left
    if traffic_mode_left == 'no' and traffic_mode_right != 'no':
        prot_level = prot_level_right

    fac_protection_level = 0.9 + prot_level / 2
    # no motor vehicle traffic? Factor is only half weighted
    if traffic_mode_left not in ['motor_vehicle', 'psv', 'parking'] and traffic_mode_right not in ['motor_vehicle', 'psv', 'parking']:
        fac_protection_level /= 2
        fac_protection_level += 0.5

    return round(fac_protection_level, 3)


def function_55(
    base_index: int,
    fac_width: float,
    fac_surface: float,
    layer: QgsVectorLayer,
    feature: QgsFeature,
    id_fac_1: int,
    id_fac_2: int,
    id_fac_3: int,
    id_fac_4: int,
    way_type: str,
    is_sidepath: Optional[str],
    fac_highway: float,
    fac_maxspeed: float,
    cycleway: Optional[str],
    cycleway_both: Optional[str],
    cycleway_left: Optional[str],
    cycleway_right: Optional[str],
    traffic_mode_left: Optional[str],
    traffic_mode_right: Optional[str],
    buffer_left: Optional[float],
    buffer_right: Optional[float],
    bicycle: Optional[str],
    malus_data: str,
    bonus_data: str,
    missing_data: str,
) -> Tuple[int, str, str, str]:
    """
    Calculate index
    """

    if base_index == 0:
        return 0, bonus_data, malus_data, missing_data

    # factor 1: width and surface
    # width and surface factors are weighted, so that low values have a stronger influence on the index
    if fac_width and fac_surface:
        # fac_1 = (fac_width + fac_surface) / 2  # formula without weight factors
        weight_factor_width = max(1 - fac_width, 0) + 0.5  # max(1-x, 0) makes that only values below 1 are resulting in a stronger decrease of the index
        weight_factor_surface = max(1 - fac_surface, 0) + 0.5
        fac_1 = (weight_factor_width * fac_width + weight_factor_surface * fac_surface) / (weight_factor_width + weight_factor_surface)
    elif fac_width:
        fac_1 = fac_width
    elif fac_surface:
        fac_1 = fac_surface
    else:
        fac_1 = 1.0
    layer.changeAttributeValue(feature.id(), id_fac_1, round(fac_1, 2))

    # factor 2: highway and maxspeed
    # highway factor is weighted according to how close the bicycle traffic is to the motor traffic
    weight = vars_settings.highway_factor_weights_defaultdict[way_type]

    # if a shared path isn't a sidepath of a road, highway factor remains 1 (has no influence on the index)
    if way_type in ['shared path', 'segregated path', 'shared footway'] and is_sidepath != 'yes':
        weight = 0
    fac_2 = fac_highway * fac_maxspeed  # maxspeed and highway factor are combined in one highway factor
    fac_2 = fac_2 + ((1 - fac_2) * (1 - weight))  # factor is weighted (see above) - low weights lead to a factor closer to 1
    if not fac_2:
        fac_2 = 1.0
    layer.changeAttributeValue(feature.id(), id_fac_2, round(fac_2, 2))

    if weight >= 0.5:
        if fac_2 > 1:
            bonus_data = helper_functions.add_delimited_value(bonus_data, 'slow traffic')
        if fac_highway <= 0.7:
            malus_data = helper_functions.add_delimited_value(malus_data, 'along a major road')
        if fac_maxspeed <= 0.7:
            malus_data = helper_functions.add_delimited_value(malus_data, 'along a road with high speed limits')

    # factor 3: separation and buffer
    fac_3 = 1.0
    layer.changeAttributeValue(feature.id(), id_fac_3, round(fac_3, 2))

    # factor group 4: miscellaneous attributes can result in an other bonus or malus
    fac_4 = 1.0

    # bonus for sharrows/cycleway=shared lane markings
    if way_type in ['shared road', 'shared traffic lane']:
        if cycleway == 'shared_lane' or cycleway_both == 'shared_lane' or cycleway_left == 'shared_lane' or cycleway_right == 'shared_lane':
            fac_4 += 0.1
            bonus_data = helper_functions.add_delimited_value(bonus_data, 'shared lane markings')

    # bonus for surface colour on shared traffic ways
    if 'cycle lane' in way_type or way_type in ['crossing', 'shared bus lane', 'link', 'bicycle road'] or (way_type in ['shared path', 'segregated path'] and is_sidepath == 'yes'):
        surface_colour = feature.attribute('surface:colour')
        if surface_colour and surface_colour not in ['no', 'none', 'grey', 'gray', 'black']:
            if way_type == 'crossing':
                fac_4 += 0.15  # more bonus for colored crossings
            else:
                fac_4 += 0.05
            bonus_data = helper_functions.add_delimited_value(bonus_data, 'surface colour')

    # bonus for marked or signalled crossings
    if way_type == 'crossing':
        crossing = feature.attribute('crossing')
        if not crossing:
            missing_data = helper_functions.add_delimited_value(missing_data, 'crossing')
        crossing_markings = feature.attribute('crossing:markings')
        if not crossing_markings:
            missing_data = helper_functions.add_delimited_value(missing_data, 'crossing_markings')
        if crossing in ['traffic_signals']:
            fac_4 += 0.2
            bonus_data = helper_functions.add_delimited_value(bonus_data, 'signalled crossing')
        elif crossing in ['marked', 'zebra'] or (crossing_markings and crossing_markings != 'no'):
            fac_4 += 0.1
            bonus_data = helper_functions.add_delimited_value(bonus_data, 'marked crossing')

    # malus for missing street light
    lit = feature.attribute('lit')
    if not lit:
        missing_data = helper_functions.add_delimited_value(missing_data, 'lit')
    if lit == 'no':
        fac_4 -= 0.1
        malus_data = helper_functions.add_delimited_value(malus_data, 'no street lighting')

    # malus for cycle way along parking without buffer (danger of dooring)
    # TODO: currently no information if parking is parallel parking - for this, a parking orientation lookup on the centerline is needed for separately mapped cycle ways
    if ((traffic_mode_left == 'parking' and buffer_left and buffer_left < 1) or (traffic_mode_right == 'parking' and buffer_right and buffer_right < 1)) and ('cycle lane' in way_type or (way_type in ['cycle track', 'shared path', 'segregated path'] and is_sidepath == 'yes')):
        # malus is 0 (buffer = 1m) .. 0.2 (buffer = 0m)
        diff = 0
        if traffic_mode_left == 'parking':
            diff = abs(buffer_left - 1) / 5
        if traffic_mode_right == 'parking':
            diff = abs(buffer_right - 1) / 5
        if traffic_mode_left == 'parking' and traffic_mode_right == 'parking':
            diff = abs(((buffer_left + buffer_right) / 2) - 1) / 5
        fac_4 -= diff
        malus_data = helper_functions.add_delimited_value(malus_data, 'insufficient dooring buffer')

    # malus if bicycle is only "permissive"
    if bicycle == 'permissive':
        fac_4 -= 0.2
        malus_data = helper_functions.add_delimited_value(malus_data, 'cycling not intended')

    layer.changeAttributeValue(feature.id(), id_fac_4, round(fac_4, 2))

    index = base_index * fac_1 * fac_2 * fac_3 * fac_4

    index = max(min(100, index), 0)  # index should be between 0 and 100 in the end for pragmatic reasons
    index = int(round(index))        # index is an int

    return index, bonus_data, malus_data, missing_data


def step_05(
    layer: QgsVectorLayer,
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
    data_missing: str,
    id_data_bonus: int,
    id_data_malus: int,
    id_data_incompleteness: int,
    way_type: str,
    feature: QgsFeature,
    proc_width: Optional[float],
    proc_oneway: str,
    proc_smoothness: Optional[str],
    proc_surface: Optional[str],
    is_sidepath: Optional[str],
    cycleway: Optional[str],
    cycleway_both: Optional[str],
    cycleway_left: Optional[str],
    cycleway_right: Optional[str],
    traffic_mode_left: Optional[str],
    traffic_mode_right: Optional[str],
    buffer_left: Optional[float],
    buffer_right: Optional[float],
    bicycle: Optional[str],
    id_fac_protection_level: int,
    id_prot_level_separation_left: int,
    id_prot_level_separation_right: int,
    id_prot_level_buffer_left: int,
    id_prot_level_buffer_right: int,
    id_prot_level_left: int,
    id_prot_level_right: int,
    separation_right: Optional[str],
    separation_left: Optional[str],
) -> None:
    """
    5: Calculate index and factors
    """

    # human readable strings for significant good or bad factors
    data_bonus = ''
    data_malus = ''

    motor_vehicle_access, base_index, data_bonus = function_50(
        way_type,
        feature,
        layer,
        id_base_index,
        data_bonus,
    )

    fac_width, data_bonus, data_malus = function_51(
        way_type,
        proc_width,
        proc_oneway,
        feature,
        layer,
        motor_vehicle_access,
        id_fac_width,
        data_malus,
        data_bonus,
    )

    fac_surface, data_bonus, data_malus = function_52(
        proc_smoothness,
        proc_surface,
        feature,
        id_fac_surface,
        layer,
        data_bonus,
        data_malus,
    )

    fac_highway, fac_maxspeed = function_53(feature)

    layer.changeAttributeValue(feature.id(), id_fac_highway, fac_highway)
    layer.changeAttributeValue(feature.id(), id_fac_maxspeed, fac_maxspeed)

    # fac_protection_level = function_54(
    #     is_sidepath,
    #     traffic_mode_left,
    #     traffic_mode_right,
    #     layer,
    #     buffer_left,
    #     buffer_right,
    #     feature,
    #     id_prot_level_separation_left,
    #     id_prot_level_separation_right,
    #     id_prot_level_buffer_left,
    #     id_prot_level_buffer_right,
    #     id_prot_level_left,
    #     id_prot_level_right,
    #     separation_right,
    #     separation_left,
    # )
    #
    # layer.changeAttributeValue(feature.id(), id_fac_protection_level, fac_protection_level)

    index, data_bonus, data_malus, data_missing = function_55(
        base_index,
        fac_width,
        fac_surface,
        layer,
        feature,
        id_fac_1,
        id_fac_2,
        id_fac_3,
        id_fac_4,
        way_type,
        is_sidepath,
        fac_highway,
        fac_maxspeed,
        cycleway,
        cycleway_both,
        cycleway_left,
        cycleway_right,
        traffic_mode_left,
        traffic_mode_right,
        buffer_left,
        buffer_right,
        bicycle,
        data_malus,
        data_bonus,
        data_missing,
    )

    layer.changeAttributeValue(feature.id(), id_index, index)
    layer.changeAttributeValue(feature.id(), id_data_missing, data_missing)
    layer.changeAttributeValue(feature.id(), id_data_bonus, data_bonus)
    layer.changeAttributeValue(feature.id(), id_data_malus, data_malus)

    # derive a data completeness number
    data_incompleteness = sum(vars_settings.data_incompleteness_defaultdict[value] for value in data_missing.split(';'))

    layer.changeAttributeValue(feature.id(), id_data_incompleteness, data_incompleteness)
