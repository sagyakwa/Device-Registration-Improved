import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup


class Register:
	post_website: object

	def __init__(self):
		self.session = requests.Session()
		self.login_url = 'http://fsunac-2.framingham.edu/j_security_check'
		self.request_url = 'http://fsunac-2.framingham.edu/administration'
		self.challenge_key = None
		self.cookies = None
		self.login()
		self.headers = {
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,'
			          'application/signed-exchange;v=b3',
			'Accept-Encoding': 'gzip, deflate',
			'Accept-Language': 'en-US, en;q=0.9',
			'Cache-Control': 'max-age=0',
			'Connection': 'keep-alive',
			'Content-Length': '196',
			'Content-Type': 'application/x-www-form-urlencoded',
			'DNT': '1',
			'Host': 'fsunac-2.framingham.edu',
			'Origin': 'http://fsunac-2.framingham.edu',
			'Referer': 'http://fsunac-2.framingham.edu/screen_preview',
			'Upgrade-Insecure-Requests': '1',
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
			              'Chrome/76.0.3809.132 Safari/537.36 '
		}

		self.data = {
			'com.ets.orginal.request.method': 'GET',
			'com.ets.orginal.request.URI': '/screen_preview',
			'challengeKey': f'{self.challenge_key}',
			'j_username': '',
			'j_password': '',
			'loginAuthenticate': 'false',
			'login': 'Login'
		}

	def login(self):
		"""
		This function handles logging in to the website
		:return: None
		"""
		with requests.Session() as session:
			# Get cookie from response
			website = session.get(self.login_url)
			self.cookies = website.cookies
			# Get challenge key!
			source = website.content
			self.challenge_key = get_challenge_key(source)

	def my_session(self, get_mac_address: object = False, add_device: object = False, purge_devices: object = False,
	               user_id: object = None,
	               username: object = None,
	               mac_address: object = None,
	               add_user: object = False,
	               search_user: object = False,
	               description: object = None,
	               sponsor: object = None) -> object:
		"""
		This function is the current session of the user (whoever is registering) and handles the major actions like
		adding and searching for users and devices. This keeps us logged in.

		:rtype: object
		:param get_mac_address: is a boolean value to get a user's mac address.
		:param add_device: is a boolean value to decide if we're going to add a device in this session.
		:param purge_devices: is a boolean value to decide if we're going to remove devices in this session.
		:param user_id: is the string ID of the user we're going to be searching.
		:param username: is the Framingham State username of the user we're going to be working with.
		:param mac_address: is the mac address of the user to either register or remove.
		:param add_user: is a boolean value to decide if we're going to add a user in this session.
		:param search_user: is a boolean value to decide if we're just searching for a user.
		:param description: is the string value of of the device type we're registering. eg(Playstation 4, Nintendo Switch).
		:param sponsor: is the string value of the person registering the device. NOT the user who wants their device registered.
		:return: None
		"""

		# We at least need this value ALL the time
		assert (username is not None), "Framingham State username is needed. If the person is not a student, " \
		                               "their first and last name will do fine. "

		with requests.Session() as session:
			web = session.post(self.login_url, cookies=self.cookies, data=self.data, headers=self.headers)
			self.challenge_key = get_challenge_key(web.content)
			if get_mac_address:
				return self.find_mac_address(session, username, user_id)
			elif add_user:
				return self.add_new_user(session, username, sponsor)
			elif search_user:
				return self.search_for_user(session, username)
			elif add_device:
				self.device_config(session, user_id, username, mac_address=mac_address, device_description=description,
				                   sponsor=sponsor, add=True)
			elif purge_devices:
				self.device_config(session, user_id, username, purge=True)

	def search_for_user(self, session: object, username: object) -> object:
		"""
		This function handles searching and returns True and the user_id or False and None.

		:param session: is the current session we're using for the request.
		:param username: is the Framingham State username of the person we're searching.
		:return: Boolean and (a user_id String or None).
		:rtype: object
		"""

		# We always need a username and a session
		assert (username is not None), "Framingham State username is needed. If the person is not a student, " \
		                               "their first and last name will do fine."
		assert (session is not None), "A session is needed!"

		# Search and prepare search content
		user_search = session.get('http://fsunac-2.framingham.edu/administration?view=showUsers')
		user_search_content = user_search.content
		self.challenge_key = get_challenge_key(user_search_content)
		# JSON key, value to be posted
		user_data = {
			'view': 'showUsers',
			'sort': 'userName',
			'sortDir': 'ASC',
			'challengeKey': f'{self.challenge_key}',
			'subview': 'http://fsunac-2.framingham.edu:80/administration?view=showUsersAll',
			'filterText': f'{username}',
			'filterTable': 'Apply'
		}
		search_result = session.post(self.request_url, data=user_data, headers=self.headers)
		soup = BeautifulSoup(search_result.content, 'lxml')

		# Look for username and return appropriate values.
		for name in soup.find_all('a', href="#"):
			if username in name:
				user_info = name['onclick']
				user_id = user_info.split()[2].replace("'", "").rstrip(',')
				return True, user_id
		return False, None

	def find_mac_address(self, session: object, username: object, user_id) -> object:
		"""
		This function looks for all mac addresses for a user, given a username and a user_id, which will come form the
		search_for_user function (if the user exists).

		:rtype: object
		:param session: is the current session we're using for the request.
		:param username: is the Framingham State username of the person we want to find the mac address for.
		:param user_id: is the user_id for the person (for search_for_user function).
		:return: A list of mac addresses or None.
		"""

		assert (username is not None), "Framingham State username is needed. If the person is not a student, " \
		                               "their first and last name will do fine."
		assert (session is not None), "A session is needed!"
		assert (user_id is not None), "A user_id is needed!"

		list_of_mac_addresses = []
		# Prepare JSON key, values for post
		user_data = {
			'view': 'showDevicesAll',
			'sort': 'userName',
			'sortDir': 'ASC',
			'subview': 'http://fsunac-2.framingham.edu:80/administration?view=showDevicesAll',
			'filterText': f'{username}',
			'filterTable': 'Apply'
		}
		# Prepare contents for a new post
		user_info = session.post(self.request_url, data=user_data)
		source_code = user_info.content
		self.challenge_key = get_challenge_key(source_code)
		# Prepare JSON key, values for second post
		view_devices_data = {
			'view': 'showDevicesAll',
			'sort': 'userName',
			'sortDir': 'ASC',
			'challengeKey': f'{self.challenge_key}',
			'subview': 'http://fsunac-2.framingham.edu:80/administration?view=showDevicesAll',
			'filterText': f'{username}',
			'userId': f'{user_id}',
			'showDevicesForUser': 'Devices For User'
		}
		view_devices = session.post(self.request_url, data=view_devices_data)
		soup = BeautifulSoup(view_devices.content, 'lxml')
		# Find all mac addresses and put in our list
		for mac_addr in soup.find_all('a', href="#"):
			if re.match('[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$', mac_addr.text, re.IGNORECASE):
				list_of_mac_addresses.append(mac_addr.text)

		# Return appropriate object (List or None)
		if len(list_of_mac_addresses) > 0:
			return list_of_mac_addresses
		else:
			return None

	def add_new_user(self, session: object, username: object, sponsor: object):
		"""
		This function adds a new user (Usually after getting a (False, None) return for the search_for_user function.
		When creating a new user, the required sections on the site are: username, email address, registration start time,
		registration end time,and A sponsor (the person doing the registering).

		:rtype: object
		:param session: is the session to use for our function.
		:param username: is the Framingham State username of the new user.
		:param sponsor: is the name of the person doing the addition of the new user.
		"""

		assert (username is not None), "Framingham State username is needed. If the person is not a student, " \
		                               "their first and last name will do fine."
		assert (session is not None), "A session is needed!"

		# Get the current date for the registration start time.
		current_date = datetime.now()
		registration_start_date = f'{current_date.strftime("%m/%d/%Y")} 0:00:00'
		# Registration end time is 2 years after the current time.
		registration_end_date = f"{current_date.strftime('%m')}/{current_date.strftime('%d')}/" \
		                        f"{int(current_date.strftime('%Y')) + 2} 0:00:00"
		# View all users to get challenge_key
		show_users = session.get('http://fsunac-2.framingham.edu/administration?view=showUsers')
		self.challenge_key = get_challenge_key(show_users.content)
		#  JSON key, value to add user and get challenge key
		add_user_data = {
			'view': 'showUsers',
			'sort': 'userName',
			'sortDir': 'ASC',
			'challengeKey': f'{self.challenge_key}',  # Not needed here for some reason, but just here!
			'subView': 'http://fsunac-2.framingham.edu:80/administration?view=showUsersAll',
			'filterText': '',
			'showUsersAdd': 'Add',
		}
		self.challenge_key = get_challenge_key(session.post(self.request_url, data=add_user_data).content)
		# JSON key, val to add new user. Empty fields are included as empty strings just in case API requires in the future.
		user_data = {
			'firstName': '',
			'middleName': '',
			'lastName': '',
			'regUserName': f'{username}',
			'emailAddress': f'{username}@student.framingham.edu',
			'phoneNumber': '',
			'regStartTime': f'{registration_start_date}',
			'regExpirationTime': f'{registration_end_date}',
			'sponsorEmail': f'{sponsor}',
			'userType': 'Web Authentication',
			'userMaxDevice': '',
			'challengeKey': f'{self.challenge_key}',
			'addUser': 'Submit'
		}
		# Finally, add the user through a post request.
		session.post(self.request_url, data=user_data, headers=self.headers)

	def device_config(self, session: object, user_id: object, username: object = None, mac_address: object = None,
	                  device_description: object = None, sponsor: object = None, add=None, purge=None):
		"""
		This function handles the addition and removal of devices.

		:rtype: object
		:param session: is the session to use for adding or removing a device.
		:param user_id: is the string ID for the user from (user_search function)
		:param username: is the username of the person we want to add/remove a device for.
		:param mac_address: is the mac address of the device we want to add/remove.
		:param device_description: is the name of the device we're going to add. (PS4, Nintendo Switch, etc)
		:param sponsor: is the name of the person registering.
		:param purge: is a boolean value to decide whether to remove all devices.
		:param add: is a boolean value to decide whether to add a device.
		"""
		pre_register_data = {
			'view': 'showUsers',
			'sort': 'userName',
			'sortDir': 'ASC',
			'challengeKey': f'{self.challenge_key}',
			'subView': 'http://fsunac-2.framingham.edu:80/administration?view=showUsersAll',
			'filterText': f'{username}',
			'userId': f'{user_id}',
			'showUsersAdd': 'Add',
		}
		pre_post = session.post('http://fsunac-2.framingham.edu/administration', data=pre_register_data)
		self.challenge_key = get_challenge_key(pre_post.content)

		register_data = {
			'regUserName': f'{username}',
			'macAddress': f'{mac_address}',
			'deviceGroup': 'Registered Guests',
			'devDesc': f'{device_description}',
			'sponsorEmail': f'{sponsor}',
			'challengeKey': f'{self.challenge_key}',
			'addDevice': 'Submit',
		}

		if add:
			session.post(self.request_url, data=register_data, headers=self.headers)
		elif purge:
			# TODO: FIX PURGE. DOES NOT PURGE. MIGHT BE DUE TO CHALLENGEKEY -> MIGHT NEED TO SEARCH USER FIRST,
			#  THEN GET CHALLENGE KEY FROM THAT
			purge_data = [
				('view', 'showUsers'),
				('sort', 'userName'),
				('sortDir', 'ASC'),
				('challengeKey', f'{self.challenge_key}'),
				('subView',
				 f'http://fsunac-2.framingham.edu:80/administration?view=showDevicesForUser&regUserName={username}'),
				('filterText', f'{username}'),
				# ('select_all', ''),
				# 'deviceId': '47262',
				# 'deviceId': '47263',
				('deleteDevice', 'Delete')
			]

			view_devices_data = {
				'view': 'showDevicesAll',
				'sort': 'userName',
				'sortDir': 'ASC',
				'challengeKey': f'{self.challenge_key}',
				'subview': 'http://fsunac-2.framingham.edu:80/administration?view=showDevicesAll',
				'filterText': f'{username}',
				'userId': f'{user_id}',
				'showDevicesForUser': 'Devices For User'
			}
			user_info = session.post(self.request_url, data=view_devices_data)
			self.challenge_key = get_challenge_key(user_info.content)

			soup = BeautifulSoup(user_info.content, 'lxml')
			for mac_id in soup.find_all('input'):
				if mac_id['name'] == 'deviceId':
					mac_tuple = (mac_id['name'], mac_id['value'])
					purge_data.append(mac_tuple)
			# Make json string to hold duplicate keys (deviceId in purge_data)
			new_purge_data = json.dumps(Container(purge_data))
			session.post(self.request_url, data=new_purge_data)


class Container(dict):
	"""Overload the items method to retain duplicate keys."""

	def __init__(self, items):
		super().__init__()
		self[""] = ""
		self._items = items

	def items(self):
		return self._items


def get_challenge_key(url_content: object) -> object:
	"""
	Function to get challenge key. The challenge key seems to be randomly generated on the first GET request
	(usually when you're getting cookies)

	:rtype: object
	:param url_content: is the HTML content (usually of a GET request)
	:return: String alphanumeric
	"""

	assert (url_content is not None), "No HTML content inputted!"

	soup = BeautifulSoup(url_content, 'lxml')
	for element in soup.find_all('form'):
		for key in element.find_all('input'):
			if key['name'] == 'challengeKey':
				return key['value']
