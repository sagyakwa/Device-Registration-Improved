import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup


class DeviceRegistration:
	post_website: object

	def __init__(self):
		self.session = requests.Session()
		self.login_url = 'http://fsunac-1.framingham.edu/j_security_check'
		self.request_url = 'http://fsunac-1.framingham.edu/administration'
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
			'Host': 'fsunac-1.framingham.edu',
			'Origin': 'http://fsunac-1.framingham.edu',
			'Referer': 'http://fsunac-1.framingham.edu/screen_preview',
			'Upgrade-Insecure-Requests': '1',
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
			              'Chrome/76.0.3809.132 Safari/537.36 '
		}

		self.data = {
			'com.ets.orginal.request.method': 'GET',
			'com.ets.orginal.request.URI': '/screen_preview',
			'challengeKey': f'{self.challenge_key}',
			'j_username': 'campus\\nacreg1',
			'j_password': 'Fsu8675309',
			'loginAuthenticate': 'false',
			'login': 'Login'
		}

	def login(self):
		with requests.Session() as session:
			# Get cookie from response
			website = session.get(self.request_url)
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

		:rtype: object
		:param get_mac_address:
		:param add_device:
		:param purge_devices:
		:param user_id:
		:param username:
		:param mac_address:
		:param add_user:
		:param search_user:
		:param description:
		:param sponsor:
		:return:
		"""
		with requests.Session() as session:
			web = session.post(self.login_url, cookies=self.cookies, data=self.data, headers=self.headers)
			self.challenge_key = get_challenge_key(web.content)
			if get_mac_address:
				return self.find_mac_address(session, username, user_id)
			elif add_user:
				return self.add_new_user(session, username, sponsor)
			elif search_user:
				return self.search(session, username)
			elif add_device:
				self.devices(session, user_id, username, mac_address=mac_address, description=description,
				             sponsor=sponsor, add=True)
			elif purge_devices:
				self.devices(session, user_id, username, purge=True)

	def search(self, session: object, username: object) -> object:
		"""

		:param session:
		:param username:
		:return:
		:rtype: object
		"""
		user_info = []
		search_user = session.get('http://fsunac-1.framingham.edu/administration?view=showUsers')
		source = search_user.content
		self.challenge_key = get_challenge_key(source)
		user_data = {
			'view': 'showUsers',
			'sort': 'userName',
			'sortDir': 'ASC',
			'challengeKey': f'{self.challenge_key}',
			'subview': 'http://fsunac-1.framingham.edu:80/administration?view=showUsersAll',
			'filterText': f'{username}',
			'filterTable': 'Apply'
		}
		result = session.post(self.request_url, data=user_data, headers=self.headers)
		soup = BeautifulSoup(result.content, 'lxml')

		for name in soup.find_all('a', href="#"):
			if username in name:
				user_info = name['onclick']
				user_id = user_info.split()[2].replace("'", "").rstrip(',')
				return True, user_id
		return False, None

	def find_mac_address(self, session: object, username: object, user_id) -> object:
		"""

		:rtype: object
		:param session:
		:param username:
		:return:
		"""
		list_of_mac_addresses = []
		user_data = {
			'view': 'showDevicesAll',
			'sort': 'userName',
			'sortDir': 'ASC',
			'subview': 'http://fsunac-1.framingham.edu:80/administration?view=showDevicesAll',
			'filterText': f'{username}',
			'filterTable': 'Apply'
		}
		user_info = session.post(self.request_url, data=user_data)
		source_code = user_info.content
		self.challenge_key = get_challenge_key(source_code)
		view_devices_data = {
			'view': 'showDevicesAll',
			'sort': 'userName',
			'sortDir': 'ASC',
			'challengeKey': f'{self.challenge_key}',
			'subview': 'http://fsunac-1.framingham.edu:80/administration?view=showDevicesAll',
			'filterText': f'{username}',
			'userId': f'{user_id}',
			'showDevicesForUser': 'Devices For User'
		}
		view_devices = session.post(self.request_url, data=view_devices_data)
		soup = BeautifulSoup(view_devices.content, 'lxml')
		for mac_addr in soup.find_all('a', href="#"):
			if re.match('[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$', mac_addr.text, re.IGNORECASE):
				list_of_mac_addresses.append(mac_addr.text)

		if len(list_of_mac_addresses) > 0:
			return list_of_mac_addresses
		else:
			return None

	def add_new_user(self, session: object, username: object, sponsor: object):
		"""

		:rtype: object
		:param session:
		:param username:
		:param sponsor:
		"""
		current_date = datetime.now()
		registration_start_date = f'{current_date.strftime("%m/%d/%Y")} 0:00:00'
		registration_end_date = f"{current_date.strftime('%m')}/{current_date.strftime('%d')}/" \
		                        f"{int(current_date.strftime('%Y')) + 2} 0:00:00"
		# View all users to get challenge_key
		show_users = session.get('http://fsunac-1.framingham.edu/administration?view=showUsers')
		self.challenge_key = get_challenge_key(show_users.content)
		#  Post to add user and get challenge key
		add_user_data = {
			'view': 'showUsers',
			'sort': 'userName',
			'sortDir': 'ASC',
			'challengeKey': f'{self.challenge_key}',  # Not needed here for some reason
			'subView': 'http://fsunac-1.framingham.edu:80/administration?view=showUsersAll',
			'filterText': '',
			'showUsersAdd': 'Add',
		}
		self.challenge_key = get_challenge_key(session.post(self.request_url, data=add_user_data).content)
		# Post request to add new user
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
		session.post(self.request_url, data=user_data, headers=self.headers)

	def devices(self, session: object, user_id: object, username: object = None, mac_address: object = None,
	            description: object = None, sponsor: object = None, add=None, purge=None):
		"""

		:rtype: object
		:param session:
		:param user_id:
		:param username:
		:param mac_address:
		:param description:
		:param sponsor:
		:param purge:
		:param add:
		"""
		pre_register_data = {
			'view': 'showUsers',
			'sort': 'userName',
			'sortDir': 'ASC',
			# 'challengeKey': f'{self.challenge_key}',  # Not need here for some reason
			'subView': 'http://fsunac-1.framingham.edu:80/administration?view=showUsersAll',
			'filterText': f'{username}',
			'userId': f'{user_id}',
			'showUsersAdd': 'Add',
		}
		pre_post = session.post('http://fsunac-1.framingham.edu/administration', data=pre_register_data)
		self.challenge_key = get_challenge_key(pre_post.content)

		register_data = {
			'regUserName': f'{username}',
			'macAddress': f'{mac_address}',
			'deviceGroup': 'Registered Guests',
			'devDesc': f'{description}',
			'sponsorEmail': f'{sponsor}',
			'challengeKey': f'{self.challenge_key}',
			'addDevice': 'Submit',
		}

		if add:
			session.post(self.request_url, data=register_data, headers=self.headers)
		elif purge:
			# TODO FIX PURGE. DOES NOT PURGE. MIGHT BE DUE TO CHALLENGEKEY -> MIGHT NEED TO SEARCH USER FIRST,
			#  THEN GET CHALLENGE KEY FROM THAT
			purge_data = [
				('view', 'showUsers'),
				('sort', 'userName'),
				('sortDir', 'ASC'),
				('challengeKey', f'{self.challenge_key}'),
				('subView',
				 f'http://fsunac-1.framingham.edu:80/administration?view=showDevicesForUser&regUserName={username}'),
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
				'subview': 'http://fsunac-1.framingham.edu:80/administration?view=showDevicesAll',
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


def get_challenge_key(url_content: object) -> object:
	"""

	:rtype: object
	:param url_content:
	:return:
	"""
	soup = BeautifulSoup(url_content, 'lxml')
	for element in soup.find_all('form'):
		for key in element.find_all('input'):
			if key['name'] == 'challengeKey':
				return key['value']


class Container(dict):
	"""Overload the items method to retain duplicate keys."""

	def __init__(self, items):
		super().__init__()
		self[""] = ""
		self._items = items

	def items(self):
		return self._items


# Tests

# Find mac address for user
# Add user (CAUTION)
# DeviceRegistration().my_session(add_user=True, username='testdev')
# val, id_ = DeviceRegistration().my_session(search_user=True, username='poppyda')
# print(val, id_)
# To Add you must search first...for secret key, and user_id
DeviceRegistration().my_session(add_device=True,  username='testdev', mac_address='10:10:10:10:10:13', description='TestAdd', sponsor='SamTest')
# DeviceRegistration().my_session(purge_devices=True, user_id=id_, username='testdev')