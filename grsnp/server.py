import cherrypy, os, cgi, tempfile, sys, itertools
from mako.template import Template
from mako.lookup import TemplateLookup
from mako.exceptions import RichTraceback as MakoTraceback
from contextlib import closing
import sqlite3
import re
from operator import attrgetter
from multiprocessing import Process
import cPickle
from path import PathNode
from operator import itemgetter
from path import basename
import logging
from logging import FileHandler,StreamHandler
import json
import pdb
import hypergeom4 as grquery
from time import gmtime, strftime
import simplejson
import string
import random
import traceback
import dbcreator as uscsreader
import argparse

root_dir = os.path.dirname(os.path.realpath(__file__))
lookup = TemplateLookup(directories=[os.path.join(root_dir,"frontend/templates")])


sett = {}

DEBUG_MODE = True

logger = logging.getLogger('genomerunner.server')
hdlr = logging.FileHandler('genomerunner_server.log')
hdlr_std = StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.addHandler(hdlr_std)
logger.setLevel(logging.INFO)




# Each function in this class is a web page 
class WebUI(object):
	def __init__(self):
		
		
		orgs = self.get_org()
		# create all directories in the custom_data dir if they do not already exist
		for o in orgs:
			if not os.path.exists(sett["custom_dir"]): os.mkdir(sett["custom_dir"])
			cust_sub_dir = ["backgrounds","gfs","fois"]
			for c in cust_sub_dir:
				tmp = os.path.join(sett["custom_dir"],c)
				if not os.path.exists(tmp): os.mkdir(tmp)
				c_dir = os.path.join(sett["custom_dir"],c,o)
				if not os.path.exists(c_dir): os.mkdir(c_dir)

		self._index_html = {}

	@cherrypy.expose
	def index(self,organism=None):
		if not organism: organism = sett["default_organism"]
		if DEBUG_MODE or not organism in self._index_html:
			paths = PathNode()
			paths.name = "Root"
			paths.organisms = self.get_org() 
			paths.traverse(os.path.join(sett["data_dir"],sett["default_organism"]))
			tmpl = lookup.get_template("index.html")
			# Load default backgrounds


			self._index_html[organism] = tmpl.render(paths=paths,default_background=paths.get_backgrounds_combo(organism,sett["custom_dir"]),custom_gfs=paths.get_custom_gfs(organism,sett["custom_dir"]),demo_snps=paths.get_custom_fois(organism,sett["custom_dir"]))
		return self._index_html[organism]


	def get_org(self):
		organisms = []
		files = os.listdir(sett["data_dir"])
		for f in files:
			if f.find(".") == -1:
				organisms.append(f)
		return organisms

	

	@cherrypy.expose
	def query(self, bed_file=None,bed_data=None, background_file=None,background_data=None, 
				genomicfeature_file=None, niter=10, name="", score="", strand="",run_annotation=None, default_background = "",**kwargs):
		# Assign a random id
		id = ''.join(random.choice(string.lowercase+string.digits) for _ in range(32))
		while (os.path.exists(os.path.join(uploads_dir,id))):
			id = ''.join(random.choice(string.lowercase+string.digits) for _ in range(32))
		res_dir = os.path.join(results_dir,str(id))
		upload_dir = os.path.join(uploads_dir,str(id))
		os.mkdir(upload_dir)
		os.mkdir(os.path.join(upload_dir,"fois"))
		os.mkdir(os.path.join(upload_dir,"gfs"))
		res_dir = os.path.join(results_dir,str(id))
		os.mkdir(res_dir)
		fois = os.path.join(upload_dir,".fois") # contains a list of the paths to fois to run through the analysis
		gfs = os.path.join(upload_dir,".gfs") # contains a list of the paths to the gfs to run the fois against
		list_gfs = []

		runset = {}
		cherrypy.response.timeout = 3600

		try:
			jobname = kwargs["jobname"]
		except Exception, e:
			jobname = ""
			logger.error("id={}".format(id) + str(e))
		runset['job_name'] = id
		runset['time'] = strftime("%Y-%m-%d %H:%M:%S", gmtime())

			
		# load the FOI data
		bed_filename = ""

		data = ""
		demo_fois_dir = kwargs["demo_fois"] # If the user selects a demo set of FOIs to run, this will contain the directory
		if demo_fois_dir == "":
			try:
				with open(fois,"wb") as out_fois:
					# bed files uploaded
					if bed_file:
						if not isinstance(bed_file,(list)): bed_file = [bed_file] # makes a list if only one file uploaded
						for b in bed_file:
							bed_filename = b.filename
							f = os.path.join(upload_dir, "fois",bed_filename)
							extension = bed_filename.split(".")[-1]
							if not os.path.exists(f):
								with open(f, "wb") as out:
									if b != None and b.filename != "":
										logger.info("Received uploaded FOI file (name={}, id={})".format(bed_filename, id))
										while True:
											data = b.file.read(8192)
											# TODO find empty lines
											#data = os.linesep.join([s for s in data.splitlines() if s ])

											# strips out new lines not compatible with bed tools
											if extension not in ["gz","bb"]: data.replace("\r","")
											if not data:
												break
											out.write(data)			
										out_fois.write(f+"\n")
							else:
								logger.error("id={} Upload file already exists at {}".format(id,f))
								print "id={} Upload file already exists at {}".format(id,f)
					# custom data entered	
					elif bed_data!="":
						f = os.path.join(upload_dir,"fois", "custom.bed")
						with open(f, "wb") as out:
							bed_filename = "custom.bed"
							logger.info('Received raw text  FOI data (id={})'.format(id))
							data = bed_data
							data = os.linesep.join([s for s in data.splitlines() if s])
							out.write(data)		
						out_fois.write(f+"\n")	
					else:
						return "upload a file please"

			except Exception, e:
				logger.error("id={}".format(id) + str(e))
				return "ERROR: upload a file please"
			runset["fois"] = bed_filename
		else:

			# gather the FOI files in the demo directory
			ls_foi = [os.path.join(demo_fois_dir,f) for f in os.listdir(demo_fois_dir) if os.path.isfile(os.path.join(demo_fois_dir,f))]
			with open(fois,"wb") as writer:
				for f in ls_foi:
					writer.write(f+"\n")					


		# uploads custom genomic features
		try:
			with open(gfs,"a") as out_gfs:
				# bed files uploaded
				if genomicfeature_file:
					if not isinstance(genomicfeature_file,(list)): genomicfeature_file = [genomicfeature_file] # makes a list if only one file uploaded
					for b in genomicfeature_file:
						gfbed_filename = b.filename
						f = os.path.join(upload_dir, "gfs", gfbed_filename)
						extension = gfbed_filename.split(".")[-1]
						if not os.path.exists(f):
							with open(f, "wb") as out:
								if b != None and b.filename != "":
									logger.info("Received uploaded GF file (name={}, id={})".format(gfbed_filename, id))
									while True:
										data = b.file.read(8192)
										# TODO find empty lines
										#data = os.linesep.join([s for s in data.splitlines() if s ])

										# strips out new lines not compatible with bed tools
										if extension not in ["gz","bb"]: data.replace("\r","")
										if not data:
											break
										out.write(data)	
									if (base_name(f) not in list_gfs): out_gfs.write(f+"\n")
									list_gfs.append(base_name(f))		
						else:
							logger.error("id={} Uploaded GF file already exists at {}".format(id,f))
		except Exception, e:
			logger.error("id={}".format(id) + str(e))
			return "ERROR: Unable to process custom Genome annotation feature"

		# "kwargs" (Keyword Arguments) stands for all the other
		# fields from the HTML form besides bed_file, niter, name, score, and strand
		# These other fields are all the tables whose boxes might
		# have been checked.
		# Thus with this way of doing things, it is not possible to have a genomicfeature
		# with one of these reserved names. 
		organism,run = "",[]
		gfeatures = [k[5:] for k,v in kwargs.items()
			if k.startswith("file:") and v=="on"]
		with open(gfs,"a") as out_gfs:
			for g in gfeatures:
				if (base_name(g) not in list_gfs): out_gfs.write(g+"\n")
				list_gfs.append(base_name(g))

		for k,v in kwargs.items():
			# organism to use
			if "organism:" in v:
				organism = v.split(":")[-1]
			# which tests to run
			if "run:" in k and v=="on":
				run.append(k.split(":")[-1])
			# append custom list to be run
			if "grouprun:" in k and v == "on":
				gp_gfs_dir = k.split(":")[-1]
				ls_foi = [os.path.join(gp_gfs_dir,f) for f in os.listdir(gp_gfs_dir) if os.path.isfile(os.path.join(gp_gfs_dir,f))]
				with open(gfs,"a") as writer:
					for f in ls_foi:
						if (base_name(f) not in list_gfs): writer.write(f+"\n")
						list_gfs.append(base_name(f))	

		runset['organism']= organism	
		
		# load the background data if uploaded
		background_name = ""
		try:
			if background_file != None and background_file.filename != "":
				b = os.path.join(upload_dir,background_file.filename)
				logger.info('Received uploaded background file (id={})'.format(id))
				background_name = background_file.filename
				extension = background_name.split(".")[-1]
				with open(b, "wb") as out:
					while True:
						data = background_file.file.read(8192)
						# TODO find empty lines
						#data = os.linesep.join([s for s in data.splitlines() if not s.isspace() ])

						# strips out new lines not compatible with bed tools
						if extension not in ["gz","bb"]: data = data.replace("\r","")
						if not data:
							break
						out.write(data)			
			elif background_data != None and background_data != "":
				b = os.path.join(upload_dir,"custom.background")
				background_name = "custom.bed"
				with open(b, "wb") as out:
					logger.info('Received raw text background data (id={})'.format(id))
					data = background_file
					data = os.linesep.join([s for s in data.splitlines() if s])
					out.write(data)
			else:				
				background_name = default_background.split("/")[-1].split(".")[0] 
				b = default_background
		except Exception, e:
			logger.error("id={}".format(id) + str(e))
			return "ERROR: unable to upload background"
		runset['background'] = background_name


		# write the enrichment settings.
		path = os.path.join(res_dir, ".settings")
		set_info = {"Jobname:": str(id),
					"Time:": strftime("%Y-%m-%d %H:%M:%S", gmtime()),
					"Background:": background_name,
					"Organism:": organism}

		with open(path, 'wb') as sett:
			for k,v in set_info.iteritems():
				sett.write(k+"\t"+v+"\n")
		print "server.jobname: ", runset['job_name']
		# This starts the enrichment analysis in another OS process.
		# We know it is done when a file appears in the "results" directory
		# with the appropriate ID.
		p = Process(target=grquery.run_hypergeom,
				args=(fois,gfs,b,res_dir,runset['job_name'],True))				
		p.start()
		raise cherrypy.HTTPRedirect("result?id=%s" % id)

	@cherrypy.expose
	def result(self, id):
		path = os.path.join(results_dir, id)
		params = {}
		params["run_id"] = id
		params["detailed"] = "Results not yet available"
		params["matrix"] = "Results not yet available"
		print "PATH ",path
		if not os.path.exists(path):  #If file is empty...
			tmpl = lookup.get_template("enrichment_not_ready.html")
			return tmpl.render(id=id)
		tmpl = lookup.get_template("results.html")

		# Loads the progress file if it exists
		p = {"status":"","curprog":0,"progmax":0}
		progress_path = os.path.join(path,".prog")
		if os.path.exists(progress_path):
			with open(progress_path) as f:
				p = json.loads(f.read() )
		params["log"] = "###Run Settings###\n"
		sett_path = os.path.join(path,".settings")
		organism = ""
		if os.path.exists(sett_path):
			with open(sett_path) as f:
				tmp = f.read()	
				params["log"] = params["log"]+ tmp
				organism = [x.split("\t")[1] for x in tmp.split("\n") if x.split("\t")[0] == "Organism:"][0]
		params["organism"] = organism
		

		params["log"] = params["log"] + "\n###Run Log###\n"
		debug_path = os.path.join(path,".log")
		if os.path.exists(debug_path):
			with open(debug_path) as f:
				params["log"] = params["log"] + f.read()

		# loads results from results file		
		detailed_path = os.path.join(path,"detailed.gr")
		if os.path.exists(detailed_path):
			with open(detailed_path) as f:
				params["detailed"] = f.read()

		
		foi_names_path = os.path.join(os.path.join(uploads_dir, id),".fois")
		if os.path.exists(foi_names_path):
			with open(foi_names_path) as f:
				params["fois"] = [basename(x).split(".")[0] for x in f.read().split("\n") if x != ""]
		else:
			params["fois"] = ""

		params["zipfile"] = os.path.join(path,"GR_{}.tar.gz").format(id)

		params.update(p)
		try:
			rend_template = tmpl.render(**params)
		except Exception, e:
			traceback = MakoTraceback()
			str_error = ""
			for (filename, lineno, function, line) in traceback.traceback:
				str_error +=  "File %s, line %s, in %s" % (os.path.split(filename)[-1], lineno, function)
				str_error += "\n"
				str_error += line + "\n"
				str_error += "%s: %s" % (str(traceback.error.__class__.__name__), traceback.error)
			print str_error
			rend_template = str_error
		return rend_template


	@cherrypy.expose
	def get_heatmaps(self, run_id, organism):
		"""	Returns clustered and PCC matrix if they exist.
		'organism': is used to load detailed labels for the GFs.
		"""
		cherrypy.response.headers['Content-Type'] = 'application/json'
		trackdb = uscsreader.load_tabledata_dumpfiles(os.path.join(sett["data_dir"],organism,"trackDb"))
		results = {}
		path = os.path.join(results_dir, run_id)
		matrix_path = os.path.join(path,"matrix.txt")
		# Load clustered matrix
		matrix_clust_path  = os.path.join(path,"clustered.txt")
		if os.path.exists(matrix_path):
			with open(matrix_path) as f:
				results["matrix"] = f.read().replace("\"","")
		if os.path.exists(matrix_clust_path):
			with open(matrix_clust_path) as f:
				d = f.read()
				d = d.replace("\"","")
				if d[:6] != "ERROR:":
					results["matrix_data"] = d.replace("\"","")
					# d3 requires "gene_name" to be inserted into the first column
					tmp_data =  results["matrix_data"].split("\n")
					tmp = tmp_data[:] # this copy is passed onto the results page
					# insert the description column if it does not exist
					tmp_matrix = [x.split("\t") for x in tmp]
					if tmp_matrix[0][-1] != "Genomic Feature Description":
						tmp_matrix[0] += ["Genomic Feature Description"]
						for i in range(1,len(tmp)):
							description = [x["longLabel"] for x in trackdb if x["tableName"] == tmp_matrix[i][0]]
							if len(description) is not 0: description = description[0]
							else: description = ""
							tmp_matrix[i] += [description]					

					results["matrix_data"] = "\n".join(["\t".join(["gene_name",tmp[0]])]+tmp[1:])  
					results["matrix_data"] = results["matrix_data"]
					results["matrix_data_gf_description"] = "\t".join([x[-1] for x in tmp_matrix[1:]])
				else: results["matrix_data"] = d[6:]
		else: 
			results["matrix_data"] = "Heatmap will be available after the analysis is complete."
			results["matrix_data_gf_description"] = ""

		# Pearson's matrix results
		matrix_cor_path = os.path.join(path,"pcc_matrix.txt")
		if os.path.exists(matrix_cor_path):
			with open(matrix_cor_path) as f:
				d = f.read()
				d = d.replace("\"","")
				if d[:6] != "ERROR:":
					results["matrix_cor_data"] =  d.replace("\"","")
					results["matrix_cor"] = d.replace("\"","")
					# d3 requires "gene_name" to be inserted into the first column
					tmp =  results["matrix_cor"].split("\n")
					results["matrix_cor"] = "\n".join(["\t".join(["gene_name",tmp[0]])]+tmp[1:])  
					results["matrix_cor"] = results["matrix_cor"]
				else: results["matrix_cor"],results["matrix_cor_data"] = d[6:],""				

		else:
			results["matrix_cor_data"] = ""
			results["matrix_cor"] = "PCC heatmap will be available after the clustered matrix is created."
		pvalue_path = os.path.join(path,"pcc_matrix_pvalue.txt")
		if os.path.exists(pvalue_path):
			with open(pvalue_path) as f:
				d = f.read()
				results["matrix_cor_pvalues"] = d.replace("\"","")
				# d3 requires "gene_name" to be inserted into the first column
				tmp =  results["matrix_cor_pvalues"].split("\n")
				results["matrix_cor_pvalues"] = "\n".join(["\t".join(["gene_name",tmp[0]])]+tmp[1:])   
				results["matrix_cor_pvalues"] = results["matrix_cor_pvalues"]			
		else: 
			results["matrix_cor_pvalues"] = ""
		return simplejson.dumps(results)


	@cherrypy.expose
	def get_annotation(self,run_id,foi_name):
		annotation_path = os.path.join(os.path.join(results_dir,run_id,"annotations",foi_name + ".txt"))
		results = []
		if os.path.exists(annotation_path):
			with open(annotation_path) as f:
				# skip the comment lines
				cols = f.readline().rstrip()
				while cols[0] == "#":
					cols = f.readline().rstrip()
				cols = cols.split("\t")	
				results.append(cols)			
				for foi in f:
					if foi.strip() != "":
						results.append(foi.rstrip().split("\t"))
		return simplejson.dumps(results)

	@cherrypy.expose
	def get_enrichment(self,run_id,foi_name):
		enrichment_path = os.path.join(os.path.join(results_dir,run_id,"enrichment",foi_name + ".txt"))
		results = []
		if os.path.exists(enrichment_path):
			with open(enrichment_path) as f:
				# skip the comment lines
				cols = f.readline().rstrip()
				while cols[0] == "#":
					cols = f.readline().rstrip()
				cols = cols.split("\t")	
				results.append(cols)			
				for foi in f:
					if foi.strip() != "":
						results.append(foi.rstrip().split("\t"))
		return simplejson.dumps(results)

	@cherrypy.expose
	def meta(self, tbl,organism="hg19"):
		try:
			trackdb = uscsreader.load_tabledata_dumpfiles("data/{}/trackDb".format(organism))
			html = trackdb[map(itemgetter('tableName'),trackdb).index(tbl)]['html']
		except Exception, e:
			print traceback.format_exc()
			return "<h3>(No data found for {}.)</h3>".format(tbl)
		if html=='':
			return "<h3>(No data found for {}.)</h3>".format(tbl)
		else:
			return html

	@cherrypy.expose
	def get_detailed(self,run_id):
		""" loads results from detailed results file
		"""
		detailed_path,results = os.path.join(results_dir, run_id,"detailed.txt"),{"detailed": ""}		 
		if os.path.exists(detailed_path):
			with open(detailed_path) as f:
				results["detailed"] = f.read()
		return simplejson.dumps(results)

	@cherrypy.expose
	def get_progress(self, run_id):
		# Loads the progress file if it exists
		p = {"status":"","curprog":0,"progmax":0}
		progress_path = os.path.join(os.path.join(results_dir, run_id),".prog")
		if os.path.exists(progress_path):
			with open(progress_path) as f:
				p = json.loads(f.read())
		return simplejson.dumps(p)

	@cherrypy.expose
	def get_log(sefl,run_id):
		results = {"log": ""}
		log_path = os.path.join(os.path.join(results_dir, run_id),"gr_log.txt")
		if os.path.exists(log_path):
			with open(log_path) as f:
				results["log"] = f.read()
		return simplejson.dumps(results)

	@cherrypy.expose
	def enrichment_log(self, id):
		with open(os.path.join(results_dir,id+".log")) as sr:
			x = sr.read()
			return "<p>{}</p>".format(x.replace("\n","<br/>"))

	@cherrypy.expose
	def cite(self):
		tmpl = lookup.get_template("cite.html")
		return tmpl.render()

	@cherrypy.expose
	def news(self):
		tmpl = lookup.get_template("news.html")
		return tmpl.render()

	@cherrypy.expose
	def overview(self):
		tmpl = lookup.get_template("overview.html")
		return tmpl.render()

	@cherrypy.expose
	def demo(self):
		tmpl = lookup.get_template("demo.html")
		return tmpl.render()


