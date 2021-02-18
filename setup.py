from distutils.core import setup
import py2exe
import win32gui
import win32.lib.win32con as win32con

import asyncio, psutil
import pypresence, time
import json
from utils import get_lockfile, get_session, get_presence, get_game_presence, parse_time, to_map_name
from exception import RiotAuthError, RiotTimeoutError, RiotPresenceError, RiotRefuseError

import os, requests, base64, iso8601
import urllib3

setup_dict = dict(console=[
    {
        "script": "main.py",
        "icon_resources": [(0, "favicon.ico")]
    }
]) # Calls setup function to indicate that we're dealing with a single console application
setup(**setup_dict)