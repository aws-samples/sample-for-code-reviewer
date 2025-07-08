import json, boto3

payload = {} # Replace this payload

#modelId = 'anthropic.claude-3-5-sonnet-20240620-v1:0' 	# For Claude3.5 Sonnet
#modelId = 'anthropic.claude-3-opus-20240229-v1:0' 		  # For Claude3 Opus
modelId = 'anthropic.claude-3-sonnet-20240229-v1:0' 	  # For Claude3 Sonnet
#modelId = 'anthropic.claude-3-haiku-20240307-v1:0'		  # For Claude3 Haiku	

bedrock_runtime = boto3.client('bedrock-runtime')
response = bedrock_runtime.invoke_model(body=json.dumps(payload).encode('utf-8'), modelId=modelId)
response_text = response['body'].read().decode('utf-8')

print('Response:', response_text)