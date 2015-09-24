#!/bin/bash

module load R/3.2.0
module load gdal/1.11.2
module load geos/3.4.2
module load species_geo_coder/git

set -e

function logg() { 
	echo $(date +%Y%m%d-%H%M:) "$*"
}

echo "Geocoder is in: $(which geocoder.py)"

GEOCODERDIR=$(dirname $(which geocoder.py))

geocoder.py \
    --path_script $GEOCODERDIR \
    -l {{localities}} \
    -p {{polygons}} \
    {% if verbose %} -v {% endif %} \
    {% if plot %} --plot {% endif %} \
    {% if occurences > 1 %} -n {{occurences}} {% endif %} \
    --out {{outfile}}

{% if plot %}
zip plots.zip \
    barchart_per_polygon.pdf \
    barchart_per_species.pdf \
    heatplot_coexistence.pdf \
    map_samples_overview.pdf \
    map_samples_per_polygon.pdf \
    map_samples_per_species.pdf \
    number_of_species_per_polygon.pdf
#'barchart_per_polygon', 'barchart_per_species',
#                    'heatplot_coexistence', 'map_samples_overview',
#                    'map_samples_per_polygon', 'map_samples_per_species',
#                    'number_of_species_per_polygon']:
{% endif %}
