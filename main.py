__project__ = 'Metin2Dev - Private Server Down Detector'
__author__ = "Emanuel Constantin"
__copyright__ = "Copyright (C) 2022 Metin2Dev"
__license__ = "MIT"
__version__ = "1.0.0"

from typing import NoReturn
from urllib.parse import urljoin
import concurrent.futures
import os.path
import json
import re
import logging
import sys
import timeit

import matplotlib.pyplot as plt
import pandas
import coloredlogs
import pyperclip
import requests
import argparse

# Check if runs in debug mode
DEBUG = False
if sys.gettrace():
	DEBUG = True


class App:
	def __init__(self, **kwargs):
		self._input_file: str = kwargs['input']
		self._output_path: str = kwargs['output']
		self._ignored_urls_file: str = kwargs['exclude']
		self._domain: str = kwargs['domain']
		self._is_logging: str = kwargs['logging']
		self._timeout = kwargs['timeout']
		self._threads = kwargs['threads']

		self._topics: list[dict] = []
		self._ignored_urls: set = set()
		self._archived_topics: dict[int, dict] = {}

		self.read_ignored_urls()
		self.read_database()

	@property
	def get_topics(self) -> list[dict]:
		"""
		# Get the topics.
		"""
		return self._topics

	@property
	def get_archived_topics(self) -> dict[int, dict]:
		"""
		# Get the archived topics.
		"""
		return self._archived_topics

	@property
	def get_ignored_urls(self) -> set:
		"""
		# Get the ignored URLs.
		"""
		return self._ignored_urls

	@property
	def get_statistics_value(self) -> tuple[int, int]:
		"""
		:return: The amount of offline and online servers.
		"""
		offline_count: int = len(self._archived_topics)
		online_count: int = len(self._topics) - offline_count
		return offline_count, online_count

	@staticmethod
	def get_statistics_percentage(offline_count: int, online_count: int) -> tuple[str, str]:
		"""
		Find out what proportion of servers are unavailable and available.
		:param offline_count: Offline servers
		:param online_count: Online servers
		"""
		total_count: int = max(offline_count + online_count, 1)
		offline_percentage: float = round(offline_count / total_count * 100, 2)
		online_percentage: float = round(online_count / total_count * 100, 2)
		return f'{offline_count} ({offline_percentage}%)', f'{online_count} ({online_percentage}%)'

	def build_topic_link(self, topic: dict) -> str:
		"""
		# Build main link to the topic.
		:param topic: The topic information
		:return: The topic link
		"""
		return urljoin(self._domain, f'{topic["topic_id"]}-{topic["title_seo"]}').encode('ASCII', 'ignore').decode('ASCII')

	def find_urls(self, topic: dict) -> NoReturn:
		"""
		Find the URLs in the topic content.
		:param topic: The topic information
		:return: The topic URLs set without duplicates and ignored URLs
		"""
		urls: set = set(re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', topic['post'], re.IGNORECASE))
		urls.difference_update(self._ignored_urls)
		return urls

	def check_website(self, url) -> bool:
		"""
		Performs an HTTP request to each of the topic's inner URLs in order.
		to identify those that have websites that are down.
		:return: Topics with unavailable URLs
		"""
		try:
			request: requests.Response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=self._timeout)
			return request.status_code == 200
		except Exception as e:
			return False

	def read_database(self) -> NoReturn:
		"""
		Reads the database file and loads the topics in the dictionary.
		"""
		with open(self._input_file, encoding="utf-8") as jsonFile:
			topics: json = json.load(jsonFile).get('RECORDS')
			for topic in topics[:]:
				if topic:
					self._topics.append({
						'id': topic['topic_id'],
						'title': topic['title_seo'],
						'full_link': self.build_topic_link(topic),
						'urls': self.find_urls(topic),
						'offline_urls': set(),
					})

	def read_ignored_urls(self) -> NoReturn:
		"""
		Reads the ignored URLs file and loads the URLs in the set.
		"""
		with open(self._ignored_urls_file, encoding='utf-8') as file:
			ignored_urls: json = json.load(file).get('urls')
			self._ignored_urls = ignored_urls

	def archive_topic(self, topic: dict) -> NoReturn:
		"""
		# Archiving the topic if it has no URLs or all URLs are offline.
		:param topic: The topic information
		"""
		if topic['id'] not in self._archived_topics:
			self._archived_topics.update({topic['id']: topic})
		else:
			self._archived_topics[topic['id']]['offline_urls'].update(topic['offline_urls'])

	def process_parallel_topics(self) -> NoReturn:
		"""
		Processing topic servers and determining whether they are
		online or offline using HTTP requests to inner URLs.
		"""
		topics: list[dict] = []
		for topic in self._topics:
			if not topic['urls']:
				self.archive_topic(topic)
				continue

			topics.append(topic)

		with concurrent.futures.ThreadPoolExecutor(max_workers=self._threads) as executor:
			futures: dict[concurrent.futures.Future, tuple] = {executor.submit(self.check_website, url): (topic, url) for topic in topics for url in topic['urls']}

			for future in concurrent.futures.as_completed(futures):
				if not future.result():
					(topic, url) = futures[future]

					topic['offline_urls'].add(url)
					self.archive_topic(topic)

	def show_chart(self) -> NoReturn:
		"""
		Display a bar graph comparing the percentage of available and unavailable servers.
		"""
		values = self.get_statistics_value
		chart_info: dict = {'title': 'Statistics', 'x_label': 'Status', 'y_label': 'Count', 'labels': ('Offline', 'Online'), 'colors': ['tab:red', 'tab:green']}

		fig, ax = plt.subplots()

		ax.bar(chart_info['labels'], values, label=chart_info['labels'], color=chart_info['colors'])
		ax.set_title(__project__)
		ax.legend(title=chart_info['title'], loc='upper center', labels=[*self.get_statistics_percentage(*values)])
		ax.grid(axis='y', linestyle='solid')
		ax.set_xlabel(chart_info['x_label'])
		ax.set_ylabel(chart_info['y_label'])

		plt.savefig(os.path.join(self._output_path, 'statistics.png'))
		plt.show()

	def print_log(self) -> NoReturn:
		"""
		Display the results of the analysis in the console.
		"""
		df = pandas.DataFrame.from_dict(self._archived_topics, orient='index', columns=['full_link', 'offline_urls'])
		df.sort_index(ascending=True)

		df_out = df.to_string(formatters={column: lambda _: f"{_!s:<{160}s}" for column in df.columns}, justify='left').replace('set()', '{}')

		print(df_out, file=open(os.path.join(self._output_path, 'output.log'), 'w', encoding='ASCII', errors='ignore'))
		if DEBUG or self._is_logging:
			print(df_out)

	def build_query(self):
		"""
		Create a query to retrieve all topics with unavailable websites and move them
		to the archive category, then copy it to the clipboard to paste into MySQL.
		"""
		query: str = f'UPDATE MD_forums_topics SET forum_id = 148 WHERE tid in {tuple(self._archived_topics.keys())};'
		logging.warning('SQL Query copied to clipboard!')
		logging.info(query)
		pyperclip.copy(query)

	def generate_report(self) -> NoReturn:
		"""
		# Generate a report on the status of the servers.
		"""
		self.show_chart()
		self.build_query()
		self.print_log()

	def run(self) -> NoReturn:
		"""
		# The main function of the program.
		"""
		elapsed_time = f'{timeit.timeit(self.process_parallel_topics, number=1):.2f}s'
		self.generate_report()
		logging.info(f'Elapsed time: {elapsed_time}')


