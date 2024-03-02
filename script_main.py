import imp
import math
import time
from collections import defaultdict
from os.path import exists

import qgis.processing as processing
from qgis import *
from qgis.core import *
from qgis.PyQt.QtCore import *

import vars_settings

imp.reload(vars_settings)
import helper_functions

imp.reload(helper_functions)
import script_step_01

imp.reload(script_step_01)
import script_step_02

imp.reload(script_step_02)
import script_step_03

imp.reload(script_step_03)
import script_step_04

imp.reload(script_step_04)


def main(dir_input, dir_output):
    print(time.strftime('%H:%M:%S', time.localtime()), 'Start processing:')

    print(time.strftime('%H:%M:%S', time.localtime()), 'Read data...')
    if not exists(dir_input):
        print(time.strftime('%H:%M:%S', time.localtime()), '[!] Error: No valid input file at "' + dir_input + '".')
    else:
        layer_way_input = QgsVectorLayer(f"{dir_input}|geometrytype=LineString", 'way input', 'ogr')

        print(time.strftime('%H:%M:%S', time.localtime()), 'Reproject data...')
        layer = processing.run('native:reprojectlayer', { 'INPUT' : layer_way_input, 'TARGET_CRS' : QgsCoordinateReferenceSystem(vars_settings.crs_to), 'OUTPUT': 'memory:'})['OUTPUT']

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
        'tracktype',
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
        'sidewalk:traffic_sign',
        'sidewalk:both:traffic_sign',
        'sidewalk:left:traffic_sign',
        'sidewalk:right:traffic_sign',

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
        'cycleway:left:surface:colour',
        'cycleway:traffic_sign',
        'cycleway:both:traffic_sign',
        'cycleway:left:traffic_sign',
        'cycleway:right:traffic_sign',

        'cycleway:lanes',
        'cycleway:lanes:forward',
        'cycleway:lanes:backward',
        'vehicle:lanes',
        'bus:lanes',
        'psv:lanes',

        'crossing',
        'crossing:markings'
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
        'proc_traffic_mode_left': 'String',
        'proc_traffic_mode_right': 'String',
        'proc_separation_left': 'String',
        'proc_separation_right': 'String',
        'proc_buffer_left': 'Double',
        'proc_buffer_right': 'Double',
        'proc_mandatory': 'String',
        'proc_traffic_sign': 'String',
        'fac_width': 'Double',
        'fac_surface': 'Double',
        'fac_highway': 'Double',
        'fac_maxspeed': 'Double',
        'fac_protection_level': 'Double',
        'prot_level_separation_left': 'Double',
        'prot_level_separation_right': 'Double',
        'prot_level_buffer_left': 'Double',
        'prot_level_buffer_right': 'Double',
        'prot_level_left': 'Double',
        'prot_level_right': 'Double',
        'base_index': 'Int',
        'fac_1': 'Double',
        'fac_2': 'Double',
        'fac_3': 'Double',
        'fac_4': 'Double',
        'index': 'Int',
        'data_incompleteness': 'Double',
        'data_missing': 'String',
        'data_bonus': 'String',
        'data_malus': 'String'
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
        id_proc_traffic_mode_left = layer.fields().indexOf('proc_traffic_mode_left')
        id_proc_traffic_mode_right = layer.fields().indexOf('proc_traffic_mode_right')
        id_proc_separation_left = layer.fields().indexOf('proc_separation_left')
        id_proc_separation_right = layer.fields().indexOf('proc_separation_right')
        id_proc_buffer_left = layer.fields().indexOf('proc_buffer_left')
        id_proc_buffer_right = layer.fields().indexOf('proc_buffer_right')
        id_proc_mandatory = layer.fields().indexOf('proc_mandatory')
        id_proc_traffic_sign = layer.fields().indexOf('proc_traffic_sign')
        id_fac_width = layer.fields().indexOf('fac_width')
        id_fac_surface = layer.fields().indexOf('fac_surface')
        id_fac_highway = layer.fields().indexOf('fac_highway')
        id_fac_maxspeed = layer.fields().indexOf('fac_maxspeed')
        id_fac_protection_level = layer.fields().indexOf('fac_protection_level')
        id_prot_level_separation_left = layer.fields().indexOf('prot_level_separation_left')
        id_prot_level_separation_right = layer.fields().indexOf('prot_level_separation_right')
        id_prot_level_buffer_left = layer.fields().indexOf('prot_level_buffer_left')
        id_prot_level_buffer_right = layer.fields().indexOf('prot_level_buffer_right')
        id_prot_level_left = layer.fields().indexOf('prot_level_left')
        id_prot_level_right = layer.fields().indexOf('prot_level_right')
        id_base_index = layer.fields().indexOf('base_index')
        id_fac_1 = layer.fields().indexOf('fac_1')
        id_fac_2 = layer.fields().indexOf('fac_2')
        id_fac_3 = layer.fields().indexOf('fac_3')
        id_fac_4 = layer.fields().indexOf('fac_4')
        id_index = layer.fields().indexOf('index')
        id_data_incompleteness = layer.fields().indexOf('data_incompleteness')
        id_data_missing = layer.fields().indexOf('data_missing')
        id_data_bonus = layer.fields().indexOf('data_bonus')
        id_data_malus = layer.fields().indexOf('data_malus')

        QgsProject.instance().addMapLayer(layer, False)

        script_step_01.step_01(
            layer,
            id_proc_highway,
            id_proc_maxspeed,
            id_proc_sidepath,
        )
        script_step_02.step_02(
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
        )
        script_step_03.step_03(
            layer,
            id_way_type
        )
        script_step_04.step_04(
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
        )

        #clean up data set
        print(time.strftime('%H:%M:%S', time.localtime()), 'Clean up data...')
        processing.run('native:retainfields', { 'INPUT' : layer, 'FIELDS' : vars_settings.retained_attributes_list, 'OUTPUT': f"{dir_output}" })



    #    print(time.strftime('%H:%M:%S', time.localtime()), 'Display data...')
    #    QgsProject.instance().addMapLayer(layer, True)
    #
    #    #focus on output layer
    #    iface.mapCanvas().setExtent(layer.extent())

    print(time.strftime('%H:%M:%S', time.localtime()), 'Finished processing.')
