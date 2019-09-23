from datetime import datetime

import requests
import re
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
			self.challenge_key = self.get_challenge_key(source)

	def get_challenge_key(self, url_content):
		soup = BeautifulSoup(url_content, 'lxml')
		for element in soup.find_all('form'):
			for key in element.find_all('input'):
				if key['name'] == 'challengeKey':
					return key['value']

	def my_session(self, user_id=None, username=None, mac_address=None, get_mac_address=False, add_device=False, add_user=False, search_user=False, description=None, sponsor=None):
		with requests.Session() as session:
			web = session.post(self.login_url, cookies=self.cookies, data=self.data, headers=self.headers)
			self.challenge_key = self.get_challenge_key(web.content)
			if get_mac_address:
				return self.find_mac_address(session, username)
			elif add_user:
				return self.add_new_user(session, username)
			elif search_user:
				return self.search(session, username)
			elif add_device:
				self.add_device(session, user_id, username, mac_address, description, sponsor)

	def search(self, session, username):
		user_info = []
		search_user = session.get('http://fsunac-1.framingham.edu/administration?view=showUsers')
		source = search_user.content
		self.challenge_key = self.get_challenge_key(source)
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
		return False

	def find_mac_address(self, session, username):
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
		soup = BeautifulSoup(source_code, 'lxml')
		for mac_addr in soup.find_all('a', href="#"):
			if re.match('[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$', mac_addr.text, re.IGNORECASE):
				list_of_mac_addresses.append(mac_addr.text)

		if len(list_of_mac_addresses) > 0:
			print(list_of_mac_addresses)
			return list_of_mac_addresses
		else:
			print(f"no devices for {username}")

	def add_new_user(self, session, username):
		current_date = datetime.now()
		registration_start_date = f'{current_date.strftime("%m/%d/%Y")} 0:00:00'
		registration_end_date = f"{current_date.strftime('%m')}/{current_date.strftime('%d')}/{int(current_date.strftime('%Y')) + 2} 0:00:00"
		# View all users to get challenge_key
		show_users = session.get('http://fsunac-1.framingham.edu/administration?view=showUsers')
		self.challenge_key = self.get_challenge_key(show_users.content)
		#  Post to add user and get challenge key
		add_user_data = {
			'view': 'showUsers',
			'sort': 'userName',
			'sortDir': 'ASC',
			'challengeKey': f'{self.challenge_key}',  # Not need here for some reason
			'subView': 'http://fsunac-1.framingham.edu:80/administration?view=showUsersAll',
			'filterText': '',
			'showUsersAdd': 'Add',
		}
		self.challenge_key = self.get_challenge_key(session.post(self.request_url, data=add_user_data).content)
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
			'sponsorEmail': 'Test',
			'userType': 'Web Authentication',
			'userMaxDevice': '',
			'challengeKey': f'{self.challenge_key}',
			'addUser': 'Submit'
		}
		session.post(self.request_url, data=user_data, headers=self.headers)

	def add_device(self, session, user_id, username, mac_address, description, sponsor):
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
		self.challenge_key = self.get_challenge_key(pre_post.content)

		register_data = {
			'regUserName': f'{username}',
			'macAddress': f'{mac_address}',
			'deviceGroup': 'Registered Guests',
			'devDesc': f'{description}',
			'sponsorEmail': f'{sponsor}',
			'challengeKey': f'{self.challenge_key}',
			'addDevice': 'Submit',
		}

		register_device = session.post(self.request_url, data=register_data, headers=self.headers)
		print(register_device.status_code)


# Tests

# Find mac address for user
# Add user (CAUTION)
DeviceRegistration().my_session(add_user=True, username='testdev')
val, id_ = DeviceRegistration().my_session(search_user=True, username='testdev')
print(id_)
# To Add you must search first...for secret key
DeviceRegistration().my_session(add_device=True, user_id=id_, username='testdev', mac_address='10:10:10:10:10:13', description='TestAdd', sponsor='SamTest')