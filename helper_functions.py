"""
functions used in multiple files to be imported
"""

from typing import List, Optional

from qgis.core import NULL, QgsFeature, QgsVariantUtils  # type: ignore
from qgis.PyQt.QtCore import QVariant  # type: ignore

debug_warning_counter__derive_attribute = 0
debug_warning_counter__cast_to_float = 0
debug_warning_counter_max_val = 5


def derive_attribute(feature: QgsFeature, attribute_name: str, way_type: str, side: str, vartype: type) -> None | int | float | str:
    """
    derive cycleway and sidewalk attributes mapped on the centerline for transferring them to separate ways
    """

    attribute = feature.attribute(f"{way_type}:{side}:{attribute_name}")

    if not attribute:
        attribute = feature.attribute(f"{way_type}:{attribute_name}")

    if attribute is None:
        return None

    if QgsVariantUtils.isNull(attribute):
        return None

    try:
        if vartype is int:
            return int(attribute)
        if vartype is float:
            return float(attribute)
        if vartype is str:
            return str(attribute)
        raise NotImplementedError(f"derive_attribute: vartype {vartype} not recognized")
    except (TypeError, ValueError) as e:
        global debug_warning_counter__derive_attribute
        if debug_warning_counter__derive_attribute < 5:
            print(f"derive_attribute: error, trying to cast type {type(attribute)} = {attribute} to {vartype}! ({e})")
            debug_warning_counter__derive_attribute += 1
            if debug_warning_counter__derive_attribute >= 5:
                print("derive_attribute: this was the last warning, future warnings will be muted!")
        return None


def derive_separation(feature: QgsFeature, traffic_mode: str) -> Optional[str]:
    """
    derive separation on the side of a specific traffic mode (e.g. foot traffic usually on the right side)
    """

    separation = None
    separation_left: Optional[str] = feature.attribute('separation:left')
    separation_right: Optional[str] = feature.attribute('separation:right')
    traffic_mode_left: Optional[str] = feature.attribute('traffic_mode:left')
    traffic_mode_right: Optional[str] = feature.attribute('traffic_mode:right')

    # default for the right side: adjacent foot traffic
    if traffic_mode == 'foot':
        if traffic_mode_left == 'foot':
            separation = separation_left
        if not traffic_mode_right or traffic_mode_right == 'foot':
            separation = separation_right

            # TODO: Wenn beidseitig gleicher traffic_mode, dann schwächere separation übergeben

    # default for the left side: adjacent motor vehicle traffic
    if traffic_mode == 'motor_vehicle':
        if traffic_mode_right in ['motor_vehicle', 'parking', 'psv']:
            separation = separation_right
        if not traffic_mode_left or traffic_mode_left in ['motor_vehicle', 'parking', 'psv']:
            separation = separation_left

    return separation


def get_access(feature: QgsFeature, access_key: str) -> Optional[str]:
    """
    interpret access tags of a feature to get the access value for a specific traffic mode
    """

    access_dict = {
        'foot': ['access'],
        'vehicle': ['access'],
        'bicycle': ['vehicle', 'access'],
        'motor_vehicle': ['vehicle', 'access'],
        'motorcar': ['motor_vehicle', 'vehicle', 'access'],
        'hgv': ['motor_vehicle', 'vehicle', 'access'],
        'psv': ['motor_vehicle', 'vehicle', 'access'],
        'bus': ['psv', 'motor_vehicle', 'vehicle', 'access']
    }

    access_value = None
    if feature.fields().indexOf(access_key) != -1:
        access_value = feature.attribute(access_key)

    if not access_value and access_key in access_dict:
        for i in range(len(access_dict[access_key])):
            if not access_value and feature.fields().indexOf(access_dict[access_key][i]) != -1:
                access_value = feature.attribute(access_dict[access_key][i])

    return access_value


def cast_to_float(value: QVariant | int | float) -> Optional[float]:
    """
    return a value as a float
    """

    if QgsVariantUtils.isNull(value):
        return NULL  # type: ignore  # TODO: change to None, if possible

    if value == "walk":
        return NULL  # type: ignore  # TODO: change to None, if possible

    if value == "no":
        return None

    if value == "yes":
        return None

    if value == "":
        return None

    # if type(value) is str:
    #     raise ValueError(f"{value=} of type str is probably not converttile to float?")

    try:
        return float(value)
    except (TypeError, ValueError) as e:
        global debug_warning_counter__cast_to_float
        if debug_warning_counter__cast_to_float < 5:
            print(f"cast_to_float: error, trying to cast type {type(value)} = {value} to float! ({e})")
            debug_warning_counter__cast_to_float += 1
            if debug_warning_counter__cast_to_float >= 5:
                print("cast_to_float: this was the last warning, future warnings will be muted!")
        return NULL  # type: ignore  # TODO: change to None, if possible


def get_weakest_surface_value(values: List[str]) -> Optional[str]:
    """
    from a list of surface values, choose the weakest one
    """

    # surface values in descending order
    surface_value_list = [
        'asphalt',
        'paved',
        'concrete',
        'chipseal',
        'metal',
        'paving_stones',
        'compacted',
        'fine_gravel',
        'paving_stones',
        'concrete:plates',
        'bricks',
        'sett',
        'cobblestone',
        'concrete:lanes',
        'unpaved',
        'wood',
        'unhewn_cobblestone',
        'ground',
        'dirt',
        'earth',
        'mud',
        'gravel',
        'pebblestone',
        'grass',
        'grass_paver',
        'stepping_stones',
        'woodchips',
        'sand',
        'rock'
    ]

    return_value = None
    for value in values:
        if value in surface_value_list:
            if surface_value_list.index(value) > surface_value_list.index(value):
                return_value = value
    return return_value


def add_delimited_value(var: str, value: str) -> str:
    """
    add a value to a delimited string
    """

    if var:
        var += ';'
    return var + value
