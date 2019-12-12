# Play any audio file on YouTube on Google Home or Amazon Alexa

# This also turns ANY Python Code into an Alexa Skill or Google Home Action with a one-line decorator!!!!

I consider this one of my favorite accomplishments & crowning achievements in Smart Speaker Developer, all deriving from my past experience that preceded it (which is also on GitHub)

This will play the audio for any YouTube Video that you tell it. I primarily use this for Google Home.

google_youtube.py is one giant Lambda Function inside of AWS. I realize I could have had this in Google Cloud Functions but I was completely fine having this in Amazon Lambda, simply because changes reflect right away in Lambda and Google Functions take about 40-60 seconds to redeploy each time it's changed, which is probably due to Docker Containers

| Class/Function/Symbol | Purpose |
| ------ | ------ |
| def handle_exception | Decorator to put on a function to gracefully handle exceptions |
| def get_current_location | Detect if this function is ran in Google Cloud/Amazon AWS or Local OS |
| class AmazonAWS | If Amazon Echo will be using this code, this will handle the Amazon Echo specific responses/payload that Amazon Alexa/Echo requires for audio & text |
| class GoogleCloud | If Google Cloud will be using this code, this will handle the Google Cloud specific responses/payload that Google Cloud + Google Dialogflow requires for audio & text |
| def smart_speaker_decorator | Turns ANY Python code into Smart Speaker code, so users can simply just focus on coding which abstracts away the Voice specific stuff. Uses the AmazonAWS & GoogleCloud classes to determine the response for the device |
| def get_audio_url_from_web_url | If employers want this, contact me |
| def lambda_handler | I used Lambda Handler for Amazon AWS because I designed this as a Lambda Function to be used. If Google Home is using Amazon's Lambda (which it is), the Google Home endpoint is the Amazon API Gateway Function. I did this because of the quick rapid speed in which changes are reflected in Lambda while developing. I don't mind. |

# def smart_speaker_decorator

```python



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
```