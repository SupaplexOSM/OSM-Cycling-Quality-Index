# ------------------------------------------------------------------------- #
#   Cycling Quality Index                                                   #
#   --------------------------------------------------                      #
#   Script for processing OSM data to analyse the cycling quality of ways.  #
#   Download OSM data input from https://overpass-turbo.eu/s/1G3t,          #
#   save it at data/way_import.geojson and run the script.                  #
#                                                                           #
#   > version/date: 2024-03-02                                              #
# ------------------------------------------------------------------------- #

import imp
import imp
import pathlib

import script_main

imp.reload(script_main)

# project directory
project_dir = pathlib.Path(__file__).parents[0]  # project directory
dir_input = project_dir / 'data/way_import.geojson'
dir_output = project_dir / 'data/cycling_quality_index.geojson'

script_main.main(dir_input, dir_output)
