__author__ = 'sysnaut'


import json
import pprint
import requests

def measurements():
	print "*********** Inside Measurements **********"
	retdata = requests.get('http://localhost:8888/measurements')
	s = retdata.text
	p = json.loads(s)
	# pprint.pprint(p)

	for i in range(0,1):
		my_dict = p[i]
		eventvalue = []
		for key, value in my_dict.items():
			if key == 'eventTypes':
				eventvalue = value
				for ev in eventvalue:
					if ev == "ps:tools:blipp:linux:net:ping:rtt":
						for key, value in my_dict.items():
							if key == 'id':
								print "~~~~get the metadata id~~~"
								meta_id = value
								print meta_id
								metadata(meta_id)

def metadata(metadata_id):
	print "\n" + "*********Inside Metadata***********"
	retdata = requests.get('http://localhost:8888/metadata')
	s = retdata.text
	p = json.loads(s)
	# pprint.pprint(p)

	for i in range(0,1):
		my_dict = p[i]
		pvalue_list = []
		mvalue_list = []
		print type(my_dict)
		for key, value in my_dict.items():
			if key == 'eventType' and value == 'ps:tools:blipp:linux:net:ping:rtt':
				print type(my_dict)
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
											# for key, value in my_dict.items():
											# 	if key == 'eventType' or value == 'ps:tools:blipp:linux:net:ping:ttl':
											for key, value in my_dict.items():
												if key == 'id':
													print "get the data id"
													data_id = value
													print data_id
													data(data_id)

def data(data_id):
	print "\n" + "*********Inside data***********"
	req_url = 'http://localhost:8888/data/'+data_id
	retdata = requests.get(req_url)
	s = retdata.text
	p = json.loads(s)
	pprint.pprint(p)

	for i in range(0,1):
		my_dict = p[i]
		valuelist = []

	for key, value in my_dict.items():
		print value
		if key == 'value':
			valuelist = value
			print valuelist

def main():
	measurements()


if __name__=="__main__":
	main()