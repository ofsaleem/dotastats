#Dota records generator v1.0.1
#Scrapes DOTABUFF for personal records of listed players and compares them to 
#generate a personal high-score table.
#
#Written by @onelivesleft, use as you will.  Contact me there, or at /u/-sideshow-.


#Full server path to writable cache file
#i.e. the cached.html file in the same folder as this script

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

CACHE = 'C:\Users\Omar\Documents\dotastats\cached.html' 


#Dotabuff IDs of the players (the number in the dotabuff URL)
PLAYERS = {
	66813455: "valo",
	66719714: "wardaddy",
	63821070: "fattie",
	69410750: "ScrubDaddy",
	51276331: "LONK",
	35241952: "DrZeuss",
	25117966: "Chester A. Arthur",
	52557656: "anonanimal",
	54456210: "Fixta Fernback",
	32456692: "wing"
	}


#Use the cache for this many seconds before rebuilding
#You can force a refresh by adding "?refresh=1" to the end of the url
REFRESH_AFTER = 60 * 60 * 2 


#Points for weekly / monthly / all time leaderboards 
POINTS = {
	0: 5,  #Points for each 1st position placing
	1: 3,  #Points for each 2nd position placing
	2: 1,  #Points for each 3rd position placing
	} 


#These are the URLs for dotabuff. Don't mess with them unless you know what you're doing
SITE = "http://dotabuff.com/players/%%d/records?date=%s" #
SITE_METRIC = "&metric=%s"
SITE_TOTALS = "total"
SITE_PERMIN = "minute"
SITE_MONTH = SITE % "month"
SITE_WEEK = SITE % "week"
SITE = SITE % ""
SITES = (SITE_WEEK, SITE_MONTH, SITE)
SITE_TITLES = {
	SITE: "ALL TIME",
	SITE_MONTH: "MONTH",
	SITE_WEEK: "WEEK",
	}
MATCH_URL = "http://dotabuff.com/matches/%d"


#Preferred order to display records in
PREFERRED_ORDER = [x.replace(" ", "&nbsp;") for x in [
	"Gold / Minute",
	"Experience / Minute",
	"Kills / Minute",
	"Assists / Minute",
	"Last Hits / Minute",
	"Denies / Minute",
	"Hero Damage / Minute",
	"Hero Healing / Minute",
	"Tower Damage / Minute",
	"Best KDA Ratio",
	"Kills",
	"Assists",
	"Last Hits",
	"Denies",
	"Gold",
	"Hero Damage",
	"Hero Healing",
	"Tower Damage",
	"Longest Match",
	"Longest Winning Streak",
	"Longest Losing Streak",
]]


# Records to ignore
VETO = set([x.replace(" ", "&nbsp;") for x in [
	"Kill Participation",
	"Experience",
]])



#####



try:
	from mod_python import apache
	from mod_python import util
except:
	apache = None
	util = []

import HTMLParser
import BeautifulSoup
import urllib2
import os, time


PLAYER_ID = {}

IMG_URL = "%s"


class MockApache(object):
	OK = True
			
if apache is None:
	apache = MockApache()
	
def get_position(p):	
	try:
		position = {0: "1st.", 1: "2nd.", 2: "3rd.", 10: "11th.", 11: "12th.", 12:"13th."}[p]
	except KeyError:
		try:
			position = {"1": "st.", "2": "nd.", 3: "rd."}[str(p)[-1]]
		except KeyError:
			position = "th."
		position = "%d%s" % (p+1, position)
	return position
	
OUTPUT_ERROR = [False]

