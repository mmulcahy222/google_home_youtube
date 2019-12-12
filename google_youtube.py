import json
import os
import pprint
import sys
import operator
import functools
import time
import datetime
import urllib
import urllib.parse 
import urllib.request
from collections import defaultdict
from urllib.parse import unquote
from urllib.request import Request, urlopen 
import re
import copy
import boto3
import random
import string
from botocore.exceptions import ClientError


origin_type = ''



def handle_exception(default_value=None):
	def wrap(f):
		def wrapped_f(*args,**kwargs):
			try:
				return f(*args,**kwargs)
			except:
				return default_value
		return wrapped_f
	return wrap


def get_current_location():
	#only purpose is for portability between windows system & google functions 
	#if in local windows system
	if os.name == 'nt':
		return 'windows'
	#if in amazon
	elif os.environ.get("AWS_EXECUTION_ENV") is not None:
		return 'amazon' 
	#if google cloud or other cloud like azure
	else:
		return 'google'



class AmazonAWS:
	@handle_exception()
	def get_request_json(self,request):
		return request
	@handle_exception()
	def get_intent(self,response_json):
		return response_json['request']['intent']['name']	
	@handle_exception({})
	def get_parameter(self,request_json,key):
		#called slot values here
		return request_json['request']['intent']['slots'][key]['value']
	@handle_exception({})
	def get_parameters(self,request_json):
		#format it for the inner function in a decorator
		#looks like {'any': 'thriller', 'time': '00:00'}
		slots = request_json['request']['intent']['slots']	
		parameters = {k:v.get("value") for k,v in slots.items()}		
		return parameters
	def device_text_response(self, **kwargs):
		speech_output = kwargs.get("speech_output","OK")
		session_attributes = kwargs.get("session_attributes",{})
		should_end_session = kwargs.get("should_end_session",0)
		response = {
			"sessionAttributes": session_attributes,
			"response": {
				"outputSpeech": {
					"type": "SSML",
					"ssml":"<speak>" + str(speech_output)[:7999] + "</speak>"
				},
			
				"reprompt": {
					"outputSpeech": {
						"type": "SSML",
						"ssml": "<speak>" + str(speech_output)[:7999] + "</speak>"
					}
				},
			},
			"shouldEndSession": should_end_session
		}
		return response
	def device_audio_response(self,**kwargs):
		alphanumeric = list(string.octdigits + string.ascii_letters)
		random.shuffle(alphanumeric)
		token = ''.join(alphanumeric[:15])
		response = {
			"response": {
				"outputSpeech": {
					"type": "SSML",
					"ssml":"<speak>" + kwargs.get("text_speech","Ok") + "</speak>"
				},
				"directives": [
					{
						"type": "AudioPlayer.Play",
						"playBehavior": "REPLACE_ALL",
						"audioItem": {
							"stream": {
								"token": token,
								"url": kwargs.get("audio_url",''),
								"offsetInMilliseconds": 0
							}
						}
					}
				],
				"shouldEndSession": 1
			}
		}
		return response
	def return_trip_json(self,contents):
		# AMAZON AWS JUST REQUIRES PAYLOAD (you're calling Lambda directly)
		#
		# if isinstance(contents,dict):
		# 	contents = json.dumps(contents)
		# return_dict = {
		# 	"statusCode": 200,
		# 	"headers": {"Content-Type": "application/json"},
		# 	"body": contents
		# }
		return contents
	def response_text_facade(self,contents):
		return self.return_trip_json(self.device_text_response(speech_output=contents))












class GoogleCloud:
	@handle_exception()
	def get_request_json(self,request):
		return json.loads(request['body'])
	@handle_exception()
	def get_intent(self,request_json):
		return request_json['queryResult']['intent']['displayName']
	@handle_exception({})
	def get_parameter(self,request_json,key):
		return request_json['queryResult']['parameters'][key]
	@handle_exception({})
	def get_parameters(self,request_json):
		#format it for the inner function in a decorator
		#looks like {'any': 'thriller', 'time': '00:00'}
		return request_json['queryResult']['parameters']
	def device_text_response(self,**kwargs):
		response_json = {
			"fulfillmentText": str(kwargs.get('speech_output','Ok')),
		}
		return json.dumps(response_json)
	def device_audio_response(self, **kwargs):
		response_json = {
			#"fulfillmentText": str(speech_output),
			"payload": {
				"google": {
					"richResponse": {
						"items": [
							{
								"simpleResponse": {
									"textToSpeech": kwargs.get("text_speech","Ok")
								}
							}
							,
							{
								"mediaResponse": {
									"mediaType": "AUDIO",
									"mediaObjects": [
										{
											"contentUrl": kwargs.get("audio_url",''),
											"description": "Audio Book",
											"name": "Audio Book"
										}
									]
								}
							}
						]
						,
						"suggestions": [
							{
								"title": "Suggestion"
							}
						]
					}
				}
			}
		}
		return json.dumps(response_json)
	def return_trip_json(self,contents):
		# Amazon API Gateway JSON is here (on way back to Dialogflow) because we're using Amazon API Gateway
		# Change Accordingly
		#if isinstance(contents,dict):
		#	contents = json.dumps(contents)
		return_dict = {
			"statusCode": 200,
			"headers": {"Content-Type": "application/json"},
			"body": contents
		}
		return return_dict
	def response_text_facade(self,contents):
		return self.return_trip_json(self.device_text_response(speech_output=contents))















