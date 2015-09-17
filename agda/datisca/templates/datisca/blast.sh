#!/bin/bash

set -e

function logg() { 
	echo $(date +%Y%m%d-%H%M:) "$*"
}

logg "Adding blast+ module: blast+/2.2.27-1"
module add blast+/2.2.27-1

db=$(basename {{db}})
dbdir=$(dirname {{db}})

if [ $db == 'all' ]; then
	logg "prepare_db $dbdir/*.blastdb.tar.gz $dbdir/all.nal"
	prepare_db $dbdir/*.blastdb.tar.gz
	cp $dbdir/all.nal $BLASTDB
else 
	logg "Preparing database: {{db}}.blastdb.tar.gz"
	prepare_db {{db}}.blastdb.tar.gz
fi

logg "Running {{program}} -num_threads 8 -query {{query}} -db $db -evalue {{evalue}} -max_target_seqs 250 -out {{out}}"
{{program}} -num_threads 8 -query {{query}} -db $db -evalue {{evalue}} -max_target_seqs 250 -out {{out}}

logg "Parsing hits..."
python parse_blast.py {{db}}

logg "Done."
