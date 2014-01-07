#!/usr/bin/env bash
# Installing prerequisites
sudo apt-get install parallel 
sudo apt-get install r-base-core 
sudo apt-get install bedtools 
sudo apt-get install tabix 
sudo apt-get install kyotocabinet-utils 
sudo apt-get install realpath
# Ubuntu-specific installation of Python packages
sudo apt-get -y install python-pip python-dev python-cherrypy3 python-numpy python-scipy python-rpy2 python-simplejson python-mako
sudo apt-get upgrade gcc 
sudo pip install -U cython
# Manual download and installation of required binaries
mkdir downloads
cd downloads
wget -N https://github.com/bedops/bedops/releases/download/v2.3.0/bedops_linux_x86_64-v2.3.0.tar.bz2
sudo tar xjvf bedops_linux_x86_64-v2.3.0.tar.bz2 -C /usr/local/
sudo wget -np -R -A "bedToBigBed" -A "bedGraphToBigWig" -A "bigWig*" -A "bigBed*" -N -e robots=off -r -P /usr/local/bin -nd "http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/"
sudo wget -o /usr/local/bin/rowsToCols http://hgdownload.cse.ucsc.edu/admin/exe/linux.x86_64/rowsToCols
sudo chmod a+x /usr/local/bin/*
cd ..
sudo rm -r downloads
# Installing R packages
sudo Rscript installer.R
# Installing Genomic Region Tool Kit
cd grtk
sudo python setup.py install
cd ..
# Finally, installing GenomeRunner itself
sudo python setup.py install