def get_records(site, player, req):
	class Parser(HTMLParser.HTMLParser):
		player_name = None
		avatars = {}
		records = {}
		heroes = {}
		match_ids = {}
		in_title = False
		in_data = False
		in_header = False
		in_hero = False
		in_record = False
		div_count = 0
		img = None
		avatar = None
		alt = ""
		header = ""
		data = ""
		headers = []
		match_id = False
		def handle_starttag(self, tag, attrs):
			if tag == "div":
				if self.in_record:
					self.div_count += 1
				do_style = False
				style = ""
				for attr in attrs:
					if attr[0] == "class":
						if "title" in attr[1]:
							self.in_header = True
						elif "value" in attr[1]:
							self.in_data = True
						elif "record" in attr[1]:
							self.in_record = True
							self.div_count = 0
							do_style = True
					elif attr[0] == "style":
						style = attr[1]
				if do_style:
					for s in style.split("("):
						if s.startswith("/assets"):
							self.img = "http://www.dotabuff.com" + s.split(")")[0], self.alt
							break							
			elif tag == "img":
				is_avatar = False
				for attr in attrs:
					if attr[0] == "class":
						if "image-avatar" in attr[1]:
							is_avatar = True
					elif attr[0] == "alt":
						self.alt = attr[1]
					elif attr[0] == "src":
						img = attr[1]
				if is_avatar:
					self.avatar = img, self.alt
			elif tag == "title":
				self.in_title = True
			elif tag == "a" and self.in_record:
				link = ""
				for attr in attrs:
					if attr[0] == "href":
						link = attr[1].strip()
						break
				self.match_id = int(link.split("/")[-1])
		def handle_data(self, d):
			if self.in_header:
				self.header = d.strip().replace(" ","&nbsp;").replace("Most&nbsp;","").replace("Highest&nbsp;","").replace("&nbsp;Per&nbsp;", "&nbsp;/&nbsp;")
				self.in_header = False
			elif self.in_data:
				self.data = d.strip().replace(",","")
				self.in_data = False
			elif self.in_title:
				full_name = d.strip().split(" - ")[0].split(' ')#replace(" ","&nbsp;")
				if len(full_name[0]) < 5 and len(full_name) > 1:
					self.player_name = "&nbsp;".join(full_name[:2])
				else:
					self.player_name = full_name[0]
				self.in_title = False
		def handle_endtag(self, tag):
			if tag == "div":
				if self.in_record:
					if self.div_count > 0:
						self.div_count -= 1
					else:
						self.in_record = False
						if self.header and self.header not in VETO:							
							if self.header not in self.headers:
								self.headers.append(self.header)
							self.records[self.header] = self.data
							self.heroes[self.header] = self.img
							self.avatars[self.header] = self.avatar
							self.match_ids[self.header] = self.match_id
			elif tag == "title":
				self.in_title = False
	parser = Parser()
	page = []
	url = (site + SITE_METRIC) % (player, SITE_TOTALS)
	try:
		page.append(BeautifulSoup.BeautifulSoup(''.join([x for x in urllib2.urlopen(url)])).prettify())
	except:
		if not OUTPUT_ERROR[0]:
			OUTPUT_ERROR[0] = True
			req.write('<h2><a href="cached.html">Previously generated version</a></h2>\n')
		
		req.write('''<h2>Can't read dotabuff records: <a href="%s">%s</a></h2>\n''' % (url, url))
	url = (site + SITE_METRIC) % (player, SITE_PERMIN)
	try:
		page.append(BeautifulSoup.BeautifulSoup(''.join([x for x in urllib2.urlopen(url)])).prettify())
	except:
		if not OUTPUT_ERROR[0]:
			OUTPUT_ERROR[0] = True
			req.write('<h2><a href="cached.html">Previously generated version</a></h2>\n')
		req.write('''<h2>Can't read dotabuff records: <a href="%s">%s</a></h2>\n''' % (url, url))
	page[0] = page[0].replace("</html>", "").replace("</body>", "")
	page[1] = page[1].replace("<html>", "").replace("header>", "span>").replace("title>", "span>")
	page = ''.join(page)
	try:
		parser.feed(page)
	except IOError: 
		pass			
	return unicode(parser.player_name), parser.records, parser.headers, parser.match_ids, parser.heroes, parser.avatars

def url_name(player, match_id, img, avatar, site, records=None):
	if img is None:
		img = ["",""]
	if avatar is None:
		avatar = ["",""]
	if not records:
		record_text = ""
	else:
		records.sort()
		output = []
		prev_pos = records[0][0]
		for record in records:
			if record[0] != prev_pos:
				output.append("")
				prev_pos = record[0]
			if "Losing" in record[1]:
				output.append("%s (%d pts)" % (record[1], 0))
			else:
				output.append("%s (%d pts)" % (record[1], POINTS[record[0]]))
		record_text = '<div class="details">%s</div>' % '<br />'.join(output)
	if match_id is not None:
		return '<a class="record" href="%s" target="_blank"><img class="hero" title="%s" src="%s" /><img class="avatar" title="%s" src="%s" />%s%s</a>' % (MATCH_URL % match_id, img[1], IMG_URL % img[0], avatar[1], avatar[0], player, record_text)
	else:
		return '<a class="record" href="%s" target="_blank"><img class="avatar" title="%s" src="%s" />%s%s</a>' % (site, avatar[1], avatar[0], player, record_text)

OUTPUT = []

