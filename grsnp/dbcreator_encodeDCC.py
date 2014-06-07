#!/usr/bin/env python2
import sys
import errno
import logging
from logging import FileHandler,StreamHandler
import os
import ftplib
import sqlite3
import string
from contextlib import closing
import subprocess
import argparse
import gzip
import re
import collections
import copy
import traceback  as trace
import pdb
from xml.sax.saxutils import quoteattr as xml_quoteattr
import BeautifulSoup
import urllib2
from grsnp.dbcreator_util import *

logger = logging.getLogger('genomerunner.dbcreator')

# connection information for the ucsc ftp server
ftp_server = 'hgdownload.cse.ucsc.edu'
directory = '/goldenPath/{}/encodeDCC'
username = 'anonymous'
password = ''
numdownloaded = collections.defaultdict(int)



# downloads the specified file from ucsc.  Saves it with a .temp extension untill the download is complete.
def download_file(organism,gf_grp,gf_file,downloaddir):
	''' Downloads the gf_file from the UCSC ftp server and saves it
	in a folder with the same name as the organism.
	'''
	outputpath = ''
	if downloaddir != None and downloaddir != '':
		outputdir = os.path.join(downloaddir,organism)
	else:
		outputdir = organism
	try:
		if os.path.exists(outputdir) == False and outputdir != '':
			logger.info( "creating directory {}".format(outputdir))
			os.makedirs(outputdir)
	except Exception, e:
		logger.warning( e)
		logger.warning("Could not create folder at {} for {}".format(outputdir,gf_file))
		return '' 
	
	try:
		outputpath = os.path.join(outputdir,gf_file)
		if not os.path.exists(outputpath):
			ftp = ftplib.FTP(ftp_server, timeout=1800) # Connection timeout 0.5h
			ftp.login(username,password)
			with open(outputpath + ".temp",'wb') as fhandle:  
				global ftp
				logger.info( 'Downloading {} from UCSC'.format(gf_file))				
				ftp.cwd(os.path.join(directory.format(organism),gf_grp))
				ftp.retrbinary('RETR ' + "{}".format(gf_file),fhandle.write)
				os.rename(outputpath+".temp",outputpath)
				logger.info( 'Finished downloading {} from UCSC'.format(gf_file))
			ftp.quit()
			# remove header lines
			remove_headers(outputpath)
		else:
			logger.info( '{} already exists, skipping download'.format(outputpath))
	except IOError as e:
		if e.errno == errno.EPIPE: # Broken pipe error handling
			logger.error('FTP download error. Restart the dbcreator. Exiting now...')
			ftp.quit()
			sys.exit(2)
	except Exception, e:
		logger.warning(e)
		logger.warning("Could not download the {} file. Names ARE case sensitive.".format(gf_file))
		return '' 
	return outputpath 

def get_gf_groups(organism):
	''' Returns the list of folders on the ucsc server which contain the GF files.
	'''
	ftp = ftplib.FTP(ftp_server, timeout=1800) # Connection timeout 0.5h
	ftp.login(username,password)

	root_dir = directory.format(organism)
	ftp.cwd(root_dir)
	gf_paths = []
	# get all folders in the root directory
	ftp.dir(gf_paths.append)
	gf_paths = [x.split()[-1] for x in gf_paths if x[0] == 'd']
	ftp.quit()
	return gf_paths

def get_gf_filepaths(organism,gf_grp):
	''' Returns the list of file in the gf_grp folder on the ucsc server.
	'''
	ftp = ftplib.FTP(ftp_server, timeout=1800) # Connection timeout 0.5h
	ftp.login(username,password)

	root_dir = os.path.join(directory.format(organism),gf_grp)
	ftp.cwd(root_dir)
	gf_paths = []
	# get all folders in the root directory
	ftp.dir(gf_paths.append)
	gf_paths = [x.split()[-1] for x in gf_paths if x[0] == '-']
	ftp.quit()
	return gf_paths


def preparebed(organism,gf_grp,gf_file,download_dir,outputpath):
	''' Opens the bed file and ensures it is in a proper format for GR and extracts it. 
	The 'chrom_index' should be the zero-based index of the column containing the chrom 
	(i.e. 1 for bedRnaElements, where the 0 column is the 'bin' column.
	'''
	if (gf_file.endswith('.bed') or gf_file.endswith('.bed.gz') or
		gf_file.endswith('.bed9') or gf_file.endswith('.bed9.gz') or
		gf_file.endswith('.bedRrbs') or gf_file.endswith('.bedRrbs.gz') or
		gf_file.endswith('.narrowPeak') or gf_file.endswith('.narrowPeak.gz') or
		gf_file.endswith('.broadPeak') or gf_file.endswith('.broadPeak.gz') or
		gf_file.endswith('.peptideMapping') or gf_file.endswith('.peptideMapping.gz') or
		):		
		gf_file = download_file(organism,gf_grp,gf_file,download_dir)
		return extract_bed(gf_file,outputpath,0)
	elif gf_file.endswith('.bedRnaElements') or gf_file.endswith('.bedRnaElements.gz'):
		gf_file = download_file(organism,gf_grp,gf_file,download_dir)		
		return extract_bed(gf_file,outputpath,1)
	else:
		return [MinMax(),'failed']