class HTTPBrowser():
	@handle_exception()
	def __getattr__(self, name):
		def wrapper(*args, **kwargs):
			return None
		return wrapper
	@handle_exception()
	def get_http_header_host(self,event):
		return event['headers']['Host']
	def return_trip_json(self,contents):
		if isinstance(contents,dict):
			contents = json.dumps(contents)
		return_dict = {
			"statusCode": 200,
			"headers": {"Content-Type": "application/json"},
			"body": contents
		}
		return return_dict































def smart_speaker_decorator(type_of_output="text"):
	'''
	This is a Decorator to turn any regular code into an Alexa Skill or Google Home Skill using Amazon AWS for now
	'''
	def first_function(f):
		def second_function(*args,**kwargs):
			try:
				#get_item
				def get_item(iterable, index, default=None):
					try:
						return operator.getitem(iterable, index)
					except:
						return default
				#initial variables (lambda or google event,context)
				amazon_aws = AmazonAWS()
				google_cloud = GoogleCloud()
				http_browser = HTTPBrowser()
				event = get_item(args,0)
				context = get_item(args,1)
				global origin_type
				#########################
				#    DETERMINES THE ORIGIN
				#########################
				#	CHECKS TO SEE IF THERE'S A SESSION->APPLICATION->APPLICATIONID, characteristic of Amazon Event Objects.
				#It looks at the decorated get_request_json objects and sees if it put in an exception
				amazon_aws_alexa_request_json = amazon_aws.get_request_json(event)
				google_cloud_alexa_request_json = google_cloud.get_request_json(event)
				if google_cloud_alexa_request_json != None:
					origin_type = 'google_cloud'
					origin = google_cloud
				elif 'amazonaws' in str(http_browser.get_http_header_host(event)):
					origin_type = 'http_browser'
					origin = http_browser
				elif amazon_aws_alexa_request_json != None:
					origin_type = 'amazon_aws'
					origin = amazon_aws
				else:
					origin_type = 'http_browser'
					origin = http_browser
				#	Key Error is wrong attribute, Type Error is for doing getattr [] on a string
				#	Origin is for Google Cloud because most of the time we want Google Devices

				#########################
				#    END DETERMINE ORIGIN
				#########################
				#	Lambda Functions will read this. Not Google Cloud Functions yet. Google Cloud Functions deploy too slowly
				destination = amazon_aws
				#	Handle the event object that passes by differently
				request_json = origin.get_request_json(event)
				#	Get Intent
				intent = origin.get_intent(request_json)
				#	Amazon Slot values & parameters from Google Home
				parameters = origin.get_parameters(request_json)
				#	send intent to the function that called the decorator
				if isinstance(parameters,dict):
					parameters.update({"intent":intent})
				else:
					parameters = {}
				#	RUN ACTUAL CODE
				result = f(event,context,*args, **parameters)
				#	END DEBUG
				#	END RUN ACTUAL CODE
				#	
				#	
				#	IF THIS IS A WEB REQUEST IN THE AMAZON API GATEWAY!!! (LAMBDA URL)
				#	
				if 'http_browser' == origin_type:
					return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": pprint.pformat(locals()) }
				#
				#	Make Destination account for Google Cloud Functions if for some reason the processign is done there
				#
				#	If it's audio, send it in either Google or Amazon format
				#	IF DOING AUDIO, SEND IT A DICT WITH AUDIO_URL & TEXT_SPEECH!!
				#	Destination means in this case, format JSON in Amazon AWS format
				#
				
				if 'audio' == type_of_output:
					#usually for debugging, it will normally not be send that way
					if isinstance(result,dict) == False:
						result = {}
					return origin.return_trip_json(origin.device_audio_response(**result))
				#
				#	TEXT is the fallback for either Amazon or Google
				#
				elif 'text' == type_of_output:
					return origin.return_trip_json(origin.device_text_response(speech_output=result))
				#
				#	YOU should NEVER reach here. Fallback
				#
				return {"statusCode": 200, "headers": {"Content-Type": "application/json"}, "body": pprint.pformat(locals()) }
			except:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				exception_text = str(exc_type) + ' ' + str(exc_obj) + ' ' + str(exc_tb.tb_lineno)
				#
				# DEBUG
				# 
				#import traceback
				#traceback.print_exc()
				# 
				# AMAZON AWS ONLY
				# 
				#return {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}, 'body': exception_text + repr(locals())}
				#
				# IF EXTENDING THIS FOR GOOGLE CLOUD FUNCTIONS TO SEE THIS, ACTIVATE THE FOLLOWING
				#
				return origin.return_trip_json(origin.device_text_response(speech_output="Nothing was found. Say something else or be more specific. " + exception_text))
				#return origin.return_trip_json(origin.device_text_response(speech_output=exception_text + pprint.pformat(locals())))
		return second_function
	return first_function











