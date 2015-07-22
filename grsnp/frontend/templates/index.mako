<body bgcolor="#A8D5FF" style="width: 1000px">

	<div class="topbar">
		<div class="topbar-inner">
			<div class="container-fluid">
				<a class="brand" href="./" style="font-family:Futura,'Helvetica Neue', Arial">
					<img width="200px" src="static/images/GRLogo.png" />
				</a>
				<ul class="pull-right">
					<li><a href="./overview">Overview</a></li>
					<li><a href="./news">News</a></li>
					<li><a href="./demo">Demo</a></li>
					<!-- <li><a href="./cite">How to Cite</a></li>
					<li><a href="http://sourceforge.net/projects/genomerunner/">GenomeRunner on SourceForge</a></li>
					<li><a href="./roadmap">Roadmap</a></li> -->
					<li><a href="https://mdozmorov.github.io/grdocs/" target="_blank">Help</a></li>
<!-- <div>
					<li><a href="./google">Google Group</a></li>
					<li><img width="30px" src="static/new-icon.jpg" alt="New: GenomeRunnerSNP Google Groups" /></li>
				</div> -->
			</ul>
			<!-- <img height="40px" src="static/images/logo-reversed-small.jpg" align="right" /> -->
		</div>
	</div>
</div>
<form id="frmQuery" name="frmQuery" action="query" method="post" enctype="multipart/form-data">
	<div id="content">
		<div class="well" style="margin-top: -15px; padding: 0px">			
			<h3>Select Database Version:</h3>
			${database_versions}		
			<h3>GenomeRunner: Functional interpretation of SNPs within regulatory context</h3>
			<p>
				<span style="font-size: 16px;"><span style="font-family:arial,helvetica,sans-serif;">GenomeRunner is a tool for annotation and enrichment analysis of the SNP sets by considering SNPs co-localization with functional/regulatory genome annotation data. GenomeRunner is particularly useful for interpretation of the collective regulatory impact of SNPs in non-protein coding regions. An example of GenomeRunner&#39;s results can be found in the analysis of Sjogren&#39;s syndrome GWAS (<em><a href="http://www.nature.com/ng/journal/v45/n11/full/ng.2792.html" target="_blank">Nature Genetics</a></em>) where it identified RFX5 transcription factor binding site as strongly enriched with the disease-associated SNPs.</span></p>
				<p>
					<br />
					<span style="font-size:16px;"><span style="font-family:arial,helvetica,sans-serif;">GenomeRunner calculates <a href="http://mdozmorov.github.io/grdocs/hypergeom4/enrichment.html">the enrichment p-values</a> by evaluating whether a SNP set co-localizes with regulatory datasets more often that could happen by chance. For three or more SNP sets, GenomeRunner performs <a href="https://mdozmorov.github.io/grdocs/hypergeom4/episimilarity.html"> a regulatory similarity analysis</a> by correlating SNP set-specific regulatory enrichment profiles. The downloadable results are visualized as interactive heatmaps and tables <a href="result?id=example">(Example)</a>.</span></span></p>
					<p>
					</p>
					</div>
					<div class="well">
						<div style="float:right;margin-top: 10px;">
							<b style="font-size:150%;">Organism:</b>
							${paths.org_as_html(id="org")} 
							<img class="helptooltip" title="Select organism-specific genome assembly" style="position: relative;top: 6px;" width=25 height=25 src="static/images/help-icon.png" alt="help"/>
						</div> 
						<h3>1. Select sets of SNPs of interest <img class="helptooltip" title="Upload files with rsIDs or genomic coordinates in BED format of SNPs of interest. At least 5 SNPs per set are required. Multiple file upload supported. Note: Avoid special characters and extra dots in file names. Do not use SNP IDs other than rsIDs." style="position: relative;top: 6px;" width=25 height=25 src="static/images/help-icon.png" alt="help"/>
						</h3>
						<div id="div_upload_fois"	style="float: left;margin-right: 13px;margin-top: 14px;"	>
							<h4 style="float:left;">Files:</h4><input type="file" id="inputbedfile" style="margin:5px" name="bed_file" multiple="multiple"/>
							<a href="http://genome.ucsc.edu/FAQ/FAQformat.html#format1">What should my data look like?</a>
						</div>
						<div id="div_demo_fois">
							<h4 style="font-size: 110%;float: left;margin-top: 15px;margin-right: 9px;;">Demo SNPs file sets: </h4>
							<div class="btn-group" id="btngroup_demo_fois" data-toggle="buttons-radio" data-toggle-name="demo_fois">
								<input type="hidden" style="margin-top: -3px;" name="demo_fois"/>
								${demo_snps}
							</div>
						</div>
						<div id="accfoi" class="accordion" style="padding-bottom: 0em;list-style:none;margin-top: 20px">       
							<h3  id="accordionheader"><a href="#" style="font-size:120%">Paste data in .BED format</a></h3>
							<div>          
								<table>
									<tr>
										<td>
											<textarea id="inputbeddata" rows=10 cols=95 style="margin:10px;margin-bottom:0px;" name="bed_data" wrap="off" disabled>
											</textarea>
										</td>
									</tr>
								</table>
							</div>
						</div>
					</div>	
					<div class="well">
						<h3 style="float:left">2. Define the background: ${default_background}<img class="helptooltip" title="By default, all common SNPs are used as a 'universe' to calculate the probability of SNPs in a set to be enriched with regulatory dataset" style="position: relative;top: 6px;" width=25 height=25 src="static/images/help-icon.png" alt="help"/>
						</h3>
						<!-- <input type="checkbox" style="font-size:120%;margin-top:1em" name="run_random">Run randomization test</input> -->
						<b style=" font-size:120%; margin-left: 10px"></b>
						<div class="accordion" style="padding-bottom: 1em;list-style:none;margin-top:2em">        
							<h3  id="accordionheader"><a href="#" style="font-size:120%">Upload custom background
								<img class="helptooltip" title="The 'background', or 'universe' of SNPs assessed in a study is critical for the correct p-value calculation. A set of SNPs of interest should be a subset of the background, else the p-values may be wrong.
								Default background selection &#40;all common SNPs from the latest organism-specific database&#41; is suitable when a genome-wide study was performed. When a microarray was used for SNPs profiling, it is advisable to use all SNPs on that array as a background." width=25 height=25 src="static/images/help-icon.png" alt="help"/>
							</a></h3>
							<div style="height=100px">       
								Bed File:
								<input type="file" id="inputbackgroundfile" style="margin:5px" name="background_file" />		
								<div id="accback" class="accordion" style="padding-bottom: 1em;list-style:none;margin-top: 20px">        
									<h3  id="accordionheader"><a href="#" style="font-size:120%">Paste data in .BED format</a></h3>							        
									<table style="margin-bottom:0px; padding-bottom:0px">
										<tr>
											<td>
												<textarea id="inputbackgrounddata" rows=5 cols=95 style="margin:10px" name="background_data" wrap="off" disabled>
												</textarea>
											</td>
										</tr>
									</table>
								</div>
							</div>
						</div>
					</div>
					<div class="well" style="padding-bottom:0em">
						<h3 style="float: left;margin-right: 10px;margin-top: 1px;">3. Select regulatory datasets:</h3>
						${custom_gfs}
						<br>
						<div id="accordGFSfile" class="accordion" style="padding-bottom: 0.5em;list-style:none; margin-top: 1em;" ><h3  id="accordionheader"><a id='gffileheader' href="#" style="font-size:120%; height: 100%">Upload regulatory bed files</a></h3>
							<ul>
								<li id="list-bedbackground">					
									Bed Files (.bed or .gz):
									<input type="file" id="inputgenomicfeaturefile" style="margin:5px" name="genomicfeature_file" multiple="multiple"/>
									<a href="http://genome.ucsc.edu/FAQ/FAQformat.html#format1">What should my data  look like?</a>
								</li>				
							</ul>
						</div>
						<div id="accordGFS" class="accordion" style="padding-bottom: 1em;list-style:none; margin-top: 0.5em;" onClick="renderCheckBoxTree()"> 
							<h3  id="accordionheader"><a id='gfselheader' href="#" style="font-size:120%; height: 100%">Choose regulatory datasets</a></h3>
							<div >								
								<div id="grfdroplist" style="display: table;">	
									<div id="divCheckBox" style="width: 70%; margin:15px; display: table-cell; verticle-align: top; visibility: hidden">
										<div style="display: table-row;">
											<div id="checkbuttons" style="margin-right: 1em;">
												<a class="btn" style="margin-top: 9px;"onClick="$('#jstree_gfs').jstree('open_all');">Expand All</a>
												<a class="btn" style="margin-top: 9px;" onClick="$('#jstree_gfs').jstree('close_all');">Collapse All</a>
												<a class="btn" style="margin-top: 9px;" onClick="$('#jstree_gfs').jstree('check_all');">Select All</a>
												<a class="btn" style="margin-top: 9px" onClick="$('#jstree_gfs').jstree('uncheck_all');">Deselect all</a>
												<a class="btn" style="margin-top: 9px;" id="descriptions">Track Descriptions</a>
											</div>
										</div>												
											<label>Search genomic features</label>
											<input style="margin-top:1.5em" id="txt_gfs_search" class='input' type="text"></input>
											<a class="btn" id="treeSelect" onClick="treeviewSelectSearchedClick()">Select</a>
											<a class="btn" id="treeSelect" onClick="treeviewDeselectSearchedClick()">Unselect</a>

									
											<div id="jstree_gfs" style="height:300px;overflow:auto"></div>
									</div>
									
								</div>			 

							</div>
						</div>
					</div>	

					<div class="well">
						<div>
							<button id="btnSubmit" class="btn btn-primary" onclick="submit_job()" type="submit" style="margin:1em">Submit job</button>									
							<input type="checkbox" id="disclaimer" checked="checked" style="margin:1em">I certify that I understand that GenomeRunner is for research purposes only.</input>
							<h3 id="upmessage" style="visibility:hidden;margin-left: -94px;margin-top: 3px;">Uploading files. Please do not refresh the page.</h3>
							<br>
						</div>
						<div class="accordion" style="margin-top:-46px;margin-bottom:18px">
						<h3 id='lblAdvancedFeatures'><a id='gfselheader' href="#" style="font-size:120%; height: 100%">Advanced Features</a></h3>
						<div>
							<label>Percent score threshold: ${pct_scores}</label>
							<img class="helptooltip" title="Increasing this number filters out more low-level signal in the regulatory datasets. If a regulatory dataset does not have a score, this setting is ignored" style="position: relative;top: 6px;" width=25 height=25 src="static/images/help-icon.png" alt="help"/>
							<input type="checkbox" style="font-size:120%;margin-top:1em;margin-left:3em" name="run_annot">Run annotation analysis</input><img class="helptooltip" title="Annotate each SNP in each set for the number of overlaps with the selected regulatory elements." style="position: relative;top: 6px;" width=25 height=25 src="static/images/help-icon.png" alt="help"/>
							<label style="margin-left:10px;visibility:hidden">Strand selection: </label>
							<select name="strand" style="visibility:hidden">
								<option value="both" selected>Both</option>
								<option value="plus">Plus</option>
								<option value="minus">Minus</option>
							</select>
							<img class="helptooltip" title="Sets whether or not to use strand-specific regulatory datasets, if available. If a regulatory dataset does not have a strand, this setting is ignored" style="position: relative;top: 6px;visibility:hidden" width=25 height=25 src="static/images/help-icon.png" alt="help"/>
						</div>
						<div class="ui-state-highlight ui-corner-all">
							<p><span class="ui-icon ui-icon-info" style="float: left; margin-right: .3em;">
							</span>GenomeRunner works best in Chrome (Windows) or Firefox. Mac users, use Safari.</p>
						</div>

					</div>
				</div>
			</form>
			<p style="text-align: center;">
				<span style="font-family:arial,helvetica,sans-serif;">You are the&nbsp;<img alt="stats counter" border="0" src="http://www.easycounter.com/counter.php?mdozmorov" />&nbsp;visitor</span>
			</p>
		</div>		
	</body>