def extract_bed(datapath,outputpath,chrom_index):
	min_max = MinMax() # keep track of the min and max score
	if datapath[:-3] == '.gz':
		infile,outfile = gzip.open(datapath),gzip.open(outputpath,'wb')
	else:
		infile,outfile = open(datapath),open(outputpath,'wb')
	while True:
		line = infile.readline().strip()
		if line == "":
			break
		outfile.write(_format_bed(line,chrom_index,min_max)+"\n")
	return [min_max.str_minmax(),'bed']

def _format_bed(line,chrom_index,min_max):
	line = line.split("\t")[chrom_index:]
	# removes special characters and the '.' used when a field is blank
	if len(line) >= 6+chrom_index:
		line[3+chrom_index] = ''.join(e for e in line[3+chrom_index] if e.isalnum())
		line[4+chrom_index] = line[4+chrom_index] if line[4+chrom_index] != "." else "0"
		line[5+chrom_index] = line[5+chrom_index] if line[5+chrom_index] in ["+","-"] else ""
		min_max.update_minmax(line[4+chrom_index])
	elif len(line) == 5+chrom_index:
		line[3+chrom_index] = ''.join(e for e in line[3+chrom_index] if e.isalnum())
		line[4+chrom_index] = line[4+chrom_index] if line[4+chrom_index] != "." else "0"
		min_max.update_minmax(line[4+chrom_index])
	elif len(line) == 4+chrom_index:
		line[3+chrom_index] = ''.join(e for e in line[3+chrom_index] if e.isalnum())
	return "\t".join(line)


def create_feature_set(data_dir,organism,gf_groups,pct_score=None):
	outputdir = os.path.join(data_dir,organism)
	download_dir = os.path.join(os.path.split(os.path.split(outputdir)[0])[0],"downloads")
	min_max_path = os.path.join(outputdir,'minmax.txt')
	added_features = [] 
	outpath = ""
	prog, num = 0,len(gfs)
	summary_path = os.path.join(outputdir,"summary.log")
	gf_groups = [x for x in gfs if x != ""]
	# get list of GFs files on server
	if len(gf_groups) == 0:
		gf_groups = get_gf_groups(organism)


	min_max_scores,num = load_minmax(min_max_path),len(gf_groups)
	for gf_grp in gf_groups:
		for gf_file in get_gf_filepaths(organism,gf_grp):
			
			try:
				gf_type = ""
				outpath = os.path.join(outputdir,gf_grp,base_name(gf_file.replace(gf_grp,'')))
				if not os.path.exists(os.path.dirname(outpath)):
					os.makedirs(os.path.dirname(outpath))
				if os.path.exists(outpath) == False:
					# removes the .temp file, to prevent duplicate data from being written
					if os.path.exists(outpath+".temp"):
						os.remove(outpath+".temp")
					# converts the ucsc data into propery bed format
					logger.info( "Converting into proper bed format: {}".format(gf_file))
					[minmax_score,gf_type] = preparebed(organism,gf_grp,gf_file,download_dir,outpath+".temp")
					# cannot detect type, skip
					if gf_type == "failed":
						write_line("\t".join([gf_file,"Not supported","None"]),summary_path)
						logger.warning( "Unable to convert {} into bed".format(gf_file))
						continue
					# output minmax stats
					min_max_scores[gf_file] = minmax_score
					save_minmax(min_max_scores,min_max_path)
					# sort the file and convert to bgzip format
					o_dir = os.path.dirname(outpath)
					new_path = os.path.join(o_dir,''.join(e for e in base_name(outpath) if e.isalnum() or e=='.' or e=='_')) + ".bed.gz"
					sort_convert_to_bgzip(outpath+".temp",new_path)
					added_features.append(outpath)
				else:
					logger.info( "{} already exists as or .gz, skipping extraction".format(outpath.replace(".gz","")))
				write_line("\t".join([gf_file,gf_type,"None"]),summary_path)
				numdownloaded[gf_type] += 1

			except Exception, e:
				write_line("\t".join([gf_file,"Failed",str(e)]),summary_path)
				exc = trace.format_exc()
				logger.warning( "Unable to convert {} into bed".format(gf_file))
				logger.warning(exc)
				prog += 1
				continue	

	prog += 1
	# cleanup the temporary files
	if os.path.exists(outpath + ".temp"): os.remove(outpath+".temp")

	# logger.info( "The following types are not supported (includes all 'big' file types):\n " + str(notsuptypes))
	# logger.info("The following features were added to the database: \n{}".format(added_features))
	logger.info("A count of features added by type: ")
	for k,d in numdownloaded.iteritems():
		logger.info( k + ":" + str(d))
	return "Created UCSC database"


