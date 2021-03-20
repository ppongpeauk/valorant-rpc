import os, subprocess, requests, base64, json, iso8601
from exception import RiotRefuseError, RiotDataNotFoundError
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
    if response:
        if response.status_code == 403:
            raise RiotRefuseError
        elif response.status_code == 200:
            response_json = response.json()
            return response_json if response_json["state"] == "connected" else None
    else:
        return None

def get_puuid(session):
    return session["puuid"]

def get_presence(lockfile, session, config):
    headers = generate_headers(lockfile)
    response, response_json = None, None
    try:
        response = requests.get(f"{config['base_endpoint']}:{lockfile['listening_port']}{config['presence_endpoint']}", headers=headers, verify=False)
        response_json = response.json()
    except:
        pass
    if response:
        for presence in response_json["presences"]:
            if presence["puuid"] == get_puuid(session):
                return presence
    return None

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

def to_map_name(config, map, ignore_alias=False):
    maps = config["rpc_map_equivalents"]
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

def open_game_client():
    installer_file = os.path.expandvars("%PROGRAMDATA%\\Riot Games\\RiotClientInstalls.json")
    try:
        with open(installer_file, "r") as installer_data:
            installer_data_json = json.load(installer_data)
            if "rc_default" in installer_data_json:
                subprocess.Popen([
                    installer_data_json["rc_default"],
                    "--launch-product=valorant",
                    "--launch-patchline=live"
                ])
            else:
                raise RiotDataNotFoundError("The path to Riot Client could not be found. Ensure that it is installed and try again.")
    except FileNotFoundError:
        raise RiotDataNotFoundError("The path to Riot Client could not be found. Ensure that it is installed and try again.")
