===========
GRSNP Database Readme
===========

This file database was created using the *grsnp.dbcreator*.  The absolute path of this directory should be passed to the *--data_dir* argument of the *grsnp.server*


Directory Structure
=========

Created by the grsnp.dbcreator:

* ./grsnp_db 
	
	* Contains the genomic feature database installed from UCSC

Created by the server:

* ./run_files 
	
	* Stores files that are uploaded to the server by the user and also stores the results of the analysis

The following directories are generated by the sever. Bed files or .bb files should be added to the appropriate directories:

* ./custom_data/gfs/[organism id]

	* Stores default genomic features.
	
* ./custom_data/fois/[organism id]

	* Stores default feature of interests.

* ./custom_data/backgrounds/[organism id]

	* Stores default backgrounds
