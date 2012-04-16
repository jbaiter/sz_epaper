#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

"""Usage: sz_epaper.py [options]
Download PDF E-Paper of German newspaper "Süddeutsche Zeitung".

Options:
  -h --help                 show this help message and exit
  -v --verbose              print status messages
  -u --username <user>      set username for SZ E-Paper (required)
  -p --password <pass>      set password for SZ E-Paper (required)
  -d --directory <dir>      select directory to store issue to [default: "./"]
  -e --edition <edition>    select edition to download (see --list-editions)
                            [default: "deutschland_full"]
  -i --issue <date>         select issue to download (e.g. 2012-04-14)
                            [default: "today"]
  --list-editions           List all available editions
"""

import logging
import os
import sys
from datetime import date

import packages.requests as requests
from packages.docopt import docopt

class SueddeutscheEPaper(object):
    LOGIN_URL = "https://epaper.sueddeutsche.de/digiPaper/servlet/attributeloginservlet"
    DOWNLOAD_URL = "http://www.sueddeutsche.de/app/epaper/pdfversion/dwlmanager.php/"
    EDITIONS = {'bayern_base': '%s_Bayernausgabe_basis.pdf',
                'bayern_full': '%s_Bayernausgabe_komplett.pdf',
                'deutschland_base': '%s_Deutschlandausgabe_basis.pdf',
                'deutschland_full': '%s_Deutschlandausgabe_komplett.pdf',
                'stadt_base': '%s_Stadtausgabe_basis.pdf',
                'stadt_full': '%s_Stadtausgabe_komplett.pdf'}
    
    def __init__(self, user, password):
        self._logger = logging.getLogger(__name__)
        self._session = requests.session()
        self._logger.info("Logging into SZ as user \"%s\"" % user)
        self._session.post(SueddeutscheEPaper.LOGIN_URL,
                           data={'sdeusername': user,
                                 'sdepasswort': password},
                           verify=False)

    def get_issue(self, edition='bayern_full', date=date.today()):
        # TODO: Throw an exception on holidays as well (e.g. no issue on
        #       25/12/2012)
        if date.weekday() == 6:
            raise Exception('No Sueddeutsche Zeitung on Sundays!')
        pdf_name = SueddeutscheEPaper.EDITIONS[edition] % date.strftime('%Y%m%d')
        pdf_raw = self._session.get(SueddeutscheEPaper.DOWNLOAD_URL+pdf_name,
                                     params={'file': pdf_name}).raw
        self._logger.info("Downloading issue \"%s\"" % pdf_name)
        # If an issue is not available to download, we get a file with
        # length 0, not a 404...
        if pdf_raw._fp.length == 0:
            raise Exception('Download of selected issue failed, maybe it is too old?')
        self._logger.debug("Size of issue is %d bytes" % pdf_raw._fp.length)
        return (pdf_name, pdf_raw)


if __name__ == '__main__':
    options, arguments = docopt(__doc__)
    if options.verbose:
        logging.basicConfig(level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
    if options.list_editions:
        print "Available editions:"
        for edition in SueddeutscheEPaper.EDITIONS.keys():
            print "    %s" % edition
        sys.exit(0)

    if not options.username or not options.password:
        print "ERROR: You must specify a username and a password.\n"
        print __doc__
        sys.exit(0)

    if options.issue == "today":
        issue_date = date.today()
    else:
        issue_date = date(*(int(x) for x in options.issue.split('-')))

    sz = SueddeutscheEPaper(options.username, options.password)
    issue_name, issue_fobj = sz.get_issue(options.edition, issue_date)

    with open(os.path.join(options.directory, issue_name), 'w') as fp:
        while True:
            chunk = issue_fobj.read(64*1024)
            if not chunk:
                break
            fp.write(chunk)

    if issue_date >= date.today():
        try: os.remove(os.path.join(options.directory, "current.pdf"))
        except: pass
        os.symlink(os.path.join(options.directory, issue_name),
                   os.path.join(options.directory, "current.pdf"))