def base_name(path):
    return ".".join(os.path.basename(path).split(".")[:-1])


if __name__ == "__main__":
	global static_dir,results_dir,media,root_dir,sett,uploads_dir
	root_dir = os.path.dirname(os.path.realpath(__file__))
	static_dir = os.path.abspath(os.path.join(root_dir, "frontend/static"))
	media = os.path.abspath(os.path.join(".","frontend/media"))
	parser = argparse.ArgumentParser(description="Starts the GenomeRunner server. Run from the directory containing the database (/grsnp_db) or use --data_dir")
	parser.add_argument("--port","-p", nargs="?", help="Socket port to start server on. Required to start server.") 
	parser.add_argument("--data_dir" , "-d", nargs="?", help="Set the directory containing the database (/grsnp_db). Use absolute path.", default="")
	parser.add_argument("--default_organism" , "-o", nargs="?", help="UCSC code for the default organism to use. Data for the organism must exist in the local GRSNP database.", default="hg19")
	args = vars(parser.parse_args())
	port = args["port"]

	data_dir = args["data_dir"]

	# global settings used by GR
	sett = {"data_dir":os.path.join(data_dir,"grsnp_db"),
				"run_files_dir": os.path.join(data_dir,"run_files_dir"),
				"default_organism":"hg19",
				"custom_dir": os.path.join(data_dir,"custom_data")
				}	



	#validate data directory
	if not os.path.exists(sett["data_dir"]):
		print "ERROR: {} does not exist. Please run grsnp.dbcreator or use --data_dir.".format(os.path.join(sett["data_dir"]))
		sys.exit()
	if not os.path.exists(os.path.join(sett["data_dir"],sett["default_organism"])):
		print "ERROR: Database for default organism {} does not exist. Either change the default organism or add data for that organism to the database at {} using the bedfilecreator".format(sett["default_organism"],sett["data_dir"])
		sys.exit()

	# validate run_files directory
	if not os.path.exists(sett["run_files_dir"]): os.mkdir(sett["run_files_dir"])
	results_dir = os.path.join(sett["run_files_dir"],"results")
	uploads_dir = os.path.join(sett["run_files_dir"],"uploads")	
	if not os.path.exists(results_dir):
		os.mkdir(results_dir)
	if not os.path.exists(uploads_dir):
		os.mkdir(uploads_dir)
	if port:
		cherrypy.server.max_request_body_size = 0
		cherrypy.config.update({
			"server.socket_port": int(port),
			"server.socket_host":"0.0.0.0"})
		conf = {os.path.join(root_dir,"/static"): 
					{"tools.staticdir.on": True,
					"tools.staticdir.dir": static_dir},
				results_dir: 
					{"tools.staticdir.on": True,
					"tools.staticdir.dir": os.path.abspath(results_dir)}
				}
			
		cherrypy.quickstart(WebUI(), "/gr", config=conf)

	else:
		print "WARNING: No port given. Server not started. Use --port flag to set port."