def get_audio_url_from_web_url(url):
	ONLY EMPLOYERS GET TO SEE THIS. CONTACT ME 










def get_audio_url_from_web_url_april_2019(url):
	ONLY EMPLOYERS GET TO SEE THIS. CONTACT ME 













@smart_speaker_decorator('audio')
def lambda_handler(event,context,*args,**kwargs):
	#return "GOON"
	# return {"audio_url":"DEBUG","text_speech":"DEBUG"}
	intent = kwargs.get("intent","Unknown")
	choice = kwargs.get("choice","Unknown")
	original_choice = choice
	developer_key = '';
	#choice (for YouTube music)
	choice = choice.lower()
	choice = choice.replace('music','topic')
	list_video_url = 'https://www.googleapis.com/youtube/v3/search?q='+urllib.parse.quote(str(choice))+'&part=id,snippet&maxResults=20&type=video&key=' + developer_key
		#parameters intent because I dont' want to write new intents beyond the simple fallback
	if intent == 'youtube.parameters':
		time_choice = get_parameter(request_json,'time_range')
		time_days = {"today":1,"day":1,"week":7,"month":30,"year":365}.get(time_choice,365)
		date_begin_string = time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(time.time() - (60 * 60 * int(time_days))))
		#duration is only in youtube.parameters for now
		if get_parameter(request_json,'duration') == 'long':
			list_video_url = list_video_url + '&videoDuration=long'
		list_video_url = list_video_url + "&publishedAfter=" + date_begin_string
	#read url
	results = json.loads(urllib.request.urlopen(list_video_url).read())
	title_id_nodes = []
	for list_node in results['items']:
		video_id = list_node['id']['videoId']
		title = list_node['snippet']['title']
		title_id_nodes.append((video_id,title))
	#FIRST [0] IS THE FIRST RESULT THAT CAME UP (change if expanding for future results)
	#SECOND [0] IS THE VIDEO ID IN ACCORDANCE TO THE TUPLE ABOVE
	video_id = title_id_nodes[0][0]
	#FINISHED DOING ALL THE WORK TO GET VIDEO ID
	#
	#ALL OF THE FOLLOWING JUST TO GET THE DURATION
	get_first_duration_match = lambda list,index: list[index] if index < len(list) else 0
	try:
		video_info_url = 'https://www.googleapis.com/youtube/v3/videos?id=' + video_id + '&part=contentDetails&type=video&key=' + developer_key 
		results = json.loads(urllib.request.urlopen(video_info_url).read())
		duration_result = results['items'][0]['contentDetails']['duration']
		hours = get_first_duration_match(re.findall('(\d*)H',duration_result),0)
		minutes = get_first_duration_match(re.findall('(\d*)M',duration_result),0)
		seconds = get_first_duration_match(re.findall('(\d*)S',duration_result),0)
	except:
		duration = "Unknown"
	duration = ''
	if int(hours) == 1:
		duration += "{} hour ".format(hours)
	elif int(hours) > 1:
		duration += "{} hours ".format(hours)
	if int(minutes) == 1:
		duration += "{} minute ".format(minutes)
	elif int(minutes) > 1:
		duration += "{} minutes ".format(minutes)
	if duration == '':
		duration = "Unknown Time"
	duration = duration.strip()
	#END DURATION
	video_url = 'https://www.youtube.com/watch?v=' + video_id
	audio_url = get_audio_url_from_web_url_april_2019(video_url)
	return {"audio_url":audio_url,"text_speech":original_choice + ' ' + duration}




