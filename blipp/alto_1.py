'''
Usage:
  blippd [options]

Options:
  -c FILE --config-file=FILE   The json formatted config file.
  -u URL --unis-url=URL        Where UNIS is running.
  -n NID --node-id=NID         ID of the node entry in UNIS that this blipp instance is running on.
  -s SID --service-id=SID      ID of the service entry in UNIS that this blipp should pull config from.
  -e ACTION --existing=ACTION  What to do with measurements already in UNIS (ignore|use) [default: ignore]
  --urn URN                    Specify urn to be used if blipp needs to create record on UNIS
'''

import sys
import pprint
import json
import socket
from copy import deepcopy
import multiprocessing
from multiprocessing import Process
import time
from joblib import Parallel, delayed
import docopt

from blipp_conf import BlippConfigure
import settings
import arbiter
from utils import merge_dicts, delete_nones


FIELD_LEN = 10
VERSION = "0.0.1"
REQUEST_TYPE = "1"
MESSAGE_LEN = 512
MAX_HOST_LEN = 256
SUCCESS = 1
FAILURE = 2
HOSTNAME = socket.gethostname()
logger = settings.get_logger('ablippd')

iplist = []


class LboneServer:
	def __init__(self, host, port):
		self.host = host
		self.port = int(port)

	def GetDepot(self, numDepots, hard, soft, duration, location, timeout):
		str_final_req = []
		str_final_req.append(self.PadField(VERSION))
		str_final_req.append(self.PadField(REQUEST_TYPE))
		str_final_req.append(self.PadField(str(numDepots)))
		str_final_req.append(self.PadField(str(hard)))
		str_final_req.append(self.PadField(str(soft)))
		str_final_req.append(self.PadField(str(duration)))
		str_final_req.append(location)
		str_request = ''.join(str_final_req)
		request = self.PadRequest(str_request)

		# Connecting to server 'dlt.incntre.iu.edu :6767'
		try:
			soc_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		except socket.error, msg:
			print 'Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1]
			sys.exit();
		soc_conn.connect((host, port))
		soc_conn.settimeout(timeout * 1000)
		req_bytes = str.encode(request)
		type(req_bytes)
		soc_conn.send(req_bytes)
		data = ''
		response = ''
		while True:
			data = soc_conn.recv(65536)
			if not data:
				break
			response += data
		if data:
			print response
		returnCode = response[0:10]
		if (returnCode == FAILURE):
			error = response[10:20]
			print "LBone error" + error
		else:
			return (self.parseDepotList(response[10:]))


	def PadField(self, field):
		str_field = []
		length = FIELD_LEN - len(field)
		for i in range(0, (length)):
			str_field.append(' ')
		str_field.append(field)
		fin_field = ''.join(str_field)
		return fin_field

	def PadRequest(self, request):
		str_request = []
		length = MESSAGE_LEN - len(request)
		str_request.append(request)
		for i in range(0, length):
			str_request.append('\0')
		fin_req = ''.join(str_request)
		return fin_req

	def parseDepotList(self, response):
		numofdepots = response[0:10]
		print "No of Depots: " + numofdepots
		depotlist = []
		print " List of IP's "
		for x in range(0, int(numofdepots)):
			starthost = x * (MAX_HOST_LEN + FIELD_LEN) + 10
			endhost = starthost + MAX_HOST_LEN
			startport = endhost
			endport = startport + 10
			host = response[starthost:endhost]
			host = host.rstrip()
			port = response[startport:endport]
			port = port.strip()
			final = host + ':' + port
			depotlist.append(final)
		print depotlist
		self.iterate_depot_list(depotlist)

	def iterate_depot_list(self, depotlist):
		for index, ipp in enumerate(depotlist):
			depotlist[index] = ipp
			ip, port = ipp.split(":")
			iplist.append(ip)
		self.parallel_process(iplist)

	def parallel_process(self, iplist):
		for ip in iplist:
			ip_process = Process(target=self._main, args=(ip, 10))
			ip_process.start()


	def get_options(self):
		options = docopt.docopt(__doc__)
		return options

	def _main(self, ip, seconds, options=None):
		ipadr = ip
		options = self.get_options() if not options else options
		conf = deepcopy(settings.STANDALONE_DEFAULTS)
		cconf = {
		"id": options.get("--service-id", None),
		"name": "blipp",
		"properties": {
		"configurations": {
		"unis_url": options.get("--unis-url", None),
		}
		}
		}
		delete_nones(cconf)
		merge_dicts(conf, cconf)

		if options['--config-file']:
			fconf = self.get_file_config(options['--config-file'], ip)
			merge_dicts(conf, fconf)
		bconf = BlippConfigure(initial_config=conf,
							   node_id=options['--node-id'],
							   pre_existing_measurements=options['--existing'],
							   urn=options['--urn'])
		bconf.initialize()
		# EK: don't need to refresh right away, right?
		# bconf.refresh()

		config = bconf.config
		logger.info('main', config=pprint.pformat(config))
		# logger.warn('NODE: ' + HOSTNAME, config=pprint.pformat(config))
		time.sleep(seconds)
		arbiter.main(bconf, ip)


	def get_file_config(self, filepath, ipaddr):
		try:
			with open(filepath) as f:
				conf = f.read()
				co = conf
				c = json.loads(co)

				c["properties"]["configurations"]["probes"]["ping"]["address"] = ipaddr
				# print c["properties"]["configurations"]["probes"]["ping"]["address"]
				config = json.loads(json.dumps(c))
				return config
		except IOError as e:
			logger.exc('get_file_config', e)
			logger.error('get_file_config',
						 msg="Could not open config file... exiting")
			exit(1)
		except ValueError as e:
			logger.exc('get_file_config', e)
			logger.error('get_file_config',
						 msg="Config file is not valid json... exiting")
		exit(1)



host = 'dlt.incntre.iu.edu'
port = 6767
numDepots = 50
hard = 25
soft = 25
duration = 30
location = "NULL"
timeout = 1000
x = LboneServer(host, port)
LboneServer.GetDepot(x, numDepots, hard, soft, duration, location, timeout)

