#/usr/bin/env python3.5
#Copyright (c) 2017 Christopher S Henning
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
from six.moves import configparser
from yattag import Doc
import os, glob
import pymysql.cursors
import sys
from datetime import datetime
import re, string
from urllib.parse import parse_qsl
from html import escape

# Read config file in
mydir = os.path.dirname(os.path.realpath(__file__))
configReader = configparser.RawConfigParser()
success = configReader.read(mydir + "/config.txt")
if not success:
   sys.exit("Missing configuration file {0}/config.txt".format(mydir))

config = {}
configitems =  ["SQLUSER", "SQLDB", "SQLLOC", "SQLPASS", "ZIPDIR"]
for var in configitems:
  try:
    config[var] = configReader.get("Firsts",var)
  except configparser.NoSectionError:
    sys.exit("Missing configuration section 'Firsts'")
  except (configparser.NoOptionError):
    sys.exit("Missing configuration item {0}. {1} are required.".format(var, ", ".join(configitems)))

eushards = ["Bloodiron", "Brisesol", "Brutwacht", "Gelidra", "Typhiria", "Zaviel"]
nashards = ["Deepwood", "Faeblight", "Greybriar", "Hailol", "Laethys", "Seastone", "Wolfsbane"]
kinds = ["All", "Achievement", "ArtifactCollection", "Item", "NPC", "Quest", "Recipe"]