if __name__ == "__main__":
	parser = argparse.ArgumentParser(prog="python -m grsnp.dbcreator", description='Creates the GenomeRunner SNP Database. Example: python -m grsnp.dbcreator -d /home/username/grsnp_db/ -g mm9', epilog='IMPORTANT: Execute DBCreator from the database folder, e.g., /home/username/grsnp_db/. Downloaded files from UCSC are placed in ./downloads database created in ./grsnp_db.')
	parser.add_argument("--data_dir" , "-d", nargs="?", help="Set the directory where the database to be created. Use absolute path. Example: /home/username/grsnp_db/. Required", required=True)
	parser.add_argument('--organism','-g', nargs="?", help="The UCSC code of the organism to use for the database creation. Default: hg19 (human). Required", default="hg19")
	parser.add_argument('--featuregroups','-f', nargs="?", help='The names of the specific genomic feature groups to download.', default="")
	parser.add_argument('--galaxy', help="Create the xml files needed for Galaxy. Outputted to the current working directory. List available for hg19 at ftp://hgdownload.cse.ucsc.edu/goldenPath/hg19/encodeDCC/", action="store_true")
	parser.add_argument('--score', '-s', help="Commas separated list of score percentiles.", nargs='?',default="")
	parser.add_argument('--scoreonly','-o', help="Only filter by score. Skips downloading and installing new GFs.", action="store_true")



	args = vars(parser.parse_args())

	hdlr = logging.FileHandler(os.path.join(args['data_dir'], 'genomerunner_dbcreator.log'))
	hdlr_std = StreamHandler()
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	hdlr.setFormatter(formatter)
	logger.addHandler(hdlr)
	logger.addHandler(hdlr_std)
	logger.setLevel(logging.INFO)

	if not args["data_dir"]:
		print "ERROR: --data_dir is required"
		sys.exit()

	if args['score'] == "":
		args['score'] = "25,50,75"
	args['score'] = set(args['score'].split(',')) # remove duplicate scores
		
	global ftp
	ftp = ftplib.FTP(ftp_server, timeout=1800) # Connection timeout 0.5h
	ftp.login(username,password)
	outputdir=os.path.join(args["data_dir"],'grsnp_db')

	if not args['scoreonly']:
		if args['galaxy']:
			usrdir = raw_input("Enter directory of Galaxy containing the run.sh file. If left blank, grsnp_gfs.xml file will be outputted in the cwd: \n")
			if usrdir == '': 
				usrdir = os.getcwd()
			else:
				usrdir = os.path.join(usrdir,"tool-data")
				if not os.path.exists(usrdir):
					logger.error("Galaxy tool-data does not exist")
					sys.exist()
			create_galaxy_xml_files(outputdir,usrdir)		
			sys.exit()
		if args['organism'] is not None: # Only organism is specified. Download all organism-specific features
			gfs = args["featuregroups"].split(",")
			create_feature_set(outputdir,args['organism'],gfs)			
		else:
			print "ERROR: Requires UCSC organism code.  Use --help for more information"
			sys.exit()
	else:
		# load score from minmax.txt file created earlier
		minmax = load_minmax(os.path.join(outputdir,args['organism'],"minmax.txt"))		

		### Second Step: Create subdirectories for score and filter data by score percentile
		# create sub directories for score percentiles and populate with score-filtered GF data
		# gather all directories (groups) in the database
		print "Filtering GFs by Score"
		orgdir = os.path.join(outputdir,args['organism'])
		dirs = [name for name in os.listdir(orgdir)
			if os.path.isdir(os.path.join(orgdir, name))]
		for d in dirs:
			# gather all paths
			gfs = []
			for base, tmp, files in os.walk(os.path.join(orgdir,d)):
					gfs += [os.path.join(base,f) for f 	 
						in files if f.endswith(('.gz', '.bb'))]
			for gf_path in gfs: 
				for pct_score in args['score']:		
					[score_min,score_max] = minmax[base_name(gf_path)].split(",")
					# calculate threshold score
					if score_min == 'NA':
						continue
					score_min,score_max = float(score_min),float(score_max) 
					thresh_score = score_min + (score_max-score_min)*float(pct_score)/100
					logger.info("MinMax stats for {}: Min={}, Max={}, {} pct_thresh={}".format(base_name(gf_path), score_min,score_max,pct_score,thresh_score))
					# is this safe? It searches /dirpath/grsnp_db/subdirs/gf.txt and replaces /grsnp_db/ with /grsnp_db_[score]/
					gf_path_out =gf_path.replace('/grsnp_db/','/grsnp_db_{}/'.format(pct_score))
					if not os.path.exists(os.path.split(gf_path_out)[0]):
						os.makedirs(os.path.split(gf_path_out)[0])
					gf_path_out_woext = os.path.join(os.path.split(gf_path_out)[0],base_name(gf_path_out))
					filter_by_score(gf_path, gf_path_out_woext,thresh_score)


	root_dir = os.path.dirname(os.path.realpath(__file__))
	readme = open(os.path.join(root_dir,"grsnp_db_readme.txt")).read()
	with open("grsnp_db_readme.txt","wb") as writer:
		writer.write(readme)
	print "FINISHED: Downloaded files from UCSC are placed in {}.  Database created in {}".format(os.path.join(args["data_dir"],"downloads"),os.path.join(args["data_dir"],"grsnp_db`"))