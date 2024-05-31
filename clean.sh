#!/usr/bin/env bash

rm -f _dna_jellyfish.*.so dna_jellyfish.py 
rm -fr build/ pyjellyfish.egg-info/
rm -fr jf/bin jf/build jf/include jf/lib jf/share
rm -fr __pycache__/

if [ "$1" == "dist" ]
then
    rm -fr dist/
fi
