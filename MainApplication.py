import argparse
import configparser
import datetime
import os
import re
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal, Qt, QRunnable, QSize, QThreadPool, pyqtSlot, QCoreApplication, \
	QEventLoop, QTimer
from PyQt5.QtGui import QIcon, QMovie, QFontDatabase, QPixmap
from PyQt5.QtWidgets import QPushButton, QLineEdit, QLabel, QCheckBox, QGraphicsBlurEffect, \
	QMenu, QMenuBar
from qtpy import uic
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QApplication, QMainWindow, QMessageBox

import DeviceRegistration
from modern_ui import styles
from modern_ui import windows


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
_history = resource_path(Path.home() / 'device_registration_history')
_about = resource_path('about')
_help = resource_path('help')
_font = resource_path('Quicksand-Regular.otf')


class Signals(QObject):
	label_update_signal = pyqtSignal(str)
	popup_signal = pyqtSignal(str, str)
	clear_textboxes_signal = pyqtSignal()
	disable_widgets_signal = pyqtSignal(bool)
	play_splash_signal = pyqtSignal(bool)


class FancyDateTimeDelta(object):
	"""
	Format the date / time difference between the supplied date and
	the current time using approximate measurement boundaries
	"""

	def __init__(self, dt):
		now = datetime.datetime.now()
		delta = now - dt
		self.year = delta.days / 365
		self.month = delta.days / 30 - (12 * self.year)
		if self.year > 0:
			self.day = 0
		else:
			self.day = delta.days % 30
		self.hour = delta.seconds / 3600
		self.minute = delta.seconds / 60 - (60 * self.hour)

	def format(self):
		fmt = []
		for period in ['year', 'month', 'day', 'hour', 'minute']:
			value = getattr(self, period)
			if value:
				if value > 1:
					period += "s"
				fmt.append("%s %s" % (value, period))
		return ", ".join(fmt) + " ago"


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
				if DeviceRegistration.Register().my_session(search_user=True, username=self.username)[0]:
					user_id = DeviceRegistration.Register().my_session(search_user=True, username=self.username)[1]
					mac_address_list = DeviceRegistration.Register().my_session(get_mac_address=True,
					                                                            username=self.username,
					                                                            user_id=user_id)
					self.signals.disable_widgets_signal.emit(False)
					self.signals.play_splash_signal.emit(False)
					self.signals.label_update_signal.emit("Ready")
					mac_string = f"""<h2><font color='DodgerBlue'>MAC Adresses for <strong>{self.username}</strong></font></h2>"""
					if mac_address_list is not None:
						for mac in mac_address_list:
							mac_string += f"""<ul><li><strong><font size=5>{mac}</font+></strong></li></ul>"""

						self.signals.popup_signal.emit(f"MAC Addresses for {self.username}", mac_string)
					else:
						self.signals.popup_signal.emit(f"MAC Addresses for {self.username}",
						                               f"""<font size=5 color='MediumOrchid'>No devices registered for {self.username}</font>""")
				else:
					self.signals.popup_signal.emit("Error",
					                               f"""<h2><font color='Violet'>No such user {self.username}</font></h2>""")
					self.signals.play_splash_signal.emit(False)
					self.signals.label_update_signal.emit("Ready")
					self.signals.disable_widgets_signal.emit(False)
			else:
				self.signals.popup_signal.emit("Error",
				                               f"""<h2><font color='MediumOrchid'>Please enter a username</font></h2>""")
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

				if DeviceRegistration.Register().my_session(search_user=True, username=self.username)[0]:
					user_id = DeviceRegistration.Register().my_session(search_user=True, username=self.username)[1]
					self.signals.label_update_signal.emit("Adding device")
					DeviceRegistration.Register().my_session(add_device=True, username=self.username,
					                                         mac_address=self.mac_address, user_id=user_id,
					                                         description=self.device_type, sponsor=self.sponsor)
					self.signals.popup_signal.emit("Success!",
					                               f"""<h2><font color='DodgerBlue'>Successfully added {self.mac_address}</font></h2>""")
					self.signals.play_splash_signal.emit(False)
					self.signals.label_update_signal.emit("Ready")
					self.signals.disable_widgets_signal.emit(False)
					self.signals.clear_textboxes_signal.emit()
				else:
					self.signals.label_update_signal.emit(f"{self.username} not found creating new user")
					DeviceRegistration.Register().my_session(add_user=True, username=self.username,
					                                         sponsor=self.sponsor)
					new_search, new_id = DeviceRegistration.Register().my_session(search_user=True,
					                                                              username=self.username)
					self.signals.label_update_signal.emit("Adding device")
					DeviceRegistration.Register().my_session(add_device=True, user_id=new_id, username=self.username,
					                                         mac_address=self.mac_address, description=self.device_type,
					                                         sponsor=self.sponsor)
					self.signals.popup_signal.emit("Success!",
					                               f"""<font size=5 color='DodgerBlue'>Successfully added {self.mac_address}</font>""")
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


# Check to see if mac address is valid format eg. (00:00:00:00:00:000) or (00-00-00-00-00-00)
def check_mac_address(mac_address):
	return bool(re.match(r'(?:^|[^-])((?:[0-9a-f]{2}[:-]){5}[0-9a-f]{2})(?:$|[^-])', mac_address, re.IGNORECASE))


def check_sponsor(your_name: object) -> object:
	return bool(re.match(r'[a-zA-Z]{1,}(.*[\s]?)', your_name, re.IGNORECASE))


def check_email(email: object) -> object:
	return bool(re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", email, re.IGNORECASE))


# Check to see if username is correct format eg. (teststudent) or (teststudent45) but not (test student)
def check_username(username, other_user=False):
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
		self.QMessageBox = QMessageBox
		self.QHistoryBox = QMessageBox
		self.thread_pool = QThreadPool()
		self.ui = uic.loadUi(_UI, self)
		self.config = configparser.RawConfigParser()
		self.center()
		self.parser = argparse.ArgumentParser(description=__doc__,
		                                      formatter_class=argparse.RawDescriptionHelpFormatter)
		self.mw = windows.ModernWindow(self)
		self.initUI()
		self.init_config()

	def initUI(self):
		self.setWindowIcon(QIcon(_logo))
		self.dark_mode_icon = QIcon(resource_path('night_mode.ico'))
		self.light_mode_icon = QIcon(resource_path('light_mode.ico'))
		self.ui.user_label.setPixmap(QPixmap(resource_path('user_ico')))
		self.ui.mac_label.setPixmap(QPixmap(resource_path('mac_ico')))
		self.ui.device_label_2.setPixmap(QPixmap(resource_path('device_ico')))
		self.ui.sponsor_label_2.setPixmap(QPixmap(resource_path('name_ico')))
		self.ui.check_devices_button.setToolTip("<i><b>Check user's devices</b></i>")
		self.ui.actionAbout.triggered.connect(self.show_about)
		self.ui.actionHelp.triggered.connect(self.show_help)
		self.ui.actionAdd_user_using_website.triggered.connect(
			lambda: webbrowser.open_new_tab('http://fsunac-1.framingham.edu/administration'))
		self.ui.actionClear_All.triggered.connect(lambda: self.clear_textboxes(sponsor=True))
		self.ui.student_checkbox.stateChanged.connect(self.on_state_change)
		self.ui.faculty_checkbox.stateChanged.connect(self.on_state_change)
		self.ui.other_checkbox.stateChanged.connect(self.on_state_change)
		self.user_type = 'student'
		self.ui.register_button.setIcon(QIcon('reg.png'))
		self.setStyleSheet(open('modern_ui/style.qss', 'r').read())
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
						self.setStyleSheet('')
					else:
						self.ui.change_mode.setIconSize(QSize(25, 25))
						self.ui.change_mode.setIcon(self.dark_mode_icon)
						styles.light_mode(QApplication.instance())
						self.ui.change_mode.setToolTip("<i><b>Dark Mode</b></i>")
						self.parser.add_argument('--no_dark', action='store_true')
						self.setStyleSheet('')
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

	@staticmethod
	def write_to_history(username, mac_address, device_type):
		with open(_history, 'a') as history_file:
			time_registered = datetime.datetime.now().strftime("%m/%d/%Y %I:%M %p")
			history_file.write(
				f"""<font size='5' color='#6B9BF4'>[{time_registered}]</font>
<font size='5'>Username: </font><font color='DodgerBlue' size='5'>{username}</font>
<font size='5'>Mac Address: <font color='DodgerBlue' size='5'>{mac_address}</font></font>
<font size='4'>Device Type: {device_type}</font>

""")

	def read_history(self):
		try:
			with open(_history, 'r') as history_file:
				self.popup_msg("History", str(history_file.readlines()), history_display=True)
		except FileNotFoundError:
			self.popup_msg("History", "No history to display")

	def clear_history(self):
		# Clears contents of file by setting it to write mode
		with open(_history, 'w'):
			pass

	def fade(self):
		self.setWindowOpacity(0.2)
		QTimer.singleShot(30, self.unfade)

	def unfade(self):
		self.setWindowOpacity(1)

	def disable_widgets(self, bool_val):
		objects = [QPushButton, QLineEdit, QMenu, QMenuBar]
		for item in objects:
			for child in self.findChildren(item):
				if bool_val:
					child.setEnabled(False)
				else:
					child.setEnabled(True)

	def other_checked(self, other_checked=True):
		if other_checked:
			self.ui.username_label.setText(
				'<html><head/><body><p><span style=" color:#ff0000;">*</span>Full Name</p></body></html>')
			self.ui.progress_label.move(10, 355)
			self.ui.register_button.move(230, 320)
			self.ui.sponsor_label.setGeometry(70, 265, 151, 41)
			self.ui.sponsor_label_2.setGeometry(10, 270, 41, 41)
			self.ui.sponsor_textbox.move(250, 278)

			self.email_label = QLabel('<html><head/><body><p><span style=" color:#ff0000;">*</span>User '
			                          'Email</p></body></html>', self)
			self.email_label.setStyleSheet('font: 16pt "Verdana";')
			self.email_label.setGeometry(67, 230, 195, 61)
			self.email_textbox = QLineEdit(self)
			self.email_label_2 = QLabel(self)
			self.email_label_2.setGeometry(10, 240, 41, 41)
			self.email_label_2.setPixmap(QPixmap(resource_path('email_ico')))
			self.email_textbox.setGeometry(250, 250, 221, 21)
			self.email_textbox.setStyleSheet('font: 11pt "Verdana";')
			self.setTabOrder(self.ui.device_textbox, self.ui.email_textbox)
			self.ui.email_textbox.returnPressed.connect(lambda: self.ui.register_button.animateClick())
			self.email_label.show()
			self.email_textbox.show()
			self.email_label_2.show()
		else:
			try:
				self.ui.username_label.setText(
					'<html><head/><body><p><span style=" color:#ff0000;">*</span>Username</p></body></html>')
				self.email_textbox.deleteLater()
				self.email_label.deleteLater()
				self.email_label_2.deleteLater()
				self.ui.progress_label.move(10, 330)
				self.ui.register_button.move(230, 280)
				self.ui.sponsor_label.setGeometry(70, 220, 151, 41)
				self.ui.sponsor_label_2.setGeometry(10, 220, 41, 41)
				self.ui.sponsor_textbox.move(250, 230)
			except AttributeError:
				pass
			except RuntimeError:
				pass

	@pyqtSlot(int)
	def on_state_change(self, state):
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
	def popup_msg(self, title, message, history_display=False):
		if history_display:
			clear = self.QHistoryBox.addButton('Clear History', self.QHistoryBox.AcceptRole)
			clear.clicked.connect(self.clear_history)
			self.QHistoryBox.about(self, title, message)
			if clear == QMessageBox.Yes:
				print("test")
		self.QMessageBox.about(self, title, message)

	# Center our application instead of putting it in the top left
	def center(self):
		frame_gm = self.frameGeometry()
		screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
		center_point = QApplication.desktop().screenGeometry(screen).center()
		frame_gm.moveCenter(center_point)
		self.move(frame_gm.topLeft())

	def clear_textboxes(self, sponsor=False):
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
				self.fade()
				styles.light_mode(QApplication.instance())
				self.ui.change_mode.setIcon(self.dark_mode_icon)
				self.ui.change_mode.setIconSize(QSize(25, 25))
				self.ui.change_mode.setToolTip("<i><b>Dark Mode</b></i>")
				with open(_config, 'w') as config:
					self.config['Default']['dark_mode'] = 'false'
					self.config.write(config)
			else:
				self.fade()
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

	def play_splash(self, bool_val):

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
	def on_actionCheck_History_triggered(self):
		self.read_history()

	@Slot()
	def on_register_button_clicked(self):
		# Get the texts entered in the textbox and pass them to the thread
		self.username = self.ui.username_textbox.text().strip()
		self.mac_address = self.ui.mac_textbox.text().strip()
		self.device_type = self.ui.device_textbox.text().strip()
		self.sponsor = self.ui.sponsor_textbox.text().strip()

		self.write_to_history(self.username, self.mac_address, self.device_type)

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

	@Slot()
	def on_check_devices_button_clicked(self):
		self.username = self.ui.username_textbox.text()
		self.registration_thread = RegisterThread(username=self.username, user_check=True)

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
	QFontDatabase.addApplicationFont(_font)
	app.setStyle('Fusion')
	window = MainWindow()
	sys.exit(app.exec_())
