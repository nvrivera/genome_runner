#!/usr/bin/env python
import sys, operator, os, numpy
from pybedtools import BedTool
import pybedtools
from collections import namedtuple
import cPickle
import logging
from logging import FileHandler,StreamHandler
from path import basename

logger = logging.getLogger('genomerunner.query')
hdlr = logging.FileHandler('genomerunner_server.log')
hdlr_std = StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.addHandler(hdlr_std)
logger.setLevel(logging.INFO)



# This class represents an Enrichment analysis result
# Lists of Enrichment objects are serialized to a Python Pickle
# file when an analysis is complete	
_Enrichment = namedtuple("Enrichment",
		["A","B","nA","nB","observed","expected","p_value","obsprox","expprox","pybed_p_value","pybed_expected","jaccard_observed","jaccard_p_value","jaccard_expected"])
class Enrichment(_Enrichment):
	def category(self):
		if self.expected == 0 or self.p_value > 0.05:
			return "nonsig"
		elif self.observed < self.expected:
			return "under"
		else:
			return "over"

def make_filter(name, score, strand):
	def filter(interval):
		if name and name != interval.name:
			return False
		if score and score > int(interval.score):
			return False
		if strand and strand != interval.strand:
			return False
		return True
	return filter
# TODO make organism specific!
def enrichment(id,a, b,background, organism,name=None, score=None, strand=None, n=10):
	"""Perform enrichment analysis between two BED files.

	a - path to Feature of Interest BED file
	b - path to Genomic Feature BED file
	n - number of Monte-Carlo iterations
	"""
	if (background != ""):
		logger.info("Using background file(id={})".format(id))
		tools = generate_background(a,b,background)
		A = tools["foi"]
		B = tools["gf"]
		genome = tools["background"]
		genome_fn = pybedtools.chromsizes_to_file(genome)

	else:
		logger.info("Using genome as background (id={})".format(id))
		A = BedTool(str(a))
		B = BedTool(str(b))
		genome = pybedtools.get_chromsizes_from_ucsc(organism)
		genome_fn = pybedtools.chromsizes_to_file(genome)
	

	organism = str(organism)
	flt = make_filter(name,score,strand)
	B.filter(flt).saveas()
	nA = len(A)
	nB = len(B)
	if not nA or not nB:
		return Enrichment(a,basename(b),nA,nB,0,0,1,0,0,1,0,0,1,0)
	print genome
	A.set_chromsizes(genome)
	B.set_chromsizes(genome)
	obs = len(A.intersect(B, u=True))
	# This is the Monte-Carlo step
	logger.info("RUNNING MONTE CARLO ({}): (id={})".format(b,id))
	write_progress(id, "Running Monte Carlo {}".format(b))
	dist = [len(A.shuffle(genome=organism,chrom=True).intersect(B, u=True)) for i in range(n)]
	exp = numpy.mean(dist)
	# gave p_value a value here so that it doesn't go out of scope, is this needed?
	p_value = 'NA'
	if exp == obs or (exp == 0 and obs == 0):
		p_value =1
	else:
		p_value = len([x for x in dist if x > obs]) / float(len(dist))
		p_value = min(p_value, 1 - p_value)
	
	# expected caluclated using pybed method
	logger.info("RUNNING RANDOM INTERSECTIONS ({}): (id={})".format(b,id))
	write_progress(id, "Running Random Intersections: {0}".format(b))
	pybeddist = A.randomintersection(B,iterations=n,shuffle_kwargs={'chrom': True})
	pybeddist = list(pybeddist)
	pybed_exp = numpy.mean(pybeddist)
	pybedp_value = 'NA'
	if pybed_exp == obs or (pybed_exp == 0 and obs == 0):
		pybedp_value =1
	else:
		pybedp_value = len([x for x in pybeddist if x > obs]) / float(len(pybeddist))
		pybedp_value = min(pybedp_value,1-pybedp_value)
	# epected calculated using jaccard method
	A2 = A.cut([0,1,2])
	B2 = B.cut([0,1,2])
	logger.info("Running Jaccard ({}): (id={})".format(b,id))
	write_progress(id, "Running Jaccard {}".format(b))

	resjaccard = A2.naive_jaccard(B2,genome_fn=genome_fn,iterations=n,shuffle_kwargs={'chrom':True})
	jaccard_dist = resjaccard[1]
	jaccard_obs = resjaccard[0]
	jaccard_exp = numpy.mean(resjaccard[1])
	jaccardp_value = 'NA'
	if jaccard_exp == jaccard_obs or (jaccard_exp  == 0 and jaccard_obs == 0):
		jaccardp_value =1
	else:
		jaccardp_value = len([x for x in jaccard_dist if x > obs]) / float(len(jaccard_dist))
		jaccardp_value = min(pybedp_value,1-pybedp_value)

	# run proximety analysis
	if True:
		logger.info("Running proximety {} (id={})".format(b,id))
		#stores the means of the distances for the MC
		expall =[]
		for i in range(n):
			tmp = A.shuffle(genome=organism).closest(B,d=True)
			# get the distances
			for t in tmp:
				expall.append(t[-1])
		# calculate the overal expected distance
		expall.append(numpy.mean(numpy.array(expall,float)))
		# calculate the expected mean for all of the runs
		expprox = numpy.mean(numpy.array(expall,float))	
		# proximety analysis for observed
		tmp = A.closest(B,d=True)
		obsall = []
		for t in tmp:
			obsall.append(t[-1])
		obsprox = numpy.mean(numpy.array(obsall,float))
	else:
		print "Skipping Proximity"
		obsprox = -1
		expprox = -1

	return Enrichment(a, basename(b), nA, nB, obs, exp, p_value,obsprox,expprox,pybedp_value,pybed_exp,jaccard_obs,jaccardp_value,jaccard_exp)

