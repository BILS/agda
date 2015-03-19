#!/bin/sh

set -e

function logg() { 
	echo $(date +%Y%m%d-%H%M:) "$*"
}

#export R_LIBS=/home/johan/rlibs1

GEOCODERDIR=/home/johan/speciesgeocoder-0.9.3

source $GEOCODERDIR/geoenv/bin/activate

python $GEOCODERDIR/geocoder.py -l {{localities}} -p {{polygons}} > {{outfile}}
