__author__ = 'sysnaut'

import json
import pprint
import requests


def measurements():
	print "*********** Inside Measurements **********"
	retdata = requests.get('http://localhost:8888/measurements')
	s = retdata.text
	p = json.loads(s)
	# print "Length of measurement list: " + str(len(p))

	for i in range(0, len(p)):
		my_dict = p[i]
		eventvalue = []

		for key, value in my_dict.items():
			if key == 'eventTypes':
				eventvalue = value
				for ev in eventvalue:
					if ev == "ps:tools:blipp:linux:net:ping:rtt":
						meta_id = my_dict.get('id')
						print "Metadata id: " + meta_id
						metadata(meta_id)


def metadata(metadata_id):
	print "\n" + "*********Inside Metadata***********"
	retdata = requests.get('http://localhost:8888/metadata')
	s = retdata.text
	p = json.loads(s)
	# pprint.pprint(p)
	# print "Length of metadata list: " + str(len(p))

	for i in range(0,len(p)):
		my_dict = p[i]
		pvalue_list = []
		mvalue_list = []
		if my_dict.get('eventType') == "ps:tools:blipp:linux:net:ping:rtt":
			for key, value in my_dict.items():
				if key == 'parameters':
					pvalue_list = value
					for key, value in pvalue_list.items():
						if key == 'measurement':
							mvalue_list = value
							for key, value in mvalue_list.items():
								if key == 'href':
									chk_measurement_id = value
									if chk_measurement_id == 'http://localhost:8888/measurements/'+metadata_id:
		 								data_id = my_dict.get('id')
		 								print "Data id: " + data_id
										data(data_id)


def data(data_id):
	print "\n" + "*********Inside data***********"
	req_url = 'http://localhost:8888/data/'+data_id
	retdata = requests.get(req_url)
	s = retdata.text
	p = json.loads(s)
	# pprint.pprint(p)

	for i in range(0,1):
		my_dict = p[i]
		valuelist = []
		value = my_dict.get('value')
		print "RTT : " + value


def main():
	measurements()


if __name__ == "__main__":
	main()