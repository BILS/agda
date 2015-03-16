#!/bin/bash

set -e

function logg() { 
	echo $(date +%Y%m%d-%H%M:) "$*"
}

logg "Adding hmmer module: hmmer/2.3.2-1"
module add hmmer/2.3.2-1

logg "Preparing MDR HMM database: {{db}}"
prepare_db {{db}} 

logg "Running hmmpfam..."
hmmpfam --informat fasta $HMMER_DB_DIR/mdr.pfam query.fasta > mdrscan.hmmpfam

logg "Parsing hits..."
python parse_mdrscan.py

logg "Done."
