from qgis.core import NULL

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