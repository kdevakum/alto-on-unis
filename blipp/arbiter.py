import ast
from ast import literal_eval
import time
import settings
from probe_runner import ProbeRunner
from multiprocessing import Process, Pipe
from copy import copy
from config_server import ConfigServer
from cmd_line_probe import Probe
import pprint
from operator import itemgetter
import sys
from collections import OrderedDict
import collections
import re

logger = settings.get_logger('arbiter')
PROBE_GRACE_PERIOD = 0  #10
final_list = []
ip_rtt_pair = {}
# ip_rtt_pair = collections.OrderedDict()

class Arbiter():
	'''

	The arbiter handles all of the Probes. It reloads the config every
	time the unis poll interval comes around. If new probes have been
	defined or if old probes removed, it starts and stops existing
	probes.

	Each probe is run by the ProbeRunner class in a separate
	subprocess. The arbiter has a dictionary which contains the
	process object for each probe, and the connection object to that
	process. The arbiter can send a "stop" string through the
	connection to give a probe the chance to shut down gracefully. If
	a probe does not shut down within the PROBE_GRACE_PERIOD, it will
	be killed.

	'''

	def __init__(self, config_obj, ip):
		self.config_obj = config_obj # BlippConfigure object
		# print self.config_obj
		self.proc_to_measurement = {} # {(proc, conn): measurement_dict, ...}
		self.stopped_procs = {} # {(proc, conn): time_stopped, ...}

	def run_probes(self, ip):
		new_m_list = self.config_obj.get_measurements()
		our_m_list = self.proc_to_measurement.values()

		for m in new_m_list:
			if not m in our_m_list:
				if settings.DEBUG:
					self._print_pc_diff(m, our_m_list)
				self._start_new_probe(m, ip)
				# print " \n ----- calling start_new_probe "

		for proc_conn, pc in self.proc_to_measurement.iteritems():
			print proc_conn
			if not pc in new_m_list:
				if settings.DEBUG:
					self._print_pc_diff(pc, new_m_list)
				self._stop_probe(proc_conn)
		return time.time()

	def reload_all(self):
		self._check_procs()
		self.config_obj.refresh()
		self._cleanup_stopped_probes()
		# self._stop_all()
		if self.config_obj.get("status", "ON").upper() == "OFF":
			self._stop_all()
			return time.time()
		#self._check_procs()
		return self.run_probes()

	def _start_new_probe(self, m, ip):
		logger.info("_start_new_probe", name=m["configuration"]["name"])
		logger.debug("_start_new_probe", config=pprint.pformat(m))
		pr = ProbeRunner(self.config_obj, m)
		parent_conn, child_conn = Pipe()
		# probe_proc = Process(target = pr.run, args = (child_conn,))
		# probe_proc.start()
		probe_proc = pr.run(child_conn, ip)
		self.proc_to_measurement[(probe_proc, parent_conn)] = m
		conn_tuple = (None, parent_conn)
		self._stop_probe(conn_tuple)


	def _stop_probe(self, proc_conn_tuple):
		try:
			logger.info('_stop_probe',
						msg="sending stop to " + self.proc_to_measurement[proc_conn_tuple]["configuration"]["name"])
		except Exception:
			logger.info('_stop_probe', msg="sending stop to " + self.proc_to_measurement[proc_conn_tuple]["id"])
		proc_conn_tuple[1].send("stop")
		self.stopped_procs[proc_conn_tuple] = 0   #time.time()
		for proc, conn in self.proc_to_measurement.keys():
			# self._stop_probe((proc, conn))
			result = []
			f = open('/home/sysnaut/github/blipp/blipp/mslist.txt', 'r')
			# print "\n Read !!"
			for line in f:
				result.append(line)
			result = map(lambda x: x.strip(), result)
			# print result
			for item in result:
				# print type(item)
				ip, rtt = re.split(':', item)
				rtt = float(rtt)
				ip_rtt_pair['IP']= ip
				ip_rtt_pair['RTT'] = rtt
				# print ip_rtt_pair
				final_list.append(ip_rtt_pair.copy())
			# print final_list
			final_list.sort(key=itemgetter('RTT'))
			print " \n === Sorted list === \n"
			print(final_list)
		exit(1)


	def _stop_all(self):
		'''
		Stop all probes... called when service status is OFF.
		'''
		logger.info('_stop_all')
		for proc, conn in self.proc_to_measurement.keys():
			self._stop_probe((proc, conn))
			break

	def _cleanup_stopped_probes(self):
		'''
		Join probes that were previously stopped, and kill probes that
		should have stopped but didn't.
		'''

		now = time.time()
		sp = copy(self.stopped_procs)
		for k,v in sp.iteritems():
			if not k[0].is_alive():
				k[0].join()
				del self.stopped_procs[k]
			elif v < (now - PROBE_GRACE_PERIOD):
				k[0].terminate()
				k[0].join()
				del self.stopped_procs[k]

	def _check_procs(self):
		'''
		Join probes that have died or exited.
		'''
		for proc, conn in self.proc_to_measurement.keys():
			if not proc.is_alive():
				proc.join()
				logger.warn('_check_procs', msg="a probe has exited", exitcode=proc.exitcode)
				m = self.proc_to_measurement.pop((proc, conn))
				m["configuration"]['status'] ='OFF'
				self.config_obj.unis.post("/measurements", m)

	def _print_pc_diff(self, pc, new_m_list):
		# a helper function for printing the difference between old and new probe configs
		# can be useful for debugging
		for npc in new_m_list:
			try:
				if npc["configuration"]["name"] == pc["configuration"]["name"]:
					for key in npc.keys():
						if key in pc.keys():
							if not pc[key] == npc[key]:
								logger.debug("reload_all",
											 msg=key +
											 " newval:" +
											 str(npc[key]) +
											 " oldval:" + str(pc[key]))
							else:
								logger.debug("reload_all", msg="new key/val: " + key + ": " + str(npc[key]))
					for key in pc.keys():
						if key not in npc.keys():
							logger.debug("reload_all", msg="deleted key/val: " + key + " :" + str(pc[key]))
			except:
				logger.debug("reload_all", msg="name not set")



def main(config, ip):
	a = Arbiter(config, ip)
	s = ConfigServer(config)
	last_reload_time = time.time()
	check_interval = (float)(config["properties"]["configurations"]["unis_poll_interval"])
	a.run_probes(ip)
	while s.listen(last_reload_time + check_interval - time.time()):
		a._stop_all()
		# last_reload_time = a.reload_all()
		check_interval = (float)(config["properties"]["configurations"]["unis_poll_interval"])
		logger.info("main", msg="check interval %d"%check_interval)
