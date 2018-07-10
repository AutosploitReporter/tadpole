import re
import os
import sys
import platform

import requests
from bs4 import BeautifulSoup

import lib.output


class AccessDeniedByAWS(Exception): pass


VERSION = "0.0.3"
GRAY_HAT_WARFARE_URL = "https://buckets.grayhatwarfare.com/results"
HOME = os.getcwd()
LOOT_DIRECTORY = "{}/loot".format(HOME)
DEFAULT_USER_AGENT = "BucketDump/{} (Language={};Platform={})".format(
    VERSION, sys.version.split(" ")[0], platform.platform().split("-")[0]
)
#  	tADpOlE 	  Aws Download Open buckEt files
BANNER = """\033[36m
  _            _____         ____  _ ______ 
 | |     /\   |  __ \       / __ \| |  ____|
 | |_   /  \  | |  | |_ __ | |  | | | |__   
 | __| / /\ \ | |  | | '_ \| |  | | |  __|  
 | |_ / ____ \| |__| | |_) | |__| | | |____ 
  \__/_/    \_\_____/| .__/ \____/|_|______|[][][]
                     | |                    
                     |_|   Aws Download Open buckEt files v({}) 
\033[0m""".format(VERSION)


def gather_bucket_links(url, query, **kwargs):
    user_agent = kwargs.get("user_agent", None)
    extra_headers = kwargs.get("extra_headers", None)
    post_data = kwargs.get("post_data", None)
    debug = kwargs.get("debug", False)

    aws_regex = re.compile(".amazonaws.", re.I)
    found_files = set()
    page_links = set()
    open_buckets = set()

    headers = {
        "Host": "buckets.grayhatwarfare.com",
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Referer": "https://buckets.grayhatwarfare.com/results/{}".format(query),
        "DNT": "1",
        "Connection": "close",
        "Upgrade-Insecure-Requests": "1",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    if extra_headers is not None:
        for header in extra_headers.keys():
            headers[header] = extra_headers[header]

    req = requests.post(url, data=post_data, headers=headers)
    soup = BeautifulSoup(req.content, "html.parser")
    all_links = soup.find_all('a', href=True)
    for link in all_links:
        if "/results/{}".format(query) in link["href"]:
            page_links.add(link["href"])
            if debug:
                lib.output.debug("found page link: {}".format(link["href"]))
    for page in page_links:
        url = url.replace("/results", page)
        req = requests.get(url, headers=headers)
        soup = BeautifulSoup(req.content, "html.parser")
        for link in soup.find_all('a', href=True):
            if aws_regex.search(link["href"]) is not None:
                found_files.add(link["href"])

    for item in found_files:
        open_buckets.add(item.split("/")[2])
    if debug:
        lib.output.debug("done!")
    return found_files, open_buckets


def download_files(url, path, debug=False):
    if not os.path.exists(path):
        os.makedirs(path)
    try:
        if debug:
            lib.output.debug("attempting to download file from {}".format(url))
        file_path = "{}/{}".format(path, url.split("/")[-1])
        downloader = requests.get(url, stream=True)
        if os.path.isfile(file_path):
            amount = 0
            path = file_path.split("/")
            path.pop()
            path = "/".join(path)
            files_in_path = os.listdir(path)
            filename = url.split("/")[-1]
            for f in files_in_path:
                if filename in f:
                    amount += 1
            file_path = "{}({})".format(file_path, amount)
        with open(file_path, "a+") as data:
            for chunk in downloader.iter_content(chunk_size=8192):
                if "AccessDenied" in chunk:
                    data.write("ACCESS DENIED")
                    raise AccessDeniedByAWS("access to s3 bucket is denied by AWS")
                if chunk:
                    data.write(chunk)
        if debug:
            lib.output.success("file saved to: {}".format(file_path))
    except AccessDeniedByAWS:
        lib.output.warn("unable to download file: {}; access denied".format(url.split("/")[-1]))
    except Exception as e:
        lib.output.fatal("failed to download file due to unknown error: {}".format(str(e)))


def get_random_agent(debug=False):
    import random

    with open("{}/etc/user-agents.txt".format(os.getcwd())) as agents:
        user_agent = random.choice(agents.readlines())
        if debug:
            lib.output.debug("grabbed random User-Agent: {}".format(user_agent.strip()))
        return user_agent.strip()