# WSGI function
def application(environ, start_response):
    # the environment variable CONTENT_LENGTH may be empty or missing
    try:
        request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
        request_body_size = 0
    request_body = environ['wsgi.input'].read(request_body_size)
    env = dict(parse_qsl(request_body.decode()))
    # Initialize search parameters
    search = { 'player': "", 'shard': "", 'guild': "", 'kind': "", }
    for var in search:
       if var in env:
          search[var] = env[var]

    # Filter invalid input
    # An invalid Kind or Shard is reset to All
    # Player + Guild names should only contain "letters" (this includes accented letters)
    if search['kind'] not in kinds:
       search['kind'] = "All"
    if search['shard'] not in ["All"] + nashards + eushards:
       search['shard'] = "All"
    pattern = re.compile('\W+')
    pattern.sub('', search['player'])
    pattern.sub('', search['guild'])

    results = None
    # The model is to print verbose errors to console/log, and print a generic error to Web page
    # Initialize generic error here
    error = None
    # If a player name OR guild name is input, search the DB using all parameters
    if search['player'] != "" or search['guild'] != "":
      query = "SELECT Kind, What, Player, Shard, Guild, Stamp, Id FROM firsts WHERE "
      params = []
      args = []
      for var in search:
         # Don't need to search for shard or kind == All
         if search[var] != "" and (var not in ["kind", "shard"] or search[var] != "All"):
            params.append("{0}=%s ".format(var))
            args.append(search[var])
      query += "AND ".join(params)
      query += " ORDER BY Kind, Stamp"

      connection = None
      try:
         connection = pymysql.connect(host=config["SQLLOC"],
                             user=config["SQLUSER"],
                             password=config["SQLPASS"],
                             db=config["SQLDB"],
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
      except Exception as e:
         # This just kills one WSGI worker which will be respawned
         # Maybe find how to kill the WSGI server if we assume connection problems (eg wrong pass) are fatal
         print("Failed to connect to SQL database. {0}".format(e), file=sys.stderr)
         error = "Something went wrong with the SQL connection."

      if connection:
         try:
            with connection.cursor() as cursor:
               cursor.execute(query, args)
               results = cursor.fetchall()
         except Exception as e:
            print(e, file=sys.stderr)
            error = "Something went wrong with the SQL query."
         finally:
            connection.close()

    # OK, now start constructing HTML
    # The defaults dict makes the select dropdowns default to the input later
    doc, tag, text, line = Doc(defaults = {'shard': search['shard'], 'kind': search['kind']}).ttl()
    doc.asis('<!DOCTYPE html>')
    with tag('html'):
       with tag('head'):
          doc.stag('meta', ('http-equiv', "Content-Type"), ('content', "text/html; charset=utf-8"))
          doc.stag('link', ('rel', "stylesheet"), ('type', "text/css"), ('href', "style.css"))
          # <script> is NOT a void tag, so need with/pass
          with tag('script', ('src', "./sorttable.js"), ('type', "text/javascript")):
             pass
          with tag('script', ('src', "https://www.magelocdn.com/pack/rift/en/magelo-bar.js#1"), ('type', "text/javascript")):
             pass
          with tag('title'):
             text("RIFT Shard Firsts Search")
       with tag('body'):
          # Prevent Cloudflare interpreting Player@Shard as email
          doc.asis("<!--email_off-->")
          # Intro / search boxes
          with tag('h3'):
             text("Rift Shard Firsts BETA")
          line('p', "This site tells you the shard firsts for your character or guild.")
          with tag('p'):
             # Find date of latest zip
             date = "*unknown*"
             for myfile in glob.glob("{0}/Rift_Discoveries*.zip".format(config['ZIPDIR'])):
                match = re.search(r'\d{4}-\d{1,2}-\d{1,2}', myfile)
                date = datetime.strptime(match.group(), '%Y-%m-%d').date()
             text("Data is checked for from Trion daily. The latest is dated ")
             line('em', "{0}".format(date))
             text(". All information is straight from Trion's ")
             line('a', "public assets", href = "http://webcdn.triongames.com/addons/assets/")
             text(".")
          with tag('form', ('id', "firstfrom")):
             line('label', "Character: ", ('for', "player"))
             doc.stag('input', ('type', "text"), ('name', "player"), ('id', "player"), ('size', "14"), ('value', escape(search['player']) if search['player'] != "" else ""))
             line('label', " Shard: ", ('for', "shard"))
             with doc.select(('name', "shard"), ('id', "shard")):
                line('option', "All")
                with tag('optgroup', label = "NA"):
                   for shard in nashards:
                      with doc.option(value = shard):
                         text(shard)
                with tag('optgroup', label = "EU"):
                   for shard in eushards:
                      with doc.option(value = shard):
                         text(shard)
             line('label', " Guild: ", ('for', "guild"))
             doc.stag('input', ('type', "text"), ('name', "guild"), ('id', "guild"), ('size', "14"), ('value', escape(search['guild']) if search['guild'] != "" else ""))
             line('label', " Type: ", ('for', "kind"))
             with doc.select(('name', "kind"), ('id', "kind")):
                for kind in kinds:
                   with doc.option(value = kind):
                      text(kind)
             doc.stag('input', ('type', "submit"), ('formmethod', "post"))
          line('p', "Enter a player name and/or a guild name, then press Submit.")
          # If we had an earlier error, print the generic message here
          if error:
             line('p', error)
          # Print search results
          # The SQL query above can return firsts of 0-6 Kinds, but was only one query.
          # We want to print one table per Kind, and not have empty tables.
          # Thus the manual idx incrementing and starting a new table when a new Kind is encountered
          if results is not None:
            idx = 0
            reslen = len(results)
            for kind in kinds:
               if idx >= reslen: # End of results
                  break
               if results[idx]['Kind'] != kind: # No firsts for this Kind, so go to the next without starting a table for it
                  continue
               line('h4', "{0}s".format(kind))
               with tag('table', klass = 'sortable'):
                  with tag('thead'):
                     with tag('tr'):
                        for header in ['Player', 'Guild', 'What', 'Date (UTC)']:
                           line('th', header)
                  with tag('tbody'):
                     # Loop through and print rows until end or next table needed
                     while idx < reslen and results[idx]['Kind'] == kind:
                        with tag('tr'):
                           for cell in ['Player', 'Guild', 'What', 'Stamp']:
                              if cell == 'What':
                                with tag('td'):
                                   magurl = kind.lower()
                                   if magurl == "artifactcollection":
                                      magurl = "artifactset"
                                   line('a', results[idx][cell], href = "https://rift.magelo.com/en/{0}/{1}".format(magurl,results[idx]['Id']))
                              else:
                                 if cell == 'Player':
                                    results[idx][cell] += "@" + results[idx]['Shard']
                                 # The timestamp comes out as a datetime.datetime. Manually make everything a string.
                                 line('td', results[idx][cell].__str__())
                        idx += 1
       doc.asis('<!--/email_off-->')

    start_response('200 OK', [('Content-Type','text/html')])
    return [doc.getvalue().encode('utf8')]
