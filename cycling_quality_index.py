#---------------------------------------------------------------------------#
#   Cycling Quality Index                                                   #
#   --------------------------------------------------                      #
#   Script for processing OSM data to analyse the cycling quality of ways.  #
#   Download OSM data input from https://overpass-turbo.eu/s/1G3t,          #
#   save it at data/way_import.geojson and run the script.                  #
#                                                                           #
#   > version/date: 2024-01-24                                              #
#---------------------------------------------------------------------------#

#TODO: buffer und separation-Faktor implementieren
#TODO: Mali und Boni für sonstige Attribute implementieren

#TODO: "use sidepath" und evtl. andere Verweiskategorien differenzieren nach shared road und shared traffic lane (z.B. Sonnenallee neben Busspur)

#TODO: highway-Klassenfaktor neu aufstellen: Hauptstraßen per Default stark abwerten - Faktor haut voll rein bei shared road/lane, aber zählt nur teilweise bei lanes (advisory: stärkerer Einfluss, exclusive: schwächerer Einfluss, protected: eher schwacher Einfluss) und tracks/sidepath (schwacher Einfluss)

#TODO: tracktype nutzen
#TODO: Anwendbarkeit im ländlichen Raum testen

from os.path import exists
import os, processing, math, time

#-------------------------------------------------#
#   V a r i a b l e s   a n d   S e t t i n g s   #
#-------------------------------------------------#

#project directory
from console.console import _console
project_dir = os.path.dirname(_console.console.tabEditorWidget.currentWidget().path) + '/'
dir_input = project_dir + 'data/way_import.geojson'
dir_output = project_dir + 'data/cycling_quality_index.geojson'

#Default values for road/way width
default_highway_width_fallback = 11
default_highway_width_dict = {
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
}

#Default values for width quality evaluations on shared roads:
default_width_traffic_lane = 3         # average width of a driving lane (for common motor cars)
default_width_bus_lane = 4.5            # average width of a bus/psv lane
default_width_parking_parallel = 2.2    # average width of parallel parking
default_width_parking_diagonal = 4.5    # average width of diagonal parking
default_width_parking_perpendicular = 5.0 # average width of perpendicular parking
default_width_motorcar = 2.0            # average width of a motorcar
default_width_cyclist = 1.0             # average width of a bicycle with a cyclist
default_distance_overtaking = 1.5       # minimum overtaking distance when overtaking a bicyclist
default_distance_motorcar_passing = 0.8 # minimum distance between motorcars while passing each other

#Default oneway on cycle lanes
default_oneway_cycle_lane = 'yes' # assume that cycle lanes are oneways
default_oneway_cycle_track = 'yes' # assume that cycle tracks are oneways

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

#TODO+ currently not in use
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
    'motorway': 0.6,
    'motorway_link': 0.6,
    'trunk': 0.7,
    'trunk_link': 0.7,
    'primary': 0.8,
    'primary_link': 0.8,
    'secondary': 0.9,
    'secondary_link': 0.9,
    'tertiary': 0.95,
    'tertiary_link': 0.95
}

maxspeed_factor_dict = {
    20: 1.2,
    30: 1,
    50: 0.95,
    60: 0.85,
    70: 0.7,
    100: 0.5
}

#base width values for width factor calculation on shared roads/lanes
#(roughly explained: The road/lane width available beyond this value defines the width available for cycle traffic)
base_width_shared = 3
base_width_bus_lanes = 2.5

#base index for way types (0 .. 100)
base_index_dict = {
    'cycle path': 100,
    'cycle track': 90,
    'shared path': 60,
    'segregated path': 80,
    'shared footway': 30,
    'cycle lane (advisory)': 70,
    'cycle lane (exclusive)': 80,
    'cycle lane (protected)': 90,
    'cycle lane (central)': 60,
    'shared bus lane': 60,
    'bicycle road': NULL, #according to motor_vehicle access, see below
    'shared road': NULL, #according to highway class, see below
    'shared traffic lane': NULL, #according to highway class, see below
    'track or service': 40,
    'use sidepath': 40,
    'optional sidepath': 40,
    'cycle prohibition': 0,
    'link': NULL, #links aren't rated
    'crossing': 40 #TODO better individual ratings crossings according to it's specific attributes (width, surface, markings, colour, highway class...)
}

#base index for bicycle roads, according to motor_vehicle access
base_index_bicycle_road_dict = {
    'no': 100,
    'destination': 70,
    'yes': 40
}

#base index for shared roads and lanes, according to highway class
base_index_shared_road_dict = {
    'primary': 20,
    'primary_link': 20,
    'secondary': 35,
    'secondary_link': 35,
    'tertiary': 50,
    'tertiary_link': 50,
    'unclassified': 65,
    'residential': 65,
    'road': 65,
    'living_street': 80
}

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
    'index',
    'base_index',
    'fac_width',
    'fac_surface',
    'fac_separation',
    'fac_highway',
    'fac_maxspeed',
    'data_completeness',
    'data_missing'
]

#missing data values and how much they wight for a data completeness number
data_completeness_dict = {
    'width': 25,
    'surface': 30,
    'smoothness': 10,
    'width:lanes': 10,
    'parking': 25
}

#-------------------------------
#   V a r i a b l e s   E n d   
#-------------------------------



#derive cycleway and sidewalk attributes mapped on the centerline for transfering them to separate ways
def deriveAttribute(feature, attribute_name, type, side, vartype):
    attribute = NULL
    attribute = feature.attribute(str(type) + ':' + str(side) + ':' + str(attribute_name))
    if not attribute:
        attribute = feature.attribute(str(type) + ':both:' + str(attribute_name))
    if not attribute:
        attribute = feature.attribute(str(type) + ':' + str(attribute_name))
    if attribute != NULL:
        try:
            if vartype == 'int':
                attribute = int(attribute)
            if vartype == 'float':
                attribute = float(attribute)
            if vartype == 'str':
                attribute = str(attribute)
        except:
            attribute = NULL
    return(attribute)



#derive separation on the side of a specific traffic mode (e.g. foot traffic usually on the right side)
def deriveSeparation(feature, traffic_mode):
    separation = NULL
    separation_left = feature.attribute('separation:left')
    separation_right = feature.attribute('separation:right')
    traffic_mode_left = feature.attribute('traffic_mode:left')
    traffic_mode_right = feature.attribute('traffic_mode:right')

    #default for the right side: adjacent foot traffic
    if traffic_mode == 'foot':
        if traffic_mode_left == 'foot':
            separation = separation_left
        if not traffic_mode_right or traffic_mode_right == 'foot':
            separation = separation_right

            #TODO: Wenn beidseitig gleicher traffic_mode, dann schwächere separation übergeben
            
    #default for the left side: adjacent motor vehicle traffic
    if traffic_mode == 'motor_vehicle':
        if traffic_mode_right in ['motor_vehicle', 'parking', 'psv']:
            separation = separation_right
        if not traffic_mode_left or traffic_mode_left in ['motor_vehicle', 'parking', 'psv']:
            separation = separation_left

    return(separation)



#interpret access tags of a feature to get the access value for a specific traffic mode
def getAccess(feature, access_key):
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
    access_value = NULL
    if feature.fields().indexOf(access_key) != -1:
        access_value = feature.attribute(access_key)
    if not access_value and access_key in access_dict:
        for i in range(len(access_dict[access_key])):
            if not access_value and feature.fields().indexOf(access_dict[access_key][i]) != -1:
                access_value = feature.attribute(access_dict[access_key][i])
    return(access_value)



#return a value as a float
def getNumber(value):
    if value != NULL:
        try:
            value = float(value)
        except:
            value = NULL
    return(value)



