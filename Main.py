import praw
import requests
import random
import threading
import sqlite3

from functools import wraps
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem

# all these variables are required for program to work.

client_id = "" # Client ID for reddit
client_secret = ""  # your client secret for reddit
reddit_username = "" # your reddit username
reddit_password = "" # your reddit password

title_of_message = "Help with homework" # title of the message you want to send
message = "" # the message to send to the reddit user
file = "" # The file with the list of subreddits you want to check
file2 = "" # The file with the keywords you would like to check in a post
time_check = 300 # How much time to wait before to check the subreddit again. In seconds. e.g (300) = 5 mins

def file_exception_handler(func):
	@wraps(func)

	def inner(*args):
		try:
			func(*args)
		except FileNotFoundError:
			print("[!] Invalid file name or file not in the same directory as the script.")
			exit()
	return inner

class RandomUserAgent:
	def __init__(self):
		self.software_names = [SoftwareName.CHROME.value]
		self.os = [OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value]
		self.user_agent_rotator = UserAgent(software_names=self.software_names, operating_system=self.os, limit=100)
		self.user_agents = self.user_agent_rotator.get_user_agents()

	def get_random_number(self):
		return random.randint(0, 99)

	def get_random_user_agents(self):
		return self.user_agents[self.get_random_number()]["user_agent"]


class DataBase:
	def __init__(self):
		self.DATA_BASE_NAME = "subreddit.db"
		self.conn = sqlite3.connect(self.DATA_BASE_NAME, check_same_thread=False)
		self.c = self.conn.cursor()

	def create_table(self):
		self.c.execute('''CREATE TABLE IF NOT EXISTS author (name TEXT, title TEXT)''')

	def insert_values(self, author, title):
		self.c.execute("INSERT INTO author VALUES (?, ?)", (author, title))
		self.conn.commit()

	def check_if_exists_author(self, author, title):

		for row in self.c.execute("SELECT * FROM author"):
			if author == row[0] and title == row[1]:
				return True

		return False


class RedditBot:
	def __init__(self):
		self.data_base = DataBase()
		self.reddit = praw.Reddit(
			client_id= client_id,
			client_secret= client_secret,
			password=reddit_password,
			username=reddit_username,
			user_agent="None"
			)

		self.subreddit_list = [] # the subreddit list
		self.get_random_user_agent = RandomUserAgent()
		self.keywords = None # the keyword list

	def subreddit_string(self, sub_reddit):
		return f"https://www.reddit.com/r/{sub_reddit}/"

	@file_exception_handler
	def get_keywords(self, file_name):
		with open(file_name, "r") as f:
			self.keywords = [x.strip().lower() for x in f.readlines()]

	@file_exception_handler
	def read_file(self, file_name):
		with open(file_name, "r") as f:
			lines = f.readlines()
			count = 1

			for sub_reddit in lines:
				sub_reddit = sub_reddit.strip()
				at = f"At: {str(count) + ' / ' + str(len(lines))}"

				print(f"[+] Verifying: {sub_reddit}, {at}")

				if not self.verify_subreddit(sub_reddit, self.get_random_user_agent.get_random_user_agents()):
					print(f"[!] Invalid subreddit for {sub_reddit}")
					exit()
				else:
					self.subreddit_list.append(sub_reddit)
				count += 1

	def verify_subreddit(self, sub_reddit, user_agent):
		return requests.head(f"{self.subreddit_string(sub_reddit)}", headers={"User-Agent": f"{user_agent}"}).status_code == 200

	def reddit_bot_main(self):
		self.get_subreddits()
		threading.Timer(time_check, self.reddit_bot_main).start()
		print(f"[+] Waiting: {str(time_check / 60)} minutes.")

	def get_subreddits(self): 

		for sub_reddit in self.subreddit_list:
			sub = self.reddit.subreddit(sub_reddit).new(limit=5)
			d = {}

			for comments in sub:
				author = str(comments.author)
				title = str(comments.title)

				for word in title.split(" "):
					word = word.lower()

					if word in self.keywords:
						d[title] = author

			if d:
				for title, author in d.items():

					if self.data_base.check_if_exists_author(author, title):
						print(f"[!] Seen Author: {author} and title: {title} already. Skipping")
					else:
						self.data_base.insert_values(author, title)
						RedditMessage(author).send_message_to_redditor(message, title_of_message)


class RedditMessage(RedditBot):
	def __init__(self, reddit_username):
		super().__init__()

		self.reddit_username = reddit_username
		self.redditor = praw.models.Redditor(self.reddit, name=self.reddit_username)

	def send_message_to_redditor(self, message, title):
		print(f"[+] Sending message to {self.reddit_username}")
		self.redditor.message(title, message)


if __name__ == '__main__':
	reddit = RedditBot()
	reddit.data_base.create_table()
	
	reddit.read_file(file) 
	reddit.get_keywords(file2) 
	reddit.reddit_bot_main()
