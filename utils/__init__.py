# -*- coding: utf-8 -*-

# Import modules
import pandas as pd
import asyncio
import json
import os

# import submodules
from datetime import datetime

# Import Telegram API submodules
from api import full_channel_req

'''
Creating functions
'''

# event loop
loop = asyncio.get_event_loop()

'''

JSON Encoder

'''
class JSONEncoder(json.JSONEncoder):
	'''
	'''
	def default(self, o):
		if isinstance(o, datetime) or isinstance(o, bytes):
			return str(o)

		return json.JSONEncoder.default(self, o)

# Get user-console request
def cmd_request_type(args):
	'''
	'''
	tm_channel = args['telegram_channel']
	batch_file = args['batch_file']

	req_type = 'channel' if tm_channel != None else 'batch'
	req_input = tm_channel if tm_channel != None else batch_file

	return req_type, req_input

# Process collected chats
def process_participants_count(client, channel_id):
	'''

	Returns:
		Participants count
	'''
	channel_request = loop.run_until_complete(
		full_channel_req(client, channel_id)
	)

	return channel_request.full_chat.participants_count


# Write collected chats
def write_collected_chats(
		chats_object,
		file,
		source,
		counter,
		req_type,
		client
	):
	'''

	chats_object -> chats metadata from API requests
	file -> a txt file to write chats' data (id, username)
	source -> channel requested by the user through cmd
	counter -> dict object to count mentioned channels
	req_type -> request type (channel request or from messages)
	client -> Telegram API client

	'''
	metadata = []
	for c in chats_object:
		try:
			id_ = c['id']
			username = c['username']
			if username != None:
				file.write(f'{id_}\n')

				# collect metadata
				if id_ in counter.keys():
					counter[id_]['counter'] += 1
					counter[id_][req_type] += 1
					src = counter[id_]['source']
					if source not in src:
						counter[id_]['source'].append(source)
				else:
					counter[id_] = {
						'username': username,
						'counter': 1,
						'from_messages': 1 \
							if req_type == 'from_messages' else 0,
						'channel_request': 1 \
							if req_type == 'channel_request' else 0,
						'channel_req_targeted_by': {
							'channels': ['self']
						},
						'source': [source]
					}

					# Telegram API -> full channel request
					channel_request = loop.run_until_complete(
						full_channel_req(client, id_)
					)

					channel_request = channel_request.to_dict()
					collected_chats = channel_request['chats']
				
					for ch in collected_chats:
						if ch['id'] == channel_request['full_chat']['id']:
							ch['participants_count'] = channel_request['full_chat']['participants_count']
						else:
							ch_id = ch['id']
							ch['participants_count'] = process_participants_count(client, ch_id)

							# write new id
							if ch['username'] != None:
								file.write(f'{ch_id}\n')

								# process in counter
								if ch_id in counter.keys():
									counter[ch_id]['counter'] += 1
									counter[ch_id]['channel_request'] += 1
									counter[ch_id]['channel_request_targeted_by']['channels'].append(username)
								else:
									counter[ch_id] = {
										'username': ch['username'],
										'counter': 1,
										'from_messages': 0,
										'channel_request': 1,
										'channel_req_targeted_by': {
											'channels': [username]
										},
										'source': [source]
									}

					metadata.extend(
						[
							i for i in collected_chats
							if i['username'] != None 
						]
					)

		except KeyError:
			pass

	df = pd.DataFrame(metadata)
	csv_path = './output/collected_chats.csv'
	df.to_csv(
		csv_path,
		encoding='utf-8',
		mode='a',
		index=False,
		header=not os.path.isfile(csv_path)
	)

	return counter