#if there is a specific delimiter character in a string (like ";" or "|"), return a list of single, non-delimited values (e.g. "asphalt;paving_stones" -> ["asphalt", "paving_stones"])
def getDelimitedValues(value_string, deli_char, var_type):
    delimiters = [-1]
    for pos, char in enumerate(value_string):
        if(char == deli_char):
            delimiters.append(pos)
    #Start- (oben) und Endpunkte des strings ergänzen zur einfacheren Verarbeitung
    delimiters.append(len(value_string))

    #einzelne Abbiegespuren in Array speichern und zurückgeben
    value_array = []
    for i in range(len(delimiters) - 1):
        value = value_string[delimiters[i] + 1:delimiters[i + 1]]
        if var_type == 'float' or var_type == 'int':
            if value == '' or value == NULL:
                value = 0
            if var_type == 'float':
                value_array.append(float(value))
            if var_type == 'int':
                value_array.append(int(value))
        else:
            value_array.append(value)
    return(value_array)



#from a list of surface values, choose the weakest one
def getWeakestSurfaceValue(value_list):
    #surface values in descent order
    surface_value_list = ['asphalt', 'paved', 'concrete', 'chipseal', 'metal', 'paving_stones', 'compacted', 'fine_gravel', 'paving_stones', 'concrete:plates', 'bricks', 'sett', 'cobblestone', 'concrete:lanes', 'unpaved', 'wood', 'unhewn_cobblestone', 'ground', 'dirt', 'earth', 'mud', 'gravel', 'pebblestone', 'grass', 'grass_paver', 'stepping_stones', 'woodchips', 'sand', 'rock']

    value = NULL
    for i in range(len(value_list)):
        if value_list[i] in surface_value_list:
            if not value:
                value = value_list[i]
            else:
                if surface_value_list.index(value_list[i]) > surface_value_list.index(value):
                    value = value_list[i]
    return(value)



#add a value to a delimited string
def addDelimitedValue(var, value):
    if var:
        var += ';'
    var += value
    return(var)



#--------------------------------
#      S c r i p t   S t a r t
#--------------------------------
print(time.strftime('%H:%M:%S', time.localtime()), 'Start processing:')

print(time.strftime('%H:%M:%S', time.localtime()), 'Read data...')
if not exists(dir_input):
    print(time.strftime('%H:%M:%S', time.localtime()), '[!] Error: No valid input file at "' + dir_input + '".')
