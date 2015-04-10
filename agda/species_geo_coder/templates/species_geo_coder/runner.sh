#!/bin/sh

set -e

function logg() { 
	echo $(date +%Y%m%d-%H%M:) "$*"
}

#export R_LIBS=/home/johan/rlibs1

GEOCODERDIR=/home/johan/speciesgeocoder-0.9.3

source $GEOCODERDIR/geoenv/bin/activate
export R_LIBS=/home/johan/rlibs1

python $GEOCODERDIR/geocoder.py \
    --path_script $GEOCODERDIR \
    -l {{localities}} \
    -p {{polygons}} \
    {% if verbose %} -v {% endif %} \
    {% if plot %} --plot {% endif %} \
    {% if occurences > 1 %} -n {{occurences}} {% endif %} \
    > {{outfile}}

{% if plot %}
#'barchart_per_polygon', 'barchart_per_species',
#                    'heatplot_coexistence', 'map_samples_overview',
#                    'map_samples_per_polygon', 'map_samples_per_species',
#                    'number_of_species_per_polygon']:
{% endif %}
