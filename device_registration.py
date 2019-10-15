import configparser
import json
import os
import re
import sys
import webbrowser
import qdarkstyle
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QRunnable, QSize, QThreadPool, pyqtSlot, QCoreApplication, QEventLoop
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import QPushButton, QLineEdit, QLabel, QCheckBox, QGraphicsBlurEffect, \
	QMenu, QMenuBar
from bs4 import BeautifulSoup
from modern_ui import styles
from modern_ui import windows
from qtpy import uic
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QApplication, QMainWindow, QMessageBox


def resource_path(relative_path):
	if getattr(sys, 'frozen', False):
		path_type = os.path.dirname(sys.executable)
		return os.path.join(path_type, relative_path)
	else:
		path_type = os.path.dirname(__file__)
		return os.path.join(path_type, relative_path)


_UI = resource_path('mainwindow.ui')
_MAC_UI = resource_path('second_window.ui')
_logo = resource_path('purple_flame.svg')
_config = resource_path(Path.home() / 'dev_config')
_about = resource_path('about')
_help = resource_path('help')


class Signals(QObject):
	label_update_signal = pyqtSignal(str)
	popup_signal = pyqtSignal(str, str)
	clear_textboxes_signal = pyqtSignal()
	disable_widgets_signal = pyqtSignal(bool)
	play_splash_signal = pyqtSignal(bool)


class RegisterThread(QRunnable):
	sponsor: Optional[object]

	def __init__(self, username: object = None, mac_address: object = None, device_type: object = None,
	             sponsor: object = None, user_type: object = 'student', user_check: bool = False):
		super(RegisterThread, self).__init__()
		self.signals = Signals()
		self.username = username
		self.mac_address = mac_address
		self.device_type = device_type
		self.sponsor = sponsor
		self.user_type = user_type
		self.user_check = user_check

	def run(self):
		if self.user_check:
			if check_username(self.username):
				# self.check_devices()
				self.signals.play_splash_signal.emit(True)
				self.signals.label_update_signal.emit(f"Checking devices for {self.username}...")
				self.signals.disable_widgets_signal.emit(True)
				if DeviceRegistration().my_session(search_user=True, username=self.username)[0]:
					user_id = DeviceRegistration().my_session(search_user=True, username=self.username)[1]
					mac_address_list = DeviceRegistration().my_session(get_mac_address=True, username=self.username, user_id=user_id)
					self.signals.disable_widgets_signal.emit(False)
					self.signals.play_splash_signal.emit(False)
					self.signals.label_update_signal.emit("Ready")
					mac_string = f"""<h2><font color='DodgerBlue'>MAC Adresses for <strong>{self.username}</strong></font></h2>"""
					if mac_address_list is not None:
						for mac in mac_address_list:
							mac_string += f"""<ul><li><strong><font size=5>{mac}</font></strong></li></ul>"""

						self.signals.popup_signal.emit(f"MAC Addresses for {self.username}", mac_string)
					else:
						self.signals.popup_signal.emit(f"MAC Addresses for {self.username}",
						                               f"""<font size=5 color='MediumOrchid'>No devices registered for {self.username}</font>""")
				else:
					self.signals.popup_signal.emit("Error", f"""<h2><font color='Violet'>No such user {self.username}</font></h2>""")
					self.signals.play_splash_signal.emit(False)
					self.signals.label_update_signal.emit("Ready")
					self.signals.disable_widgets_signal.emit(False)
			else:
				self.signals.popup_signal.emit("Error", f"""<h2><font color='MediumOrchid'>Please enter a username</font></h2>""")
		else:
			# Make dictionary to check whether format of text boxes are correct
			everything = {
				'right_address': bool(check_mac_address(self.mac_address)),
				'right_username': bool(check_username(self.username)),
				'right_name': bool(check_sponsor(self.sponsor))
			}

			if self.user_type != 'student' and self.user_type != 'faculty':
				everything.update(correct_email=bool(check_email(self.user_type)))
				everything.update(right_username=bool(check_username(self.username, other_user=True)))

			# Check to see that there is some text in the Text boxes and it is correctly formatted
			if all(everything.values()):
				self.signals.play_splash_signal.emit(True)
				self.signals.label_update_signal.emit("Starting...")
				self.signals.disable_widgets_signal.emit(True)

				if DeviceRegistration().my_session(search_user=True, username=self.username)[0]:
					user_id = DeviceRegistration().my_session(search_user=True, username=self.username)[1]
					self.signals.label_update_signal.emit("Adding device")
					DeviceRegistration().my_session(add_device=True, username=self.username, mac_address=self.mac_address, user_id=user_id, description=self.device_type, sponsor=self.sponsor)
					self.signals.popup_signal.emit("Success!", f"""<h2><font color='DodgerBlue'>Successfully added {self.mac_address}</font></h2>""")
					self.signals.play_splash_signal.emit(False)
					self.signals.label_update_signal.emit("Ready")
					self.signals.disable_widgets_signal.emit(False)
					self.signals.clear_textboxes_signal.emit()
				else:
					self.signals.label_update_signal.emit(f"{self.username} not found creating new user")
					DeviceRegistration().my_session(add_user=True, username=self.username, sponsor=self.sponsor)
					new_search, new_id = DeviceRegistration().my_session(search_user=True, username=self.username)
					DeviceRegistration().my_session(add_device=True, user_id=new_id, username=self.username, mac_address=self.mac_address, description=self.device_type, sponsor=self.sponsor)
					self.signals.popup_signal.emit("Success!", f"""<font size=5 color='DodgerBlue'>Successfully added {self.mac_address}</font>""")
					self.signals.play_splash_signal.emit(False)
					self.signals.label_update_signal.emit("Ready")
					self.signals.disable_widgets_signal.emit(False)
					self.signals.clear_textboxes_signal.emit()
			else:
				# Go through the dictionary and give appropriate error messages if it turns out something is wrong
				for _ in everything:
					global msg
					msg = ''
					if not everything['right_address']:
						msg += 'Invalid MAC address format!\n'
						pass
					if not everything['right_username']:
						msg += 'Invalid username!\n'
					if not everything['right_name']:
						msg += 'You entered invalid values for your name!\n'
					try:
						if not everything['correct_email']:
							msg += 'Invalid email address!\n'
					except KeyError:
						pass
				self.signals.play_splash_signal.emit(False)
				self.signals.disable_widgets_signal.emit(False)
				self.signals.popup_signal.emit('Errors in your form', msg)


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
			'j_username': '',
			'j_password': '',
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


