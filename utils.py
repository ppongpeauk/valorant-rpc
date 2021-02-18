import os, requests, base64, json, iso8601
from exception import RiotAuthError, RiotTimeoutError, RiotPresenceError, RiotRefuseError
import urllib3
urllib3.disable_warnings()

lockfile_path = os.getenv("localappdata") + R'\Riot Games\Riot Client\Config\lockfile'
def generate_headers(lockfile):
    return {
        # for some reason, riot encodes authorization in base64??
        "Authorization": f"Basic {base64.b64encode(('riot:' + lockfile['auth_key']).encode()).decode()}"
    }

def get_lockfile():
    with open(lockfile_path) as file:
        data = file.read().split(":")
        return dict(zip([
            "name",
            "pid",
            "listening_port",
            "auth_key",
            "protocol"], 
            data
            )
        )

def get_session(lockfile, config):
    headers = generate_headers(lockfile)
    response = None
    try:
        response = requests.get(f"{config['base_endpoint']}:{lockfile['listening_port']}{config['session_endpoint']}", headers=headers, verify=False)
    except:
        pass
    if response.status_code == 403:
        raise RiotRefuseError
    elif response.status_code == 200:
        response_json = response.json()
        if response_json["state"] == "connected":
            return response_json
        elif response_json["state"] == "disconnected":
            raise RiotAuthError

def get_puuid(session):
    return session["puuid"]

def get_presence(lockfile, session, config):
    headers = generate_headers(lockfile)
    response = None
    try:
        response = requests.get(f"{config['base_endpoint']}:{lockfile['listening_port']}{config['presence_endpoint']}", headers=headers, verify=False)
    except:
        pass
    response_json = response.json()

    for presence in response_json["presences"]:
        if presence["puuid"] == get_puuid(session):
            return presence
    raise RiotPresenceError

def get_game_presence(presence):
    return json.loads(base64.b64decode(presence["private"].encode()).decode())

def parse_time(time): # from colinhartigan/valorant-rich-presence
    time = str(time)
    split = time.split("-")
    split[0] = split[0].replace(".","-")
    split[1] = split[1].replace(".",":")
    split = "T".join(i for i in split)
    split = iso8601.parse_date(split).timestamp()
    return split

def to_map_name(map, ignore_alias=False):
    maps = {
        "Port": "Icebox",
        "Duality": "Bind",
        "Bonsai": "Split",
        "Ascent": "Ascent",
        "Triad": "Haven",
        "Range": "Range"
    }
    split = map.split("/")
    if not ignore_alias:
        if len(split) > 1:
            return maps[split[len(split)-1]]
        else:
            return "Unknown"
    else:
        if len(split) > 1:
            return split[len(split)-1]
        else:
            return "Unknown"