else:
    layer_way_input = QgsVectorLayer(dir_input + '|geometrytype=LineString', 'way input', 'ogr')

    print(time.strftime('%H:%M:%S', time.localtime()), 'Reproject data...')
    layer = processing.run('native:reprojectlayer', { 'INPUT' : layer_way_input, 'TARGET_CRS' : QgsCoordinateReferenceSystem(crs_to), 'OUTPUT': 'memory:'})['OUTPUT']

    #prepare attributes
    print(time.strftime('%H:%M:%S', time.localtime()), 'Prepare data...')
    #delete unneeded attributes
    #list of attributes that are used for cycling quality analysis
    attributes_list = [
    'id',
    'layer',
    'highway',
    'name',
    'oneway',
    'oneway:bicycle',
    'segregated',
    'is_sidepath',
    'is_sidepath:of',

    'access',
    'vehicle',
    'motor_vehicle',
    'bicycle',
    'foot',

    'bicycle_road',
    'footway',
    'path',
    'bridleway',
    'informal',

    'maxspeed',
    'lit',
    'incline',

    'surface',
    'surface:bicycle',
    'smoothness',
    'smoothness:bicycle',
    'lanes',
    'width',
    'width:carriageway',
    'width:effective',
    'width:lanes',
    'width:lanes:forward',
    'width:lanes:backward',
    'lane_markings',
    'separation',
    'separation:both',
    'separation:left',
    'separation:right',
    'buffer',
    'buffer:both',
    'buffer:left',
    'buffer:right',
    'traffic_mode:both',
    'traffic_mode:left',
    'traffic_mode:right',
    'surface:colour',
    'traffic_sign',

    'parking:both',
    'parking:left',
    'parking:right',
    'parking:both:orientation',
    'parking:left:orientation',
    'parking:right:orientation',
    'parking:both:width',
    'parking:left:width',
    'parking:right:width',

    'sidewalk:bicycle',
    'sidewalk:both:bicycle',
    'sidewalk:left:bicycle',
    'sidewalk:right:bicycle',
    'sidewalk:surface',
    'sidewalk:both:surface',
    'sidewalk:left:surface',
    'sidewalk:right:surface',
    'sidewalk:smoothness',
    'sidewalk:both:smoothness',
    'sidewalk:left:smoothness',
    'sidewalk:right:smoothness',
    'sidewalk:width',
    'sidewalk:both:width',
    'sidewalk:left:width',
    'sidewalk:right:width',
    'sidewalk:oneway',
    'sidewalk:both:oneway',
    'sidewalk:left:oneway',
    'sidewalk:right:oneway',
    'sidewalk:oneway:bicycle',
    'sidewalk:both:oneway:bicycle',
    'sidewalk:left:oneway:bicycle',
    'sidewalk:right:oneway:bicycle',

    'footway:width',

    'cycleway',
    'cycleway:both',
    'cycleway:left',
    'cycleway:right',
    'cycleway:lane',
    'cycleway:both:lane',
    'cycleway:left:lane',
    'cycleway:right:lane',
    'cycleway:surface',
    'cycleway:both:surface',
    'cycleway:left:surface',
    'cycleway:right:surface',
    'cycleway:smoothness',
    'cycleway:both:smoothness',
    'cycleway:left:smoothness',
    'cycleway:right:smoothness',
    'cycleway:width',
    'cycleway:both:width',
    'cycleway:left:width',
    'cycleway:right:width',
    'cycleway:oneway',
    'cycleway:both:oneway',
    'cycleway:left:oneway',
    'cycleway:right:oneway',
    'cycleway:oneway:bicycle',
    'cycleway:both:oneway:bicycle',
    'cycleway:left:oneway:bicycle',
    'cycleway:right:oneway:bicycle',
    'cycleway:segregated',
    'cycleway:both:segregated',
    'cycleway:left:segregated',
    'cycleway:right:segregated',
    'cycleway:foot',
    'cycleway:both:foot',
    'cycleway:left:foot',
    'cycleway:right:foot',
    'cycleway:separation',
    'cycleway:separation:left',
    'cycleway:separation:right',
    'cycleway:separation:both',
    'cycleway:both:separation',
    'cycleway:both:separation:left',
    'cycleway:both:separation:right',
    'cycleway:both:separation:both',
    'cycleway:right:separation',
    'cycleway:right:separation:left',
    'cycleway:right:separation:right',
    'cycleway:right:separation:both',
    'cycleway:left:separation',
    'cycleway:left:separation:left',
    'cycleway:left:separation:right',
    'cycleway:left:separation:both',
    'cycleway:buffer',
    'cycleway:buffer:left',
    'cycleway:buffer:right',
    'cycleway:buffer:both',
    'cycleway:both:buffer',
    'cycleway:both:buffer:left',
    'cycleway:both:buffer:right',
    'cycleway:both:buffer:both',
    'cycleway:right:buffer',
    'cycleway:right:buffer:left',
    'cycleway:right:buffer:right',
    'cycleway:right:buffer:both',
    'cycleway:left:buffer',
    'cycleway:left:buffer:left',
    'cycleway:left:buffer:right',
    'cycleway:left:buffer:both',
    'cycleway:traffic_mode:left',
    'cycleway:traffic_mode:right',
    'cycleway:traffic_mode:both',
    'cycleway:both:traffic_mode:left',
    'cycleway:both:traffic_mode:right',
    'cycleway:both:traffic_mode:both',
    'cycleway:left:traffic_mode:left',
    'cycleway:left:traffic_mode:right',
    'cycleway:left:traffic_mode:both',
    'cycleway:right:traffic_mode:left',
    'cycleway:right:traffic_mode:right',
    'cycleway:right:traffic_mode:both',
    'cycleway:surface:colour',
    'cycleway:both:surface:colour',
    'cycleway:right:surface:colour',
    'cycleway:left:surface:colour,'
    'cycleway:traffic_sign',
    'cycleway:both:traffic_sign',
    'cycleway:right:traffic_sign',
    'cycleway:left:traffic_sign',
    
    'cycleway:lanes',
    'cycleway:lanes:forward',
    'cycleway:lanes:backward'
    ]
    layer = processing.run('native:retainfields', { 'INPUT' : layer, 'FIELDS' : attributes_list, 'OUTPUT': 'memory:'})['OUTPUT']

    #list of new attributes, important for calculating cycling quality index
    new_attributes_dict = {
    'way_type': 'String',
    'offset': 'Double',
    'offset_cycleway_left': 'Double',
    'offset_cycleway_right': 'Double',
    'offset_sidewalk_left': 'Double',
    'offset_sidewalk_right': 'Double',
    'type': 'String',
    'side': 'String',
    'proc_width': 'Double',
    'proc_surface': 'String',
    'proc_smoothness': 'String',
    'proc_oneway': 'String',
    'proc_sidepath': 'String',
    'proc_highway': 'String',
    'proc_maxspeed': 'Int',
    'index': 'Int',
    'base_index': 'Int',
    'fac_width': 'Double',
    'fac_surface': 'Double',
    'fac_separation': 'Double',
    'fac_highway': 'Double',
    'fac_maxspeed': 'Double',
    'data_completeness': 'Double',
    'data_missing': 'String'
    }
    for attr in list(new_attributes_dict.keys()):
        attributes_list.append(attr)

    #make sure all attributes are existing in the table to prevent errors when asking for a missing one
    with edit(layer):
        for attr in attributes_list:
            if layer.fields().indexOf(attr) == -1:
                if attr in new_attributes_dict:
                    if new_attributes_dict[attr] == 'Double':
                        layer.dataProvider().addAttributes([QgsField(attr, QVariant.Double)])
                    elif new_attributes_dict[attr] == 'Int':
                        layer.dataProvider().addAttributes([QgsField(attr, QVariant.Int)])
                    else:
                        layer.dataProvider().addAttributes([QgsField(attr, QVariant.String)])
                else:
                    layer.dataProvider().addAttributes([QgsField(attr, QVariant.String)])
        layer.updateFields()

    id_way_type = layer.fields().indexOf('way_type')
    id_offset = layer.fields().indexOf('offset')
    id_offset_cycleway_left = layer.fields().indexOf('offset_cycleway_left')
    id_offset_cycleway_right = layer.fields().indexOf('offset_cycleway_right')
    id_offset_sidewalk_left = layer.fields().indexOf('offset_sidewalk_left')
    id_offset_sidewalk_right = layer.fields().indexOf('offset_sidewalk_right')
    id_type = layer.fields().indexOf('type')
    id_side = layer.fields().indexOf('side')
    id_proc_width = layer.fields().indexOf('proc_width')
    id_proc_surface = layer.fields().indexOf('proc_surface')
    id_proc_smoothness = layer.fields().indexOf('proc_smoothness')
    id_proc_oneway = layer.fields().indexOf('proc_oneway')
    id_proc_sidepath = layer.fields().indexOf('proc_sidepath')
    id_proc_highway = layer.fields().indexOf('proc_highway')
    id_proc_maxspeed = layer.fields().indexOf('proc_maxspeed')
    id_index = layer.fields().indexOf('index')
    id_base_index = layer.fields().indexOf('base_index')
    id_fac_width = layer.fields().indexOf('fac_width')
    id_fac_surface = layer.fields().indexOf('fac_surface')
    id_fac_separation = layer.fields().indexOf('fac_separation')
    id_fac_highway = layer.fields().indexOf('fac_highway')
    id_fac_maxspeed = layer.fields().indexOf('fac_maxspeed')
    id_data_missing = layer.fields().indexOf('data_missing')
    id_data_completeness = layer.fields().indexOf('data_completeness')

    QgsProject.instance().addMapLayer(layer, False)



    #---------------------------------------------------------------#
    #1: Check paths whether they are sidepath (a path along a road) #
    #---------------------------------------------------------------#

    sidepath_buffer_size = 22 #check for adjacent roads for ... meters around a way
    sidepath_buffer_distance = 100 #do checks for adjacent roads every ... meters along a way

    print(time.strftime('%H:%M:%S', time.localtime()), 'Sidepath check...')
    print(time.strftime('%H:%M:%S', time.localtime()), '   Create way layers...')
    #create path layer: check all path, footways or cycleways for their sidepath status
    layer_path = processing.run('qgis:extractbyexpression', { 'INPUT' : layer, 'EXPRESSION' : '"highway" IS \'cycleway\' OR "highway" IS \'footway\' OR "highway" IS \'path\' OR "highway" IS \'bridleway\' OR "highway" IS \'steps\'', 'OUTPUT': 'memory:'})['OUTPUT']
    #create road layer: extract all other highway types (except tracks)
    layer_roads = processing.run('qgis:extractbyexpression', { 'INPUT' : layer, 'EXPRESSION' : '"highway" IS NOT \'cycleway\' AND "highway" IS NOT \'footway\' AND "highway" IS NOT \'path\' AND "highway" IS NOT \'bridleway\' AND "highway" IS NOT \'steps\' AND "highway" IS NOT \'track\'', 'OUTPUT': 'memory:'})['OUTPUT']

    print(time.strftime('%H:%M:%S', time.localtime()), '   Create check points...')
    #create "check points" along each segment (to check for near/parallel highways at every checkpoint)
    layer_path_points = processing.run('native:pointsalonglines', {'INPUT' : layer_path, 'DISTANCE' : sidepath_buffer_distance, 'OUTPUT': 'memory:'})['OUTPUT']
    layer_path_points_endpoints = processing.run('native:extractspecificvertices', { 'INPUT' : layer_path, 'VERTICES' : '-1', 'OUTPUT': 'memory:'})['OUTPUT']
    layer_path_points = processing.run('native:mergevectorlayers', { 'LAYERS' : [layer_path_points, layer_path_points_endpoints], 'OUTPUT': 'memory:'})['OUTPUT']
    #create "check buffers" (to check for near/parallel highways with in the given distance)
    layer_path_points_buffers = processing.run('native:buffer', { 'INPUT' : layer_path_points, 'DISTANCE' : sidepath_buffer_size, 'OUTPUT': 'memory:'})['OUTPUT']
    QgsProject.instance().addMapLayer(layer_path_points_buffers, False)

    print(time.strftime('%H:%M:%S', time.localtime()), '   Check for adjacent roads...')

    #for all check points: Save nearby road id's, names and highway classes in a dict
    sidepath_dict = {}
    for buffer in layer_path_points_buffers.getFeatures():
        buffer_id = buffer.attribute('id')
        buffer_layer = buffer.attribute('layer')
        if not buffer_id in sidepath_dict:
            sidepath_dict[buffer_id] = {}
            sidepath_dict[buffer_id]['checks'] = 1
            sidepath_dict[buffer_id]['id'] = {}
            sidepath_dict[buffer_id]['highway'] = {}
            sidepath_dict[buffer_id]['name'] = {}
            sidepath_dict[buffer_id]['maxspeed'] = {}
        else:
            sidepath_dict[buffer_id]['checks'] += 1
        layer_path_points_buffers.removeSelection()
        layer_path_points_buffers.select(buffer.id())
        processing.run('native:selectbylocation', {'INPUT' : layer_roads, 'INTERSECT' : QgsProcessingFeatureSourceDefinition(layer_path_points_buffers.id(), selectedFeaturesOnly=True), 'METHOD' : 0, 'PREDICATE' : [0,6]})

        id_list = []
        highway_list = []
        name_list = []
        maxspeed_dict = {}
        for road in layer_roads.selectedFeatures():
            road_layer = road.attribute('layer')
            if buffer_layer != road_layer:
                continue #only consider geometries in the same layer
            road_id = road.attribute('id')
            road_highway = road.attribute('highway')
            road_name = road.attribute('name')
            road_maxspeed = getNumber(road.attribute('maxspeed'))
            if not road_id in id_list:
                id_list.append(road_id)
            if not road_highway in highway_list:
                highway_list.append(road_highway)
            if not road_highway in maxspeed_dict or maxspeed_dict[road_highway] < road_maxspeed:
                maxspeed_dict[road_highway] = road_maxspeed
            if not road_name in name_list:
                name_list.append(road_name)
        for road_id in id_list:
            if road_id in sidepath_dict[buffer_id]['id']:
                sidepath_dict[buffer_id]['id'][road_id] += 1
            else:
                sidepath_dict[buffer_id]['id'][road_id] = 1
        for road_highway in highway_list:
            if road_highway in sidepath_dict[buffer_id]['highway']:
                sidepath_dict[buffer_id]['highway'][road_highway] += 1
            else:
                sidepath_dict[buffer_id]['highway'][road_highway] = 1
        for road_name in name_list:
            if road_name in sidepath_dict[buffer_id]['name']:
                sidepath_dict[buffer_id]['name'][road_name] += 1
            else:
                sidepath_dict[buffer_id]['name'][road_name] = 1

        for highway in maxspeed_dict.keys():
            if not highway in sidepath_dict[buffer_id]['maxspeed'] or sidepath_dict[buffer_id]['maxspeed'][highway] < maxspeed_dict[highway]:
                sidepath_dict[buffer_id]['maxspeed'][highway] = maxspeed_dict[highway]

    highway_class_list = ['motorway', 'motorway_link', 'trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link', 'tertiary', 'tertiary_link', 'unclassified', 'residential', 'road', 'living_street', 'service', 'pedestrian', NULL]

    #a path is considered a sidepath if at least two thirds of its check points are found to be close to road segments with the same OSM ID, highway class or street name
    with edit(layer):
        for feature in layer.getFeatures():
            hw = feature.attribute('highway')
            if not hw in ['cycleway', 'footway', 'path', 'bridleway', 'steps']:
                continue
            id = feature.attribute('id')
            is_sidepath = feature.attribute('is_sidepath')
            if feature.attribute('footway') == 'sidewalk':
                is_sidepath = 'yes'
            is_sidepath_of = feature.attribute('is_sidepath:of')
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

            #derive the highway class of the associated road
            if not is_sidepath_of and is_sidepath == 'yes':
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



    #-------------------------------------------------------------------------------#
    #2: Split and shift attributes/geometries for sidepath mapped on the centerline #
    #-------------------------------------------------------------------------------#

    print(time.strftime('%H:%M:%S', time.localtime()), 'Split line bundles...')
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

            #use road width as offset for the new geometry
            width = getNumber(feature.attribute('width'))

            #use default road width if width isn't specified
            if not width:
                if highway in default_highway_width_dict:
                    width = default_highway_width_dict[highway]
                else:
                    width = default_highway_width_fallback

            #offset for cycleways
            if highway != 'cycleway':
                #offset for left cycleways
                if cycleway in ['lane', 'track', 'share_busway'] or cycleway_both in ['lane', 'track', 'share_busway'] or cycleway_left in ['lane', 'track', 'share_busway']:
                    offset_cycleway_left = width / 2
                    layer.changeAttributeValue(feature.id(), id_offset_cycleway_left, offset_cycleway_left)

                #offset for right cycleways
                if cycleway in ['lane', 'track', 'share_busway'] or cycleway_both in ['lane', 'track', 'share_busway'] or cycleway_right in ['lane', 'track', 'share_busway']:
                    offset_cycleway_right = width / 2
                    layer.changeAttributeValue(feature.id(), id_offset_cycleway_right, offset_cycleway_right)

            #offset for shared footways
            #offset for left sidewalks
            if sidewalk_bicycle in ['yes', 'designated', 'permissive'] or sidewalk_both_bicycle in ['yes', 'designated', 'permissive'] or sidewalk_left_bicycle in ['yes', 'designated', 'permissive']:
                #use larger offset than for cycleways to get nearby, parallel lines in case both (cycleway and sidewalk) exist
                offset_sidewalk_left = width / 2 + 2
                layer.changeAttributeValue(feature.id(), id_offset_sidewalk_left, offset_sidewalk_left)

            #offset for right sidewalks
            if sidewalk_bicycle in ['yes', 'designated', 'permissive'] or sidewalk_both_bicycle in ['yes', 'designated', 'permissive'] or sidewalk_right_bicycle in ['yes', 'designated', 'permissive']:
                offset_sidewalk_right = width / 2 + 2
                layer.changeAttributeValue(feature.id(), id_offset_sidewalk_right, offset_sidewalk_right)

        processing.run('qgis:selectbyexpression', {'INPUT' : layer, 'EXPRESSION' : '\"offset_cycleway_left\" IS NOT NULL'})
        offset_cycleway_left_layer = processing.run('native:offsetline', {'INPUT': QgsProcessingFeatureSourceDefinition(layer.id(), selectedFeaturesOnly=True), 'DISTANCE': QgsProperty.fromExpression('"offset_cycleway_left"'), 'OUTPUT': 'memory:'})['OUTPUT']
        processing.run('qgis:selectbyexpression', {'INPUT' : layer, 'EXPRESSION' : '\"offset_cycleway_right\" IS NOT NULL'})
        offset_cycleway_right_layer = processing.run('native:offsetline', {'INPUT': QgsProcessingFeatureSourceDefinition(layer.id(), selectedFeaturesOnly=True), 'DISTANCE': QgsProperty.fromExpression('-"offset_cycleway_right"'), 'OUTPUT': 'memory:'})['OUTPUT']
        processing.run('qgis:selectbyexpression', {'INPUT' : layer, 'EXPRESSION' : '\"offset_sidewalk_left\" IS NOT NULL'})
        offset_sidewalk_left_layer = processing.run('native:offsetline', {'INPUT': QgsProcessingFeatureSourceDefinition(layer.id(), selectedFeaturesOnly=True), 'DISTANCE': QgsProperty.fromExpression('"offset_sidewalk_left"'), 'OUTPUT': 'memory:'})['OUTPUT']
        processing.run('qgis:selectbyexpression', {'INPUT' : layer, 'EXPRESSION' : '\"offset_sidewalk_right\" IS NOT NULL'})
        offset_sidewalk_right_layer = processing.run('native:offsetline', {'INPUT': QgsProcessingFeatureSourceDefinition(layer.id(), selectedFeaturesOnly=True), 'DISTANCE': QgsProperty.fromExpression('-"offset_sidewalk_right"'), 'OUTPUT': 'memory:'})['OUTPUT']

