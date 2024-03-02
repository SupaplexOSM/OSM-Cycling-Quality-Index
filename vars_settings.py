"""
place to put setting variables to be imported and used as constants
"""

from collections import defaultdict

from qgis import *
from qgis.core import *
from qgis.PyQt.QtCore import *

#right or left hand traffic?
#TODO: left hand traffic not supported yet in most cases
right_hand_traffic = True

#offset distance for sidepath ways
#-> set variable to 'realistic' (offset is derived from osm tags like width values)
#-> or set to a number for a static offset (meter, can also be 0, if no offset is needed, e.g. for better routing analysis)
offset_distance = 0
#offset_distance = 'realistic'

#Default oneway on cycle lanes and tracks
default_oneway_cycle_lane = 'yes' # assume that cycle lanes are oneways
default_oneway_cycle_track = 'yes' # assume that cycle tracks are oneways

#highway values with cycling prohibition
cycling_highway_prohibition_list = ['motorway', 'motorway_link', 'trunk', 'trunk_link']


default_highway_width_dict = defaultdict(lambda: 11)  # Default values for road/way width
for key, value in {
    'motorway': 15,
    'motorway_link': 6,
    'trunk': 15,
    'trunk_link': 6,
    'primary': 17,
    'primary_link': 4,
    'secondary': 15,
    'secondary_link': 4,
    'tertiary': 13,
    'tertiary_link': 4,
    'unclassified': 11,
    'residential': 11,
    'living_street': 6,
    'pedestrian': 6,
    'road': 11,
    'service': 4,
    'track': 2.5,
    'cycleway': 1.5,
    'footway': 2,
    'bridleway': 2,
    'steps': 2,
    'path': 2
}.items():
    default_highway_width_dict[key] = value

#Default values for width quality evaluations on shared roads:
default_width_traffic_lane = 3.2        # average width of a driving lane (for common motor cars)
default_width_bus_lane = 4.5            # average width of a bus/psv lane
default_width_cycle_lane = 1.4          # average width of a cycle lane
default_width_parking_parallel = 2.2    # average width of parallel parking
default_width_parking_diagonal = 4.5    # average width of diagonal parking
default_width_parking_perpendicular = 5.0 # average width of perpendicular parking

#default_width_motorcar = 2.0            # average width of a motorcar
#default_width_cyclist = 1.0             # average width of a bicycle with a cyclist
#default_distance_overtaking = 1.5       # minimum overtaking distance when overtaking a bicyclist
#default_distance_motorcar_passing = 0.8 # minimum distance between motorcars while passing each other

#Default surface values
default_cycleway_surface_tracks = 'paving_stones' # common surface on cycle tracks
default_cycleway_surface_lanes = 'asphalt' # common surface on cycle lanes
default_highway_surface_dict = { # common surface on highways
    'motorway': 'asphalt',
    'motorway_link': 'asphalt',
    'trunk': 'asphalt',
    'trunk_link': 'asphalt',
    'primary': 'asphalt',
    'primary_link': 'asphalt',
    'secondary': 'asphalt',
    'secondary_link': 'asphalt',
    'tertiary': 'asphalt',
    'tertiary_link': 'asphalt',
    'unclassified': 'asphalt',
    'residential': 'asphalt',
    'living_street': 'paving_stones',
    'pedestrian': 'paving_stones',
    'road': 'asphalt',
    'service': 'asphalt',
    'track': 'concrete',
    'cycleway': 'paving_stones',
    'footway': 'paving_stones',
    'path': 'paving_stones'
}

default_track_surface_dict = { # common surface on tracks according to tracktype
    'grade1': 'asphalt',
    'grade2': 'compacted',
    'grade3': 'unpaved',
    'grade4': 'ground',
    'grade5': 'grass'
}

surface_factor_dict = {
    'asphalt': 1,
    'paved': 1,
    'concrete': 1,
    'chipseal': 1,
    'metal': 1,
    'paving_stones': 0.7,
    'compacted': 0.7,
    'fine_gravel': 0.7,
    'paving_stones': 0.7,
    'concrete:plates': 0.7,
    'bricks': 0.7,
    'sett': 0.3,
    'cobblestone': 0.3,
    'concrete:lanes': 0.3,
    'unpaved': 0.3,
    'wood': 0.3,
    'unhewn_cobblestone': 0.2,
    'ground': 0.2,
    'dirt': 0.2,
    'earth': 0.2,
    'mud': 0.2,
    'gravel': 0.2,
    'pebblestone': 0.2,
    'grass': 0.2,
    'grass_paver': 0.2,
    'stepping_stones': 0.2,
    'woodchips': 0.2,
    'sand': 0.15,
    'rock': 0.15
}

smoothness_factor_dict = {
    'excellent': 1.1,
    'good': 1,
    'intermediate': 0.7,
    'bad': 0.3,
    'very_bad': 0.2,
    'horrible': 0.15,
    'very_horrible': 0.1,
    'impassable': 0
}

