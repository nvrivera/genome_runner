#!/usr/bin/env python
import sys, operator, os, numpy
from pybedtools import BedTool
from collections import namedtuple
import cPickle

from path import basename

# This class represents an Enrichment analysis result
# Lists of Enrichment objects are serialized to a Python Pickle
# file when an analysis is complete	
_Enrichment = namedtuple("Enrichment",
		["A","B","nA","nB","observed","expected","p_value"])
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

def enrichment(a, b, name=None, score=None, strand=None, n=10):
	"""Perform enrichment analysis between two BED files.

	a - path to Feature of Interest BED file
	b - path to Genomic Feature BED file
	n - number of Monte-Carlo iterations
	"""
	flt = make_filter(name,score,strand)
	A = BedTool(str(a))
	B = BedTool(str(b)).filter(flt).saveas()
	nA = len(A)
	nB = len(B)
	if not nA or not nB:
		return Enrichment(a,basename(b),nA,nB,0,0,1)
	A.set_chromsizes("hg19")
	B.set_chromsizes("hg19")
	obs = len(A.intersect(B, u=True))
	# This is the Monte-Carlo step
	dist = [len(A.shuffle(g="data/hg19.genome").intersect(B, u=True)) for i in range(n)]
	exp = numpy.mean(dist)
	p_value = len([x for x in dist if x > obs]) / float(len(dist))
	p_value = min(p_value, 1 - p_value)
	return Enrichment(a, basename(b), nA, nB, obs, exp, p_value)

def run_enrichments(id, f, gfeatures, niter, name, score, strand):
	"""
	Run one FOI file (f) against multiple GFs, then 
	save the result to the "results" directory.
	"""
	enrichments = []
	for gf in gfeatures:
		e = enrichment(f,gf,name,score,strand,niter)
		enrichments.append(e)
	path = os.path.join("results", str(id))
	with open(path, "w") as strm:
		cPickle.dump(enrichments, strm)


