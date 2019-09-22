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

	def my_session(self, username=None, mac_address=None, get_mac_address=False, add_device=False, add_user=False):
		with requests.Session() as session:
			list_of_mac_addresses = []
			web = session.post(self.login_url, cookies=self.cookies, data=self.data, headers=self.headers)
			self.challenge_key = self.get_challenge_key(web.content)

			def search():
				# TODO
				pass

			def find_mac_addresses():
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

			def add_new_user():
				current_date = datetime.now()
				registration_start_date = f'{current_date.strftime("%m/%d/%Y")} 0:00:00'
				registration_end_date = f"{current_date.strftime('%m')}/{current_date.strftime('%d')}/{int(current_date.strftime('%Y')) + 2} 0:00:00"
				# View all users to get challenge_key
				show_users = session.get('http://fsunac-1.framingham.edu/administration?view=showUsers')
				source = show_users.content
				self.challenge_key = self.get_challenge_key(source)
				#  Post to add user and get challenge key
				add_user_data = {
					'view': 'showUsers',
					'sort': 'userName',
					'sortDir': 'ASC',
					'challengeKey': f'{self.challenge_key}',
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

			if get_mac_address:
				find_mac_addresses()
			elif add_user:
				add_new_user()


DeviceRegistration().my_session(get_mac_address=True, username='sagyakwa')
DeviceRegistration().my_session(add_user=True, username='testdev')