# Check to see if mac address is valid format eg. (00:00:00:00:00:000) or (00-00-00-00-00-00)
def check_mac_address(mac_address: object) -> object:
	"""

	:param mac_address:
	:return:
	"""
	return bool(re.match('[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$', mac_address, re.IGNORECASE))


# Check to see if username is correct format eg. (teststudent) or (teststudent45) but not (test student)
def check_sponsor(your_name: object) -> object:
	"""

	:param your_name:
	:return:
	"""
	return bool(re.match(r'[a-zA-Z]{1,}(.*[\s]?)', your_name, re.IGNORECASE))


def check_email(email: object) -> object:
	"""

	:param email:
	:return:
	"""
	return bool(re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email, re.IGNORECASE))


def check_username(username: object, other_user: object = False) -> object:
	"""

	:param username:
	:param other_user:
	:return:
	"""
	if other_user:
		return True
	else:
		return bool(re.match(r'[a-zA-Z]{1,}', username, re.IGNORECASE) or (
				re.match(r'[a-zA-Z]{1,}', username, re.IGNORECASE) and username.endswith(re.match(r'[0-9]{1,}'))))


class MainWindow(QMainWindow):
	registration_thread: RegisterThread
	sponsor: object
	device_type: object
	mac_address: object
	username: object
	movie: QMovie
	gif_label: QLabel
	email_label: QLabel
	email_textbox: QLineEdit
	button_clicked: bool
	user_type: str
	light_mode_icon: QIcon
	dark_mode_icon: QIcon

	def __init__(self):
		super(MainWindow, self).__init__()
		self.thread_pool = QThreadPool()
		self.ui = uic.loadUi(_UI, self)
		self.config = configparser.RawConfigParser()
		self.center()
		self.mw = windows.ModernWindow(self)
		self.initUI()
		self.init_config()

	def initUI(self) -> object:
		self.setWindowIcon(QIcon(_logo))
		self.dark_mode_icon = QIcon(resource_path('night_mode.ico'))
		self.light_mode_icon = QIcon(resource_path('light_mode.ico'))
		self.ui.actionAbout.triggered.connect(self.show_about)
		self.ui.actionHelp.triggered.connect(self.show_help)
		self.ui.actionAdd_user_using_website.triggered.connect(
			lambda: webbrowser.open_new_tab('http://fsunac-1.framingham.edu/administration'))
		self.ui.actionClear_All.triggered.connect(lambda: self.clear_textboxes(sponsor=True))
		self.ui.student_checkbox.stateChanged.connect(self.on_state_change)
		self.ui.faculty_checkbox.stateChanged.connect(self.on_state_change)
		self.ui.other_checkbox.stateChanged.connect(self.on_state_change)
		self.user_type = 'student'
		self.mw.show()

	def init_config(self):
		try:
			# Open our config file and load configs if applicable
			with open(_config, 'r') as config_file:
				if os.path.getsize(_config):
					self.config.read_file(config_file)
					self.ui.sponsor_textbox.setText(self.config.get('Default', 'sponsor'))

					if self.config.getboolean('Default', 'dark_mode'):
						self.ui.change_mode.setIconSize(QSize(35, 35))
						self.ui.change_mode.setIcon(self.light_mode_icon)
						styles.dark_mode(QApplication.instance())
						self.ui.change_mode.setToolTip("<i><b>Light Mode</b></i>")
					else:
						self.ui.change_mode.setIconSize(QSize(25, 25))
						self.ui.change_mode.setIcon(self.dark_mode_icon)
						styles.light_mode(QApplication.instance())
						self.ui.change_mode.setToolTip("<i><b>Dark Mode</b></i>")
				else:
					raise FileNotFoundError
		except FileNotFoundError:
			# Create config file if no config found
			self.config.add_section('Default')
			self.config['Default']['sponsor'] = ''
			self.config['Default']['dark_mode'] = 'true'
			self.ui.change_mode.setIcon(self.light_mode_icon)
			self.ui.change_mode.setIconSize(QSize(35, 35))
			self.ui.change_mode.setIcon(self.light_mode_icon)
			styles.dark_mode(QApplication.instance())
			self.ui.change_mode.setToolTip("<i><b>Light Mode</b></i>")

			with open(_config, 'w') as config_file:
				self.config.write(config_file)

	def disable_widgets(self, bool_val: object) -> object:
		"""

		:param bool_val:
		"""
		objects = [QPushButton, QLineEdit, QMenu, QMenuBar]
		for item in objects:
			for child in self.findChildren(item):
				if bool_val:
					child.setEnabled(False)
				else:
					child.setEnabled(True)

	def other_checked(self, other_checked: object = True) -> object:
		"""

		:param other_checked:
		"""
		if other_checked:
			self.ui.username_label.setText(
				'<html><head/><body><p><span style=" color:#ff0000;">*</span>Full Name</p></body></html>')
			self.ui.progress_label.move(10, 355)
			self.ui.register_button.move(230, 320)
			self.ui.sponsor_label.setGeometry(95, 265, 151, 41)
			self.ui.sponsor_textbox.move(250, 278)

			self.email_label = QLabel('<html><head/><body><p><span style=" color:#ff0000;">*</span>User '
			                          'Email</p></body></html>', self)
			self.email_label.setStyleSheet('font: 16pt "Verdana";')
			self.email_label.setGeometry(94, 230, 151, 61)
			self.email_textbox = QLineEdit(self)
			self.email_textbox.setGeometry(250, 250, 221, 21)
			self.email_textbox.setStyleSheet('font: 11pt "Verdana";')
			self.setTabOrder(self.ui.device_textbox, self.ui.email_textbox)
			self.ui.email_textbox.returnPressed.connect(lambda: self.ui.register_button.animateClick())
			self.email_label.show()
			self.email_textbox.show()
		else:
			try:
				self.ui.username_label.setText(
					'<html><head/><body><p><span style=" color:#ff0000;">*</span>Username</p></body></html>')
				self.email_textbox.deleteLater()
				self.email_label.deleteLater()
				self.ui.progress_label.move(10, 330)
				self.ui.register_button.move(230, 280)
				self.ui.sponsor_label.setGeometry(95, 220, 151, 41)
				self.ui.sponsor_textbox.move(250, 230)
			except AttributeError:
				pass
			except RuntimeError:
				pass

	@pyqtSlot(int)
	def on_state_change(self, state: object) -> object:
		"""

		:param state:
		"""
		if state == Qt.Checked:
			if self.sender() == self.ui.student_checkbox:
				self.other_checked(other_checked=False)
				self.user_type = 'student'
				self.ui.faculty_checkbox.setChecked(False)
				self.ui.other_checkbox.setChecked(False)
			elif self.sender() == self.ui.faculty_checkbox:
				self.other_checked(other_checked=False)
				self.user_type = 'faculty'
				self.ui.student_checkbox.setChecked(False)
				self.ui.other_checkbox.setChecked(False)
			elif self.sender() == self.ui.other_checkbox:
				self.other_checked()
				self.user_type = 'other'
				self.ui.student_checkbox.setChecked(False)
				self.ui.faculty_checkbox.setChecked(False)
		else:
			if not self.ui.student_checkbox.isChecked() and not self.ui.faculty_checkbox.isChecked() and not self.ui.other_checkbox.isChecked():
				self.ui.student_checkbox.setChecked(True)

	# Function to display an error if we get one
	def popup_msg(self, title: object, message: object) -> object:
		"""

		:param title:
		:param message:
		"""
		QMessageBox.about(self, title, message)

	# Center our application instead of putting it in the top left
	def center(self):
		frame_gm = self.frameGeometry()
		screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
		center_point = QApplication.desktop().screenGeometry(screen).center()
		frame_gm.moveCenter(center_point)
		self.move(frame_gm.topLeft())

	def clear_textboxes(self, sponsor: object = False):
		"""

		:param sponsor:
		"""
		self.ui.username_textbox.clear()
		self.ui.mac_textbox.clear()
		self.ui.device_textbox.clear()
		if sponsor:
			self.ui.sponsor_textbox.clear()
		try:
			self.ui.email_textbox.clear()
		except RuntimeError as r:
			pass
		except AttributeError as a:
			pass

	def change_ui(self):
		with open(_config, 'r'):
			if self.config.getboolean('Default', 'dark_mode'):
				styles.light_mode(QApplication.instance())
				self.ui.change_mode.setIcon(self.dark_mode_icon)
				self.ui.change_mode.setIconSize(QSize(25, 25))
				self.ui.change_mode.setToolTip("<i><b>Dark Mode</b></i>")
				with open(_config, 'w') as config:
					self.config['Default']['dark_mode'] = 'false'
					self.config.write(config)
			else:
				styles.dark_mode(QApplication.instance())
				self.ui.change_mode.setIcon(self.light_mode_icon)
				self.ui.change_mode.setIconSize(QSize(35, 35))
				self.ui.change_mode.setToolTip("<i><b>Light Mode</b></i>")
				with open(_config, 'w') as config:
					self.config['Default']['dark_mode'] = 'true'
					self.config.write(config)

	def show_about(self):
		with open(_about, 'r') as about:
			self.popup_msg('About', about.read())

	def show_help(self):
		with open(_help, 'r') as about:
			self.popup_msg('Help', about.read())

	def update_label(self, label_text):
		self.ui.progress_label.setText(label_text)

	@Slot()
	def on_change_mode_clicked(self):
		self.change_ui()

	def play_splash(self, bool_val: object):
		"""

		:param bool_val:
		"""
		def blur_objects(blur=True):
			objects = [QLabel, QPushButton, QLineEdit, QCheckBox, QMenu, QMenuBar]

			for item in objects:
				for child in self.findChildren(item):
					if child is not self.ui.progress_label:
						if blur:
							child.setGraphicsEffect(QGraphicsBlurEffect())
						else:
							child.setGraphicsEffect(QGraphicsBlurEffect().setBlurRadius(0))

			QCoreApplication.processEvents(QEventLoop.AllEvents)

		if bool_val:
			blur_objects(blur=True)
		else:
			blur_objects(blur=False)

	@Slot()
	def on_actionCheck_device_for_current_user_triggered(self):
		self.username = self.ui.username_textbox.text()
		self.registration_thread = RegisterThread(username=self.username, user_check=True)

		self.registration_thread.signals.clear_textboxes_signal.connect(self.clear_textboxes)
		self.registration_thread.signals.disable_widgets_signal.connect(self.disable_widgets)
		self.registration_thread.signals.popup_signal.connect(self.popup_msg)
		self.registration_thread.signals.label_update_signal.connect(self.update_label)
		self.registration_thread.signals.play_splash_signal.connect(self.play_splash)
		self.thread_pool.start(self.registration_thread)

	@Slot()
	def on_register_button_clicked(self):
		# Get the texts entered in the textbox and pass them to the thread
		self.username = self.ui.username_textbox.text()
		self.mac_address = self.ui.mac_textbox.text()
		self.device_type = self.ui.device_textbox.text()
		self.sponsor = self.ui.sponsor_textbox.text()

		if self.user_type == 'other':
			self.registration_thread = RegisterThread(self.username, self.mac_address, self.device_type, self.sponsor,
			                                          user_type=self.email_textbox.text())
		else:
			self.registration_thread = RegisterThread(self.username, self.mac_address, self.device_type, self.sponsor,
			                                          user_type=self.user_type)
		self.registration_thread.signals.clear_textboxes_signal.connect(self.clear_textboxes)
		self.registration_thread.signals.disable_widgets_signal.connect(self.disable_widgets)
		self.registration_thread.signals.popup_signal.connect(self.popup_msg)
		self.registration_thread.signals.label_update_signal.connect(self.update_label)
		self.registration_thread.signals.play_splash_signal.connect(self.play_splash)

		self.thread_pool.start(self.registration_thread)

	# If the user clicks the red button to exit the window
	@Slot()
	def closeEvent(self, event):
		with open(_config, 'r'):
			self.config['Default']['sponsor'] = self.ui.sponsor_textbox.text()
		with open(_config, 'w') as config:
			self.config.write(config)
			event.accept()


if __name__ == '__main__':
	app = QApplication(sys.argv)
	app.setStyle('Fusion')
	window = MainWindow()
	sys.exit(app.exec_())