highway_factor_dict = {
    'motorway': 0.1,
    'motorway_link': 0.1,
    'trunk': 0.15,
    'trunk_link': 0.15,
    'primary': 0.35,
    'primary_link': 0.35,
    'secondary': 0.65,
    'secondary_link': 0.65,
    'tertiary': 0.85,
    'tertiary_link': 0.85,
    'unclassified': 0.95,
    'road': 0.95,
    'residential': 1,
    'living_street': 1.1
}

maxspeed_factor_dict = {
    20: 1.05,
    30: 1,
    50: 0.95,
    60: 0.85,
    70: 0.7,
    100: 0.5
}

highway_factor_dict_weights = {
    'bicycle road': 1,
    'shared road': 1,
    'shared traffic lane': 1,
    'cycle lane (advisory)': 0.7,
    'cycle lane (central)': 0.7,
    'shared bus lane': 0.7,
    'crossing': 0.7,
    'link': 0.7,
    'cycle lane (exclusive)': 0.5,
    'cycle lane (protected)': 0.2,
    'cycle track': 0.2,
    'shared path': 0.2,
    'segregated path': 0.2,
    'shared footway': 0.2,
    'track or service': 0,
    'cycle path': 0
}

separation_level_dict = {
    'no': 0,
    'none': 0,
    NULL: 0,
    'studs': 0.1,
    'yes': 0.3,
    'vertical_panel': 0.3,
    'tree_row': 0.3,
    'bump': 0.3,
    'kerb': 0.3,
    'flex_post': 0.5,
    'greenery': 0.5,
    'bollard': 0.6,
    'planter': 0.6,
    'structure': 0.7,
    'ditch': 0.8,
    'jersey_barrier': 0.9,
    'hedge': 0.9,
    'fence': 1,
    'guard_rail': 1,
    'ELSE': 0.3
}

#base index for way types (0 .. 100)
base_index_dict = {
    'cycle path': 100,
    'cycle track': 90,
    'shared path': 70,
    'segregated path': 80,
    'shared footway': 50,
    'cycle lane (advisory)': 70,
    'cycle lane (exclusive)': 80,
    'cycle lane (protected)': 90,
    'cycle lane (central)': 60,
    'shared bus lane': 65,
    'bicycle road': 70,
    'shared road': 60,
    'shared traffic lane': 60,
    'track or service': 65,
    'link': 60,
    'crossing': 60
}

#base index for roads with restricted motor vehicle access
motor_vehicle_access_index_dict = {
    'no': 100,
    'agricultural': 90,
    'forestry': 90,
    'agricultural;forestry': 90,
    'forestry;agricultural': 90,
    'private': 80,
    'customers': 80,
    'delivery': 80,
    'permit': 80,
    'destination': 70
}

#list of traffic signs, that make a way or path mandatory to use for cyclists
#this lists are for DE:; adjust it if needed
mandatory_traffic_sign_list = ['237', '240', '241']
not_mandatory_traffic_sign_list = ['none', '1022']

#output/save options
crs_from = "EPSG:4326"
crs_to = "EPSG:25833"
transform_context = QgsCoordinateTransformContext()
transform_context.addCoordinateOperation(QgsCoordinateReferenceSystem(crs_from), QgsCoordinateReferenceSystem(crs_to), "")
coordinateTransformContext=QgsProject.instance().transformContext()
save_options = QgsVectorFileWriter.SaveVectorOptions()
save_options.driverName = 'GeoJSON'
save_options.ct = QgsCoordinateTransform(QgsCoordinateReferenceSystem(crs_from), QgsCoordinateReferenceSystem(crs_to), coordinateTransformContext)

#list of attributes that are retained in the saved file
retained_attributes_list = [
    'id',
    'name',
    'way_type',
    'side',
    'offset',
    'proc_width',
    'proc_surface',
    'proc_smoothness',
    'proc_oneway',
    'proc_sidepath',
    'proc_highway',
    'proc_maxspeed',
    'proc_traffic_mode_left',
    'proc_traffic_mode_right',
    'proc_separation_left',
    'proc_separation_right',
    'proc_buffer_left',
    'proc_buffer_right',
    'proc_mandatory',
    'proc_traffic_sign',
    'fac_width',
    'fac_surface',
    'fac_highway',
    'fac_maxspeed',
#    'fac_protection_level',
#    'prot_level_separation_left',
#    'prot_level_separation_right',
#    'prot_level_buffer_left',
#    'prot_level_buffer_right',
#    'prot_level_left',
#    'prot_level_right',
    'base_index',
    'fac_1',
    'fac_2',
    'fac_3',
    'fac_4',
    'index',
    'data_incompleteness',
    'data_missing',
    'data_bonus',
    'data_malus'
]

#missing data values and how much they wight for a data (in)completeness number
data_incompleteness_dict = {
    'width': 25,
    'surface': 30,
    'smoothness': 10,
    'width:lanes': 10,
    'parking': 25,
    'crossing': 10,
    'crossing_markings': 10,
    'lit': 15
}