#        QgsProject.instance().addMapLayer(offset_cycleway_left_layer, True)
#        QgsProject.instance().addMapLayer(offset_cycleway_right_layer, True)
#        QgsProject.instance().addMapLayer(offset_sidewalk_left_layer, True)
#        QgsProject.instance().addMapLayer(offset_sidewalk_right_layer, True)

        #TODO: offset als Attribut überschreiben
        #eigenständige Attribute ableiten

        layer.updateFields()

    #derive attributes for offset ways
    for side in ['left', 'right']:
        for type in ['cycleway', 'sidewalk']:
            layer_name = 'offset_' + type + '_' + side + '_layer'
            exec("%s = %s" % ('offset_layer', layer_name))
            with edit(offset_layer):
                for feature in offset_layer.getFeatures():
                    offset_layer.changeAttributeValue(feature.id(), id_offset, feature.attribute('offset_' + type + '_' + side))
                    offset_layer.changeAttributeValue(feature.id(), id_type, type)
                    offset_layer.changeAttributeValue(feature.id(), id_side, side)
                    #this offset geometries are sidepath
                    offset_layer.changeAttributeValue(feature.id(), id_proc_sidepath, 'yes')
                    offset_layer.changeAttributeValue(feature.id(), id_proc_highway, feature.attribute('highway'))

                    offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('width'), deriveAttribute(feature, 'width', type, side, 'float'))
                    offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('oneway'), deriveAttribute(feature, 'oneway', type, side, 'str'))
                    offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('oneway:bicycle'), deriveAttribute(feature, 'oneway:bicycle', type, side, 'str'))

                    #surface and smoothness of cycle lanes are usually the same as on the road (if not explicitely tagged)
                    if type != 'cycleway' or (type == 'cycleway' and ((feature.attribute('cycleway:' + side) == 'track' or feature.attribute('cycleway:both') == 'track') or feature.attribute(type + ':' + side + ':surface') != NULL or feature.attribute(type + ':both:surface') != NULL or feature.attribute(type + ':surface') != NULL)):
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('surface'), deriveAttribute(feature, 'surface', type, side, 'str'))
                    if type != 'cycleway' or (type == 'cycleway' and ((feature.attribute('cycleway:' + side) == 'track' or feature.attribute('cycleway:both') == 'track') or feature.attribute(type + ':' + side + ':smoothness') != NULL or feature.attribute(type + ':both:smoothness') != NULL or feature.attribute(type + ':smoothness') != NULL)):
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('smoothness'), deriveAttribute(feature, 'smoothness', type, side, 'str'))

                    if type == 'cycleway':
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('separation'), deriveAttribute(feature, 'separation', type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('separation:both'), deriveAttribute(feature, 'separation:both', type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('separation:left'), deriveAttribute(feature, 'separation:left', type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('separation:right'), deriveAttribute(feature, 'separation:right', type, side, 'str'))

                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('traffic_mode:both'), deriveAttribute(feature, 'traffic_mode:both', type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('traffic_mode:left'), deriveAttribute(feature, 'traffic_mode:left', type, side, 'str'))
                        offset_layer.changeAttributeValue(feature.id(), offset_layer.fields().indexOf('traffic_mode:right'), deriveAttribute(feature, 'traffic_mode:right', type, side, 'str'))

    #TODO: Attribute mit "both" auf left und right aufteilen?

    #clean up offset layers
    #TODO

    #merge vanilla and offset layers
    layer = processing.run('native:mergevectorlayers', {'LAYERS' : [layer, offset_cycleway_left_layer, offset_cycleway_right_layer, offset_sidewalk_left_layer, offset_sidewalk_right_layer], 'OUTPUT': 'memory:'})['OUTPUT']



    #--------------------------------------------#
    #3: Determine way type for every way segment #
    #--------------------------------------------#

    print(time.strftime('%H:%M:%S', time.localtime()), 'Determine way type...')
    with edit(layer):
        for feature in layer.getFeatures():

            #exclude segments with no public bicycle access
            if getAccess(feature, 'bicycle') and getAccess(feature, 'bicycle') not in ['yes', 'permissive', 'designated', 'use_sidepath', 'optional_sidepath', 'discouraged']:
                layer.deleteFeature(feature.id())

            #exclude informal paths without explicit bicycle access
            if feature.attribute('highway') == 'path' and feature.attribute('informal') == 'yes' and feature.attribute('bicycle') == NULL:
                layer.deleteFeature(feature.id())

            way_type = ''
            highway = feature.attribute('highway')
            segregated = feature.attribute('segregated')

            bicycle = feature.attribute('bicycle')
            foot = feature.attribute('foot')
            vehicle = feature.attribute('vehicle')
            is_sidepath = feature.attribute('is_sidepath')

            #before determining the way type according to highway tagging, first check for some specific way types that are tagged independend from "highway":
            if feature.attribute('bicycle_road') == 'yes':
                #features with a "side" attribute are representing a cycleway or footway adjacent to the road with offset geometry - treat them as separate path, not as a bicycle road
                side = feature.attribute('side')
                if not side:
                    way_type = 'bicycle road'
            if feature.attribute('footway') == 'link' or feature.attribute('cycleway') == 'link' or feature.attribute('path') == 'link' or feature.attribute('bridleway') == 'link':
                way_type = 'link'
            if feature.attribute('footway') == 'crossing' or feature.attribute('cycleway') == 'crossing' or feature.attribute('path') == 'crossing' or feature.attribute('bridleway') == 'crossing':
                way_type = 'crossing'
            if feature.attribute('bicycle') == 'use_sidepath':
                way_type = 'use sidepath'
            if feature.attribute('bicycle') == 'no':
                way_type = 'cycle prohibition'

            #for all other cases: derive way type according to their primary "highway" tagging:
            if way_type == '':
                #for footways (with bicycle access):
                if highway in ['footway', 'pedestrian', 'bridleway', 'steps']:
                    if bicycle in ['yes', 'designated', 'permissive']:
                        way_type = 'shared footway'
                    else:
                        way_type = 'cycle prohibition'

                #for path:
                elif highway == 'path':
                    if foot == 'designated' and bicycle != 'designated':
                        way_type = 'shared footway'
                    else:
                        if segregated == 'yes':
                            way_type = 'segregated path'
                        else:
                            way_type = 'shared path'

                #for cycleways:
                elif highway == 'cycleway':
                    if foot in ['yes', 'designated', 'permissive']:
                        way_type = 'shared path'
                    else:
                        separation_foot = deriveSeparation(feature, 'foot')
                        if separation_foot == 'no':
                            way_type = 'segregated path'
                        else:
                            if not is_sidepath in ['yes', 'no']:
                                #Use the geometrically determined sidepath value, if is_sidepath isn't specified
                                if feature.attribute('proc_sidepath') == 'yes':
                                    way_type = 'cycle track'
                                else:
                                    way_type = 'cycle path'
                                    if not feature.attribute('proc_sidepath') in ['yes', 'no']:
                                        print(feature.attribute('id'))
                            
                            elif is_sidepath == 'yes':
                                separation_motor_vehicle = deriveSeparation(feature, 'motor_vehicle')
                                if not separation_motor_vehicle in [NULL, 'no', 'none']:
                                    if 'kerb' in separation_motor_vehicle or 'tree_row' in separation_motor_vehicle:
                                        way_type = 'cycle track'
                                    else:
                                        way_type = 'cycle lane (protected)'
                                else:
                                    way_type = 'cycle track'
                            else:
                                way_type = 'cycle path'

                #for service roads/tracks:
                elif highway == 'service' or highway == 'track':
                    way_type = 'track or service'

                #for motorways/trunks:
                elif 'motorway' in highway or 'trunk' in highway:
                    way_type = 'cycle prohibition'

                #for regular roads:
                else:
                    cycleway = feature.attribute('cycleway')
                    cycleway_both = feature.attribute('cycleway:both')
                    cycleway_left = feature.attribute('cycleway:left')
                    cycleway_right = feature.attribute('cycleway:right')
                    bicycle = feature.attribute('bicycle')
                    oneway = feature.attribute('oneway')
                    side = feature.attribute('side') #features with a "side" attribute are representing a cycleway or footway adjacent to the road with offset geometry
                    #if this feature don't represent a cycle lane, it's a center line representing the shared road
                    if not side:
                        #if cycle lanes are present, mark center line as "use sidepath"
                        if cycleway in ['lane', 'share_busway'] or cycleway_both in ['lane', 'share_busway'] or (oneway == 'yes' and cycleway_right in ['lane', 'share_busway']):
                            way_type = 'use sidepath'
                        #if tracks are present, mark center line as "optional sidepath" - as well as if "bicycle" is explicitely tagged as "optional_sidepath"
                        elif (cycleway == 'track' or cycleway_both == 'track' or (oneway == 'yes' and cycleway_right == 'track') or bicycle == 'optional_sidepath'):
                            way_type = 'optional sidepath'
                        else:
                            lane_markings = feature.attribute('lane_markings')
                            if lane_markings == 'yes':
                                way_type = 'shared traffic lane'
                            else:
                                way_type = 'shared road'
                    else:
                        type = feature.attribute('type')
                        if type == 'sidewalk':
                            way_type = 'shared footway'
                        else:
                            #for cycle lanes
                            if cycleway == 'lane' or cycleway_both == 'lane' or (side == 'right' and cycleway_right == 'lane') or (side == 'left' and cycleway_left == 'lane'):
                                cycleway_lanes = feature.attribute('cycleway:lanes')
                                if cycleway_lanes and 'no|lane|no' in cycleway_lanes:
                                    way_type = 'cycle lane (central)'
                                else:
                                    separation_motor_vehicle = deriveSeparation(feature, 'motor_vehicle')
                                    if not separation_motor_vehicle in [NULL, 'no', 'none']:
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
                            #for cycle tracks
                            elif cycleway == 'track' or cycleway_both == 'track' or (side == 'right' and cycleway_right == 'track') or (side == 'left' and cycleway_left == 'track'):
                                cycleway_foot = feature.attribute('cycleway:foot')
                                cycleway_both_foot = feature.attribute('cycleway:both:foot')
                                cycleway_left_foot = feature.attribute('cycleway:left:foot')
                                cycleway_right_foot = feature.attribute('cycleway:right:foot')
                                if cycleway_foot in ['yes', 'designated', 'permissive'] or cycleway_both_foot in ['yes', 'designated', 'permissive'] or (side == 'right' and cycleway_right_foot in ['yes', 'designated', 'permissive']) or (side == 'left' and cycleway_left_foot in ['yes', 'designated', 'permissive']):
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
                                        separation_foot = deriveSeparation(feature, 'foot')
                                        if separation_foot == 'no':
                                            way_type = 'segregated path'
                                        else:
                                            separation_motor_vehicle = deriveSeparation(feature, 'motor_vehicle')
                                            if not separation_motor_vehicle in [NULL, 'no', 'none']:
                                                if 'kerb' in separation_motor_vehicle or 'tree_row' in separation_motor_vehicle:
                                                    way_type = 'cycle track'
                                                else:
                                                    way_type = 'cycle lane (protected)'
                                            else:
                                                way_type = 'cycle track'
                            #for shared bus lanes
                            elif cycleway == 'share_busway' or cycleway_both == 'share_busway' or (side == 'right' and cycleway_right == 'share_busway') or (side == 'left' and cycleway_left == 'share_busway'):
                                way_type = 'shared bus lane'
                            #for other vales - no cycle way
                            else:
                                sidewalk_bicycle = feature.attribute('sidewalk:bicycle')
                                sidewalk_both_bicycle = feature.attribute('sidewalk:both:bicycle')
                                sidewalk_left_bicycle = feature.attribute('sidewalk:left:bicycle')
                                sidewalk_right_bicycle = feature.attribute('sidewalk:right:bicycle')
                                if sidewalk_bicycle == 'yes' or sidewalk_both_bicycle == 'yes' or (side == 'right' and sidewalk_right_bicycle == 'yes') or (side == 'left' and sidewalk_left_bicycle == 'yes'):
                                    way_type = 'shared footway'
                                else:
                                    lane_markings = feature.attribute('lane_markings')
                                    if lane_markings == 'yes':
                                        way_type = 'shared traffic lane'
                                    else:
                                        way_type = 'shared road'
            if way_type == '':
                way_type = NULL
            else:
                layer.changeAttributeValue(feature.id(), id_way_type, way_type)

        layer.updateFields()



    #----------------------------------------------------#
    #4: Derive relevant attributes for index and factors #
    #----------------------------------------------------#

    print(time.strftime('%H:%M:%S', time.localtime()), 'Derive attributes...')
    with edit(layer):
        for feature in layer.getFeatures():
            way_type = feature.attribute('way_type')
            side = feature.attribute('side')
            data_missing = ''

            proc_width = NULL
            proc_oneway = NULL #TODO+: derzeit noch nicht genutzt

            #-------------
            #Derive width. Use explicitely tagged attributes, derive from other attributes or use default values.
            #-------------
            if way_type in ['cycle path', 'cycle track', 'shared path', 'shared footway', 'crossing', 'cycle lane (advisory)', 'cycle lane (exclusive)', 'cycle lane (protected)', 'cycle lane (central)'] or getAccess(feature, 'motor_vehicle') == 'no':
                #width for cycle lanes and sidewalks have already been derived from original tags when calculating way offsets
                proc_width = getNumber(feature.attribute('width'))
                if not proc_width:

                    #TODO+: differentiate default width according to oneway (1.5m for oneways, 2.4 for non-oneways)

                    if way_type in ['cycle path', 'shared path', 'cycle lane (protected)']:
                        proc_width = default_highway_width_dict['path']
                    elif way_type == 'shared footway':
                        proc_width = default_highway_width_dict['footway']
                    else:
                        proc_width = default_highway_width_dict['cycleway']
                    data_missing = addDelimitedValue(data_missing, 'width')
            if way_type == 'segregated path':
                highway = feature.attribute('highway')
                if highway == 'path':
                    proc_width = getNumber(feature.attribute('cycleway:width'))
                    if not proc_width:
                        width = getNumber(feature.attribute('width'))
                        footway_width = getNumber(feature.attribute('footway:width'))
                        if width:
                            if footway_width:
                                proc_width = width - footway_width
                            else:
                                proc_width = width / 2
                        data_missing = addDelimitedValue(data_missing, 'width')
                else:
                    proc_width = getNumber(feature.attribute('width'))
                if not proc_width:
                    proc_width = default_highway_width_dict['path']
                    data_missing = addDelimitedValue(data_missing, 'width')
            if way_type in ['shared road', 'shared traffic lane', 'shared bus lane', 'bicycle road', 'track or service', 'use sidepath', 'optional sidepath']:

                #on shared traffic or bus lanes, use a width value based on lane width, not on carriageway width
                if way_type in ['shared road', 'shared traffic lane', 'shared bus lane',]:
                    highway = feature.attribute('highway') #assume that lanes are marked on main highways (secondary or higher)
                    if way_type in ['shared traffic lane', 'shared bus lane'] or highway in ['primary', 'secondary']:
                        oneway = feature.attribute('oneway')
                        width_lanes = feature.attribute('width:lanes')
                        width_lanes_forward = feature.attribute('width:lanes:forward')
                        width_lanes_backward = feature.attribute('width:lanes:backward')
                        if (oneway == 'yes' or way_type != 'shared bus lane') and width_lanes and '|' in width_lanes:
                            #TODO: at the moment, forward/backward can only be processed for shared bus lanes, since there are no separate geometries for shared road lanes
                            #TODO: for bus lanes, currently only assuming that the right lane is the bus lane. Instead derive lane position from "psv:lanes" or "bus:lanes", if specified
                            proc_width = getNumber(width_lanes[width_lanes.rfind('|') + 1:])
                        elif (way_type == 'shared bus lane' and oneway != 'yes') and side == 'right' and width_lanes_forward and '|' in width_lanes_forward:
                            proc_width = getNumber(width_lanes_forward[width_lanes_forward.rfind('|') + 1:])
                        elif (way_type == 'shared bus lane' and oneway != 'yes') and side == 'left' and width_lanes_backward and '|' in width_lanes_backward:
                            proc_width = getNumber(width_lanes_backward[width_lanes_backward.rfind('|') + 1:])
                        else:
                            if way_type == 'shared bus lane':
                                proc_width = default_width_bus_lane
                            else:
                                proc_width = default_width_traffic_lane
                                data_missing = addDelimitedValue(data_missing, 'width:lanes')

                #for shared roads without lane markings, derive effective (usable) width from carriageway width and parking lane information
                if not proc_width:
                    #effective width (usable width of a road for flowing traffic) can be mapped explicitely
                    proc_width = getNumber(feature.attribute('width:effective'))
                    #try to use lane count and a default lane width if no width and no width:effective is mapped
                    #(usually, this means, there are lane markings (see above), but sometimes "lane" tag is misused or "lane_markings" isn't mapped)
                    if not proc_width:
                        width = getNumber(feature.attribute('width'))
                        if not width:
                            lanes = getNumber(feature.attribute('lanes'))
                            if lanes:
                                proc_width = lanes * default_width_traffic_lane
                    #derive effective road width from road width and parking lane informations
                    if not proc_width:
                        parking_right = feature.attribute('parking:right')
                        parking_right_orientation = feature.attribute('parking:right:orientation')
                        parking_right_width = getNumber(feature.attribute('parking:right:width'))
                        parking_left = feature.attribute('parking:left')
                        parking_left_orientation = feature.attribute('parking:left:orientation')
                        parking_left_width = getNumber(feature.attribute('parking:left:width'))
                        parking_both = feature.attribute('parking:both')
                        parking_both_orientation = feature.attribute('parking:both:orientation')
                        parking_both_width = getNumber(feature.attribute('parking:both:width'))

                        #split parking:both-keys into left and right values
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

                        #subtract parking width from carriageway width to get effective width (usable width for driving)
                        if parking_right:
                            if not parking_right_width:
                                if parking_right_orientation == 'diagonal':
                                    parking_right_width = default_width_parking_diagonal
                                elif parking_right_orientation == 'perpendicular':
                                    parking_right_width = default_width_parking_perpendicular
                                else:
                                    parking_right_width = default_width_parking_parallel

                            #only use share of width that is located on the carriageway
                            if parking_right_width and parking_right == 'half_on_kerb':
                                parking_right_width = float(parking_right_width) / 2
                            elif parking_right != 'lane':
                                parking_right_width = 0

                        if parking_left:
                            if not parking_left_width:
                                if parking_left_orientation == 'diagonal':
                                    parking_left_width = default_width_parking_diagonal
                                elif parking_left_orientation == 'perpendicular':
                                    parking_left_width = default_width_parking_perpendicular
                                else:
                                    parking_left_width = default_width_parking_parallel

                            if parking_left_width and parking_left == 'half_on_kerb':
                                parking_left_width = float(parking_left_width) / 2
                            elif parking_left != 'lane':
                                parking_left_width = 0

                        #use default road width if no width is specified
                        if not width:
                            highway = feature.attribute('highway')
                            oneway = feature.attribute('oneway')
                            if highway in default_highway_width_dict:
                                width = default_highway_width_dict[highway]
                            else:
                                width = default_highway_width_fallback
                            #assume that oneway roads are narrower
                            if oneway == 'yes':
                                width = round(width / 1.6, 1)
                            data_missing = addDelimitedValue(data_missing, 'width')

                        if parking_right and parking_left:
                            proc_width = width - parking_right_width - parking_left_width
                            #if width was derived from a default, the result should not be less than the default width of a motorcar lane
                            if proc_width < default_width_traffic_lane and 'width' in data_missing:
                                proc_width = default_width_traffic_lane
                        else:
                            #if parking isn't mapped, only subtract some parking width defaults on shared regular roads
                            if way_type == 'shared road':
                                oneway = feature.attribute('oneway')
                                if oneway != 'yes':
                                    #assume that 5.5m of a regular unmarked carriageway are used for driving, other space for parking...
                                    proc_width = min(width, 5.5)
                                else:
                                    #resp. 4m in oneway roads
                                    proc_width = min(width, 4)
                                #mark "parking" as a missing value if there are no parking tags on regular roads
                                #TODO: Differentiate between inner and outer urban areas/city limits - out of cities, there is usually no need to map street parking
                                data_missing = addDelimitedValue(data_missing, 'parking')
                            else:
                                proc_width = width
            if not proc_width:
                proc_width = NULL

            layer.changeAttributeValue(feature.id(), id_proc_width, proc_width)

            #-------------
            #Derive surface and smoothness.
            #-------------

            proc_surface = NULL
            proc_smoothness = NULL

            #in rare cases, surface or smoothness is explicitely tagged for bicycles - check that first
            surface_bicycle = feature.attribute('surface:bicycle')
            smoothness_bicycle = feature.attribute('smoothness:bicycle')
            if surface_bicycle:
                if surface_bicycle in surface_factor_dict:
                    proc_surface = surface_bicycle
                elif ';' in surface_bicycle:
                    proc_surface = getWeakestSurfaceValue(getDelimitedValues(surface_bicycle, ';', 'string'))
            if smoothness_bicycle and smoothness_bicycle in smoothness_factor_dict:
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
                            if highway in default_highway_surface_dict:
                                proc_surface = default_highway_surface_dict[highway]
                            else:
                                proc_surface = default_highway_surface_dict['path']
                            data_missing = addDelimitedValue(data_missing, 'surface')
                    if not proc_smoothness:
                        proc_smoothness = feature.attribute('cycleway:smoothness')
                        if not proc_smoothness:
                            smoothness = feature.attribute('smoothness')
                            if smoothness:
                                proc_smoothness = smoothness
                            else:
                                data_missing = addDelimitedValue(data_missing, 'smoothness')
                else:
                    #surface and smoothness for cycle lanes and sidewalks have already been derived from original tags when calculating way offsets
                    proc_surface = feature.attribute('surface')
                    if not proc_surface:
                        if way_type in ['cycle lane (advisory)', 'cycle lane (exclusive)', 'cycle lane (protected)', 'cycle lane (central)']:
                            proc_surface = default_cycleway_surface_lanes
                        elif way_type == 'cycle track':
                            proc_surface = default_cycleway_surface_tracks
                        else:
                            highway = feature.attribute('highway')
                            if highway in default_highway_surface_dict:
                                proc_surface = default_highway_surface_dict[highway]
                            else:
                                proc_surface = default_highway_surface_dict['path']
                        data_missing = addDelimitedValue(data_missing, 'surface')
                    if not proc_smoothness:
                        proc_smoothness = feature.attribute('smoothness')
                        if not proc_smoothness:
                            data_missing = addDelimitedValue(data_missing, 'smoothness')

            #if more than one surface value is tagged (delimited by a semicolon), use the weakest one
            if ';' in proc_surface:
                proc_surface = getWeakestSurfaceValue(getDelimitedValues(proc_surface, ';', 'string'))
            if proc_surface not in surface_factor_dict:
                proc_surface = NULL
            if proc_smoothness not in smoothness_factor_dict:
                proc_smoothness = NULL
            
            layer.changeAttributeValue(feature.id(), id_proc_surface, proc_surface)
            layer.changeAttributeValue(feature.id(), id_proc_smoothness, proc_smoothness)



    #-------------------------------#
    #5: Calculate index and factors #
    #-------------------------------#

            #------------------------------------
            #Set base index according to way type
            #------------------------------------
            if way_type not in ['bicycle road', 'shared road', 'shared traffic lane']:
                base_index = base_index_dict[way_type]
            elif way_type == 'bicycle road':
                access = NULL
                if getAccess(feature, 'motor_vehicle') == 'no':
                    access = 'no'
                elif getAccess(feature, 'motor_vehicle') == 'destination':
                    access = 'destination'
                else:
                    access = 'yes'
                if access in base_index_bicycle_road_dict:
                    base_index = base_index_bicycle_road_dict[access]
                else:
                    base_index = NULL
            elif way_type in ['shared road', 'shared traffic lane']:
                highway = feature.attribute('highway')
                if highway in base_index_shared_road_dict:
                    base_index = base_index_shared_road_dict[highway]
                else:
                    base_index = NULL
            else:
                base_index = NULL
            layer.changeAttributeValue(feature.id(), id_base_index, base_index)

            #--------------------------------------------
            #Calculate width factor according to way type
            #--------------------------------------------
            calc_width = NULL
            oneway = feature.attribute('oneway')
            oneway_bicycle = feature.attribute('oneway:bicycle')
            minimum_factor = 0
            #for dedicated ways for cycling
            if way_type not in ['bicycle road', 'shared road', 'shared traffic lane', 'shared bus lane', 'track or service', 'use sidepath', 'optional sidepath', 'cycle prohibition', 'link'] or getAccess(feature, 'motor_vehicle') == 'no':
                calc_width = proc_width
                #calculated width depends on the width/space per driving direction
                if calc_width and oneway != 'yes' and oneway_bicycle != 'yes' and oneway != '-1' and oneway_bicycle != '-1':
                    if (not 'cycle lane' in way_type or ('cycle lane' in way_type and default_oneway_cycle_lane == 'no')) and (way_type != 'cycle track' or (way_type == 'cycle track' and default_oneway_cycle_track == 'no')):
                        calc_width /= 1.6 #TODO+: use proc_oneway to make this check easier

            #for shared roads and lanes
            else:
                calc_width = proc_width
                if calc_width:
                    if way_type == 'shared traffic lane':
                        calc_width = max(calc_width - 2 + ((4.5 - calc_width) / 3), 0)
                    elif way_type == 'shared bus lane':
                        calc_width = max(calc_width - 3 + ((5.5 - calc_width) / 3), 0)
                    else:
                        if not oneway or oneway == 'no':
                            calc_width /= 1.6 #TODO+: use proc_oneway to make this check easier
                        #TODO: Use a global 'optimum road width' variable for this?
                        calc_width -= 2 #on motor vehicle roads, optimum width is 2m for a car + 1m for bicycle + 1.5m safety distance -> exactly 2m more than the optimum width on cycleways. Simply subtract 2m from the processed width to get a comparable width value that can be used with the following width factor formula

            #Calculate width factor (logistic regression)
            if calc_width:
                #factor should not be negative and not 0, since the following logistic regression isn't working for 0
                calc_width = max(0.001, calc_width)
                #regular formula
                if calc_width <= 3 or way_type in ['bicycle road', 'shared road', 'shared traffic lane', 'shared bus lane', 'track or service', 'use sidepath', 'optional sidepath', 'cycle prohibition', 'link']:
                    fac_width = 1.1 / (1 + 20 * math.e ** (-2.1 * calc_width))
                #formula for extra wide ways (not used for shared roads and lanes)
                else:
                    fac_width = 2 / (1 + 1.8 * math.e ** (-0.24 * calc_width))
                fac_width = round(max(minimum_factor, fac_width), 3)
            else:
                fac_width = NULL

            layer.changeAttributeValue(feature.id(), id_fac_width, fac_width)

            #---------------------------------------
            #Calculate surface and smoothness factor
            #---------------------------------------
            if proc_smoothness and proc_smoothness in smoothness_factor_dict:
                fac_surface = smoothness_factor_dict[proc_smoothness]
            elif proc_surface and proc_surface in surface_factor_dict:
                fac_surface = surface_factor_dict[proc_surface]

            layer.changeAttributeValue(feature.id(), id_fac_surface, fac_surface)

            #------------------------------------------------
            #Calculate highway (sidepath) and maxspeed factor
            #------------------------------------------------
            proc_highway = feature.attribute('proc_highway')
            proc_maxspeed = feature.attribute('proc_maxspeed')
            fac_highway = 1
            fac_maxspeed = 1
            if proc_highway and proc_highway in highway_factor_dict:
                fac_highway = highway_factor_dict[proc_highway]
            if proc_maxspeed:
                for maxspeed in maxspeed_factor_dict.keys():
                    if proc_maxspeed >= maxspeed:
                        fac_maxspeed = maxspeed_factor_dict[maxspeed]

            layer.changeAttributeValue(feature.id(), id_fac_highway, fac_highway)
            layer.changeAttributeValue(feature.id(), id_fac_maxspeed, fac_maxspeed)

            #---------------
            #Calculate index
            #---------------
            index = NULL
            if base_index != NULL:
                #factor 1: width and surface
                #width and surface factors are weighted, so that low values have a stronger influence on the index
                if fac_width and fac_surface:
                    #fac1 = (fac_width + fac_surface) / 2 #formula without weight factors
                    weight_factor_width = max(1 - fac_width, 0) + 0.5 #max(1-x, 0) makes that only values below 1 are resulting in a stronger decrease of the index
                    weight_factor_surface = max(1 - fac_surface, 0) + 0.5
                    fac1 = (weight_factor_width * fac_width + weight_factor_surface * fac_surface) / (weight_factor_width + weight_factor_surface)
                elif fac_width:
                    fac1 = fac_width
                elif fac_surface:
                    fac1 = fac_surface
                else:
                    fac1 = 1

                #factor 2: highway and maxspeed
                #if way type isn't a cycle lane or shared bus lane, this factor is only counted half, as it does not have such a strong influence on the quality if there is physical separation
                fac2 = (fac_highway + fac_maxspeed) / 2
                if not fac2:
                   fac2 = 1
                if not ' lane' in way_type or way_type == 'cycle lane (protected)':
                    fac2 = (fac2 + 1) / 2

                #factor 3: separation and buffer
                #TODO+
                fac3 = 1

                #factor group 4: miscellaneous attributes can result in an other bonus or malus
                #TODO+
                fac4 = 1

                index = base_index * fac1 * fac2 * fac3 * fac4

                index = max(min(100, index), 0) #index should be between 0 and 100 in the end for pragmatic reasons
                index = int(round(index))       #index is an int

            layer.changeAttributeValue(feature.id(), id_index, index)
            layer.changeAttributeValue(feature.id(), id_data_missing, data_missing)

            #derive a data completeness number
            data_completeness = 100
            missing_values = getDelimitedValues(data_missing, ';', 'string')
            for value in missing_values:
                if value in data_completeness_dict:
                    data_completeness -= data_completeness_dict[value]
            layer.changeAttributeValue(feature.id(), id_data_completeness, data_completeness)

        layer.updateFields()

    #clean up data set
    print(time.strftime('%H:%M:%S', time.localtime()), 'Clean up data...')
    processing.run('native:retainfields', { 'INPUT' : layer, 'FIELDS' : retained_attributes_list, 'OUTPUT': dir_output })



#    print(time.strftime('%H:%M:%S', time.localtime()), 'Display data...')
#    QgsProject.instance().addMapLayer(layer, True)
#
#    #focus on output layer
#    iface.mapCanvas().setExtent(layer.extent())

print(time.strftime('%H:%M:%S', time.localtime()), 'Finished processing.')