def generate_background(foipath,gfpath,background):
	"""accepts a background filepath
	generate a background and returns as a pybedtool.
	Replaces the chrom fields of the foi and the gf with the interval
	id from the background.
	"""
	bckg = BedTool(str(background))
	bckgnamed = "" 
	interval = 0 

	#inserts a unique interval id into the backgrounds name field
	for b in bckg:
		bckgnamed +=  "\t".join(b[:3])+'\t{}\t'.format(interval) + "\t".join(b[4:]) + "\n"
		interval += 1
	bckg = BedTool(bckgnamed,from_string=True)
	foi = BedTool(str(foipath))
	gf = BedTool(str(gfpath))
	# get the interval names from the background that the gf intersects with
	gf = bckg.intersect(gf)
	gfnamed = ""

	# insert the interval id into the chrom field of the gf and creates a new bedtool
	for g in gf:
		gfnamed += '{}\t'.format(g.name) + "\t".join(g[1:]) + "\n"
		#print "GFNAMED: " + str(g)
	gf = BedTool(gfnamed,from_string=True)
	#print "GFBEDTOOL: " + str(g)

	# inserts the interval id into the chrom column of the foi and creates a new bedtool
	foi = bckg.intersect(foi)
	foinamed = ""
	for f in foi:
		foinamed += '{}\t'.format(f.name) + "\t".join(f[1:])+"\n" 
		#print "FOINAMED: " + str(f)
	foi = BedTool(foinamed,from_string=True)

	#print "FOIBEDTOOL: " + str(f)
	bckgnamed = ""
	for b in bckg:
		bckgnamed += '{}\t'.format(b.name) + "\t".join(b[1:])+"\n"
	bckg = BedTool(bckgnamed,from_string=True)
	# converts the background to a genome dictionary
	chrstartend = [(g.start,g.end) for g in bckg]
	background = dict(zip([g.chrom for g in bckg],chrstartend))
	return {"foi": foi,"gf":gf,"background":background}


def run_enrichments(id, f, gfeatures,background, niter, name, score, strand,organism):
	"""
	Run one FOI file (f) against multiple GFs, then 
	save the result to the "results" directory.
	"""
	enrichments = []
	for gf in gfeatures:
		write_progress(id, "RUNNING ENRICHMENT ANALYSIS FOR: {}".format(gf))
		e = enrichment(id,f,gf,background,organism,name,score,strand,niter)
		enrichments.append(e)
		path = os.path.join("results", str(id))
		print "writing output"
		with open(path, "a") as strm:
			cPickle.dump(enrichments, strm)
	write_progress(id, "FINISHED")

def write_progress(id,line):
	"""Saves the current progress to the progress file
	"""

	path = os.path.join("results",str(id)+".prog")
	with open(path,"wb") as progfile:
		progfile.write(line)

		
def get_progress(id):
	"""returns the progress from the progress file
	"""

	path = os.path.join("results",str(id) + ".prog")
	if os.path.exists(path):
		return open(path).read()
	else:
		return ""