def handler(req):
	try:
		parameters = util.FieldStorage(req)
	except:
		parameters = ["refresh"]
	req.content_type = 'text/html'
	req.send_http_header()
	if "refresh" not in parameters and os.path.exists(CACHE) and os.stat(CACHE)[8] + REFRESH_AFTER > time.time():
		for line in (x for x in open(CACHE)):
			req.write(line)
	else:
		#open(CACHE, 'w').close()
		def out(*args):
			s = ','.join((str(x) for x in args))
			req.write(s)
			OUTPUT.append(s)
		out("""\
	<!DOCTYPE html>
	<html>
	<head>
		<meta http-equiv="content-type" content="text/html; charset=utf-8"></meta>
		<title>Dota Records</title>
		<link rel="shortcut icon" href="http://www.dota2.com/images/favicon.ico" type="image/x-icon" />
		<script src="//code.jquery.com/jquery-2.1.1.min.js"></script>
		<link href="http://code.jquery.com/ui/1.10.4/themes/ui-lightness/jquery-ui.css" rel="stylesheet">
		<script src="http://code.jquery.com/ui/1.10.4/jquery-ui.js"></script>
		<link href="//fonts.googleapis.com/css?family=Roboto" rel="stylesheet" type="text/css">
		<!-- style for paper -->
		<style>
		body {
            font-family: 'Roboto';
			background-image: url("470584434.png");
			background-repeat: no-repeat;
			background-attachment: fixed;
        }
		p {
            margin: 20px;
            padding: 80px 20px;
            border-radius: 20px;
            background-color: #eeeeee;
        }
		#progresslabel {
			color: #FFFFFF;
		}
		</style>
		<style>		
		    * {margin: 0;}
		    html, body {height: 100%;}
		    .wrapper {
				min-height: 100%;
				height: auto !important;
				height: 100%;
				margin: 0 auto -299px;
				padding: 2em;
		    }
		    .footer, .push {
		    	margin-left: 3em;
		    	height: 299px;		    	
		    }
			.footer img {
				position: fixed;
				bottom: 0;
				right: 0;
				z-index: -999;
				max-width: 350px; 
				max-height: 350px;
			}
			#main{margin-left: 1em; margin-right: 1em;}
			table {border-collapse:collapse; background-color:rgba(255,255,255,0.75); margin-top: 1em; box-shadow: 10px 10px 5px #888888;}
			th {text-align: left;padding-left: 0.5em;padding-right: 0.5em;margin: 0px; border-right:1px solid black}
			td {padding-left: 0.5em;padding-right: 0.5em;margin: 0; border-top: 1px solid black; border-bottom: 1px solid black; }
			tr.odd td {background-color: rgba(255,200,200,0.25); }
			tr.even td {background-color: rgba(255,255,200,0.25);}
			tr:hover td.left {color: #f80;}	
			tr:hover td.left-border {color: #f80;}	
			td.left {border-left: 1px solid black; text-align: right;}
			td.left-border {border-left: 1px solid black;}
			td.right {border-right: 1px solid black;}
			th.right {border-right: 1px solid black;}
			th.left {text-align: right;}
			.center {text-align: center; text-decoration:underline; padding-bottom: 1em; font-weight: normal; font-weight: bold;}
			h1 {font-size: 1.5em; margin-bottom: 1em; text-align: center;}
			.footer h1 {font-size: 1em;}
			img.hero {width: 32px; border: 1px solid black; position: relative; bottom: -4px; margin-right: 4px;}
			img.avatar {height: 18px; border: 1px solid black;  position: relative; bottom: -4px; margin-right: 4px;}
			a {text-decoration: none; color: #55F;}
			a:hover img.hero {border: 1px solid #f80;}
			a:hover img.avatar {border: 1px solid #f80;}
			a:hover {color: #f80;}
			.record {white-space: nowrap; position: relative; top: -2px;}
			td table.rankings {	display: none;  
								margin-left: -4em;
								background-color: white; 
								color: black; 
								border: 1px solid black;
								position: absolute; 
								margin-top: 0px;
								box-shadow: 5px 5px 0px 0 rgba(0,0,0,0.25);
			}
			td+td+td+td+td+td+td table.rankings  {margin-left: -6em;}	
			td table.rankings td { border: none; background-color: #eff; }
			td table.rankings td.score {color: #f80;}
			td table.rankings tr+tr td {border-top: 1px solid #888;}
			td:hover table.rankings {display: block; z-index: 999;}
			table.point-rankings td {font-style: normal; text-align: left;}
			th img {height: 2em; margin-left: 1em;}
			th table.point-rankings {	display: none;  
								background-color: white; 
								color: black; 
								border: 1px solid black;
								position: absolute; 
								margin-top: 0px;
								margin-left: 1em;
								box-shadow: 5px 5px 0px 0 rgba(0,0,0,0.25);
			}
			th table.point-rankings td { border: none; background-color: #eff; }
			th table.point-rankings td.score {color: #f80; text-align: right;}
			th table.point-rankings tr+tr td {border-top: 1px solid #888;}
			th:hover table.point-rankings {display: block; z-index: 998;}
			th:hover {color: #f80;}
			.details { 
				display:none;
				float: right; 
				position: absolute; 
				background-color: #fff; 
				border: 1px solid #888; 
				z-index: 999; 
				padding: 0.5em; 
				color: black; 
				font-size: 0.75em;
				box-shadow: 5px 5px 0px 0 rgba(0,0,0,0.25);
			}
			a:hover .details {display: block;}
				
			</style>
	</head>	
	<body>
		<div class="wrapper">
			<div id="main">
				<h1><img src="dotarecords.png" alt="Dota Records" /></h1>			
				<span class="hidden"><h1>Refreshing...</h1>
				<div id="progresslabel" style="text-align:center"></div>
				<div id="progressbar" style="width:750px; margin-left:auto; margin-right:auto"></div>
""")

		html = []
		point_rankings = {}
		points = {}
		player_avatars = {}
		records_needed = len(PLAYERS) * 3
		records_done = 0
		records_by_player = {}
		out("""
		<script type="text/javascript">
			$("#progressbar").progressbar({ 
				max: """ + str(records_needed) + """
			});
		</script>
		""")
				
		for site in SITES:
			players = {}			
			heroes = {}
			avatars = {}
			matches = {}
			highest = {}
			formats = {}
			urls = {}
			header_order = []
			points[site] = {}
			records_by_player[site] = {}
			for player in PLAYERS:				
				player_name, records, headers, match_ids, record_heroes, record_avatars = get_records(site, player, req)
				records_done += 1
				out("""
					<script type="text/javascript">
						$("#progressbar").progressbar("option", "value", """ + str(records_done) + """);
						$("#progresslabel").html(" """ + str(records_done) + """/""" + str(records_needed) + """ records done");
					</script>
					""" 
				)
				PLAYERS[player] = player_name
				PLAYER_ID[player_name] = player
				points[site][player_name] = 0				
				if player_name:
					if len(headers) > len(header_order):
						header_order = list(headers)
					for record in records:
						#out("[%s: %s]<br><br>" % (record, records[record]))
						if record not in highest:
							highest[record] = {}							
						records[record] = records[record].split(" ")[0]
						if '%' in records[record]:
							records[record] = records[record].replace("%","")
						if 'k' in records[record]:
							records[record] = records[record].replace('k','')
							records[record] = str(int(float(records[record]) * 1000))						
						if ":" in records[record]:
							parts = records[record].split(":")
							if len(parts) == 2:
								m,s = (int(x) for x in parts)
								h = 0
							else:
								h,m,s = (int(x) for x in parts)
							records[record] = (h,m,s)
							formats[record] = "%d:%02d:%02d"
						else:
							try:
								records[record] = int(records[record])
								formats[record] = "%d"
							except ValueError:
								records[record] = float(records[record])
								formats[record] = "%0.02f"							
						if records[record] in highest[record]:
							highest[record][records[record]].append(player_name)
						else:
							highest[record][records[record]] = [player_name]													
					players[player_name] = records
					matches[player_name] = match_ids
					heroes[player_name] = record_heroes
					avatars[player_name] = record_avatars
					for r in record_avatars:
						if record_avatars[r]:
							player_avatars[player_name] = record_avatars[r]
							break
					urls[player_name] = site % player

			order = []
			
					
			for header in PREFERRED_ORDER:		
				if header in header_order:
					order.append(header)
			for header in header_order:
				if header not in order:
					order.append(header)			
			header_order = order
			
			for i, record in enumerate(header_order):
				if i >= len(html):
					html.append(['<td class="left-border">%s</td>' % record])
				scores = list(reversed(sorted(highest[record])))
				#out(site.split("=")[-1], record, len(scores), "<br><br>")
				ranked = []
				for position, score in enumerate(scores):
					rbp = (position, record, score)
					if len(highest[record][score]) == 1:
						player = highest[record][score][0]
						if "Losing" in record:
							pass
						else:
							points[site][player] += POINTS[position]
						ranked = [formats[record] % score, url_name(player, matches[player][record], heroes[player][record], avatars[player][record], urls[player])]
						try:
							records_by_player[site][player].append(rbp)
						except KeyError:
							records_by_player[site][player] = [rbp]
					else:
						ranked = []
						for player in sorted(highest[record][score]):							
							ranked.append(url_name(player, matches[player][record], heroes[player][record], avatars[player][record], urls[player]))
							if "Losing" in record:
								pass
							else:
								points[site][player] += POINTS[position]
							try:
								records_by_player[site][player].append(rbp)
							except KeyError:
								records_by_player[site][player] = [rbp]
						if record.startswith('Longest'):
							joiner = ',<br />'
						else:
							joiner = ', '
						ranked = [formats[record] % score, joiner.join(ranked)]																	
					if position == 0:
						html[i].append(''.join(('<td class="left">', ranked[0], '</td><td class="right">', ranked[1],'<table class="rankings">')))
					if position <= 2:
						html[i][-1] += ''.join(('<tr><td>', get_position(position), '</td><td class="score">', ranked[0], '</td><td>', ranked[1], '</td></tr>'))
					if position == 2:
						html[i][-1] += '</table></td>'
						break
				if len(scores) < 3:
					html[i][-1] += '</table></td>'
			
		for site in SITES:
			point_rankings[site] = []
			players_by_points = {}			
			for player in points[site]:
				if player not in records_by_player[site]:
					records_by_player[site][player] = []
				try:
					tag = url_name(player, None, None, player_avatars[player], site % PLAYER_ID[player], records_by_player[site][player])
				except KeyError:
					tag = url_name(player, None, None, ("",""), site % PLAYER_ID[player], records_by_player[site][player])
				try:
					players_by_points[points[site][player]].append(tag)
				except KeyError:
					players_by_points[points[site][player]] = [tag]
			point_table = point_rankings[site]
			point_table.append('<table class="point-rankings">')
			offset = 0
			for i, p in enumerate(reversed(sorted(players_by_points))):
				if p > 0:
					if len(players_by_points[p]) == 1:
						point_table.append('<tr><td>%s</td><td class="score">%d</td><td>%s</td></tr>' % (get_position(i+offset), p, players_by_points[p][0]))
					else:
						point_table.append('<tr><td>%s</td><td class="score">%d</td><td>%s</td></tr>' % (get_position(i+offset), p, ", ".join(players_by_points[p])))
						offset += len(players_by_points[p]) - 1
			point_table.append("</table>")
			point_rankings[site] = ''.join(point_table)

			
		out("""</span>
				<script type="text/javascript">
					var css = document.createElement("style");
					css.type = "text/css";
					css.innerHTML = ".hidden { display: none; position: fixed}";
					document.head.appendChild(css);
					$('.hidden').empty();
				</script>
				<div align=center>
				<table>""")
		
		if OUTPUT_ERROR[0]:
			return apache.OK
		
		out("""\
					<tr style="background-color:rgba(255,255,200,0.25)";><th></th><th class="center" colspan=2>%s<img src="statsIcon.png" />%s</th><th class="center" colspan=2>%s<img src="statsIcon.png" />%s</th><th class="center" colspan=2>%s<img src="statsIcon.png" />%s</th></tr>
					<!--<tr><th>Record</th><th class="left">Score</th><th>Player(s)</th><th class="left">Score</th><th>Player(s)</th><th class="left">Score</th><th>Player(s)</th></tr>-->
	""" % (SITE_TITLES[SITES[0]], point_rankings[SITES[0]], SITE_TITLES[SITES[1]], point_rankings[SITES[1]], SITE_TITLES[SITES[2]], point_rankings[SITES[2]]))

		if OUTPUT_ERROR[0]:
			return apache.OK
			

		parity = 0	
		for row in html:
			parity = 1 - parity
			out("""\
					<tr class="%s">%s%s%s%s</tr>
""" % (("even", "odd")[parity], row[0], row[1], row[2], row[3]))

		out("""\
				</table>
			</div>
			</div>
			<div class="push"></div>
		</div>			
		<div class="footer">
			<img src="vtqqlogoround2-smalldota.png" />
		</div>
		<script>
		(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
		(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
			m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
		})(window,document,'script','//www.google-analytics.com/analytics.js','ga');

		ga('create', 'UA-56755363-2', 'auto');
		ga('send', 'pageview');

		</script>
	</body>
	</html>
	""")	
		if not OUTPUT_ERROR[0] and OUTPUT:
			try:
				outfile = open(CACHE, 'w')
			except IOError:
				outfile = None
			if outfile:
				for line in OUTPUT:
					outfile.write(line)
				outfile.close()

	return apache.OK