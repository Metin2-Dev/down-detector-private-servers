__author__ = "Emanuel Constantin"
__copyright__ = "Copyright (C) 2022 Metin2Dev"
__license__ = "MIT"
__version__ = "1.0"

import json
import os.path
from typing import NoReturn

import requests


class App:
	def __init__(self):
		self.database_topic_list = []
		self.read_database()

	@staticmethod
	def check_website(url: str) -> bool:
		"""
		:param url: The URL to check
		:return: True if the website is up, False otherwise
		"""
		try:
			requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=None)
			return True
		except BaseException as error:
			return False

	def read_database(self) -> NoReturn:
		"""
		Reads the database file and loads the data into the database_topic_list
		"""
		with open('private-servers.json', encoding="utf-8") as jsonFile:
			queries: json = json.load(jsonFile).get('RECORDS')
			self.database_topic_list = queries

	def process_database(self) -> NoReturn:
		"""
		Processing the database topics
		"""
		for topic in self.database_topic_list:
			print(topic)

	def run(self) -> NoReturn:
		"""
		"""
		pass


if __name__ == '__main__':
	app = App()
	app.process_database()
	# app.run()
