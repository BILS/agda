#!/bin/bash

set -e

### Setup
module add python/2.7.6-build01
module add pcons-fold/140128
module add blast+/2.2.27-1 # for prepare_db
module add plmdca/2012-build01 # reminder that this workflow uses this plmDCA version. 

scratch=$SNIC_TMP
agdaworkdir=$(pwd)

DEBUG=false
if [ "$DEBUG" = "true" ]; then
	cp /scratch/local/test/intermediary_predictions.tgz .
	tar xf intermediary_predictions.tgz '*.png' '*.out' '*.txt'
	mv intermediary_predictions/* .
	exit
fi

blastdb=$(dirname {{jackhmmerdb}})/$(basename {{jackhmmerdb}} .gz).blastdb.tar.gz

hhblitsdbname=$(basename {{hhblitsdb}} .tar.gz)
local_hhblitsdb=$scratch/$hhblitsdbname/$hhblitsdbname
local_jackhmmerdb=$scratch/$(basename {{jackhmmerdb}} .gz)

intermediariesname=$(basename {{intermediaries}} .tgz) 


### Stage data
prepare_db {{hhblitsdb}} {{jackhmmerdb}} $blastdb
cp {{query}} $scratch

### Run prediction

pushd $scratch
predictAll_1.0.py -c $SLURM_JOB_CPUS_PER_NODE $local_hhblitsdb $local_jackhmmerdb {{query}} 2> $agdaworkdir/{{log}}
predictAll_2.0.py $local_hhblitsdb $local_jackhmmerdb {{query}} $SLURM_JOB_CPUS_PER_NODE 2>> $agdaworkdir/{{log}}

### Assemble results
cp *.png *.out $agdaworkdir
mkdir $intermediariesname
mv query.fasta.horiz *.psicov *.plmdca *.png *.ss *.ss2 *.rsa *.out $intermediariesname
cp $agdaworkdir/{{log}} $intermediariesname
tar czf $agdaworkdir/{{intermediaries}} $intermediariesname
popd