if __name__ == '__main__':
	# Set up the argument parser
	parser = argparse.ArgumentParser(description=__project__)

	parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
	parser.add_argument('--input', help='JSON database file', action='store', default='database.json')
	parser.add_argument('--output', help='Output path directory', action='store', default='output')
	parser.add_argument('--exclude', help='JSON excluded urls file', action='store', default='ignored_urls.json')
	parser.add_argument('--timeout', help='Timeout for HTTP requests', action='store', default=None, type=int, metavar='SECONDS')
	parser.add_argument('--logging', help='Enable console output', action='store', default=True, type=bool, choices=[True, False])
	parser.add_argument('--threads', help='The maximum number of threads that can be used', action='store', default=None, type=int, choices=range(1, 32), metavar='THREADS')
	parser.add_argument('--domain', help='The domain name of the site', action='store', default='https://metin2.dev/topic/', type=str, metavar='DOMAIN')

	args = parser.parse_args()
	print(args)

	if not args.input:
		raise FileNotFoundError('No input file specified!')

	# Output path directory creation
	if not os.path.isdir(args.output):
		os.mkdir(args.output)

	# Set up logging
	coloredlogs.ColoredFormatter()
	coloredlogs.install(level=logging.INFO)

	logging.basicConfig(format='%(asctime)s; %(levelname)-8s %(message)s', level=logging.INFO)

	# Run the program
	app = App(**vars(args))
	app.run()
