import subprocess
import re
from utils import full_event_types
import shlex
import settings

logger = settings.get_logger('cmd_line_probe')
rtt_list = []
e_list = []
class Probe:

	def __init__(self, service, measurement):
		self.service = service
		self.measurement = measurement
		self.config = measurement["configuration"]
		self.command = self._substitute_command(str(self.config.get("command")), self.config)
		try:
			self.data_regex = re.compile(
				str(self.config["regex"]),
				flags=re.S|re.M)
		except Exception:
			self.data_regex = None
		try:
			self.EVENT_TYPES = self.config["eventTypes"]
		except Exception:
			self.EVENT_TYPES = {}

	def get_data(self, ip):
		proc = subprocess.Popen(self.command,
								stdout = subprocess.PIPE,
								stderr = subprocess.PIPE)
		output = proc.communicate()

		if not output[0]:
			raise CmdError(output[1])
		try:
			# print " --- Obt data ---- \n"
			data = self._extract_data(output[0])
			# print data
			rtt = data.get("rtt")
			ip_rtt_pair = ip+":"+rtt
			rtt_list.append(ip_rtt_pair)
			if len(rtt_list) == 0:
				self.get_data(ip)
			self.ping_result(rtt_list)
		except NonMatchingOutputError as e:
			logger.exc("get_data", e)
			return {}
		data = full_event_types(data, self.EVENT_TYPES)
		# print data
		return data

	def ping_result(self, rtt_list):
		file = '/home/sysnaut/github/blipp/blipp/mslist.txt'
		f = open(file, 'a')
		for item in rtt_list:
			f.write(str(item))
			f.write('\n')
		# f.close()
		return rtt_list

	def _extract_data(self, stdout):
		matches = self.data_regex.search(stdout)
		if not matches:
			raise NonMatchingOutputError(stdout)
		return matches.groupdict()

	def _substitute_command(self, command, config):
		''' command in form "ping $ADDRESS"
		config should have substitutions like "address": "example.com"
		Note; now more complex
		'''
		command = shlex.split(command)
		ret = []
		for item in command:
			# print item
			if item[0] == '$':
				if item[1:] in config:
					val = config[item[1:]]
					if isinstance(val, bool):
						if val:
							ret.append(item[1:])
					elif item[1]=="-":
						ret.append(item[1:])
						ret.append(str(val))
					else:
						ret.append(str(val))
			elif item:
				ret.append(item)
		logger.info('substitute_command', cmd=ret, name=self.config['name'])
		print str(ret)
		return ret


class NonMatchingOutputError(Exception):
	def __init__(self, output):
		self.output = output

	def __str__(self):
		return "output did not match regex... output: " + self.output



class CmdError(Exception):
	def __init__(self, stderr):
		self.stderr = stderr

	def __str__(self):
		return "Exception in command line probe: " + self.stderr
