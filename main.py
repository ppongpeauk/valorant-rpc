
print("loading VALORANT RPC extension")
# import libraries
import os, subprocess
import asyncio, psutil
import pypresence, time
import json
from psutil import AccessDenied
from utils import get_lockfile, get_session, get_presence, get_game_presence, parse_time, to_map_name
from exception import RiotAuthError, RiotTimeoutError, RiotPresenceError, RiotRefuseError
# for hiding the console window
import win32gui
import win32.lib.win32con as win32con
# for future threading
event_loop = asyncio.get_event_loop()
# load configuration
global config
with open("config.json", "r") as configfile:
    config = json.load(configfile)
    configfile.close()

# hide the console window if debug is off
if not config["debug"]:
    try:
        get_window = win32gui.GetForegroundWindow()
        win32gui.ShowWindow(get_window, win32con.SW_HIDE)
    except:
        pass

def is_process_running(required_processes=["VALORANT.exe", "RiotClientServices.exe"]):
    processes = []
    for proc in psutil.process_iter():
        try:
            processes.append(proc.name())
        except (PermissionError, AccessDenied):
            pass # can't display name or id here
    for process in required_processes:
        if process in processes:
            return True
    return False

# discord rpc implementation
rpc = pypresence.Presence(str(config["client_id"]), loop=event_loop)
rpc_menu_default = {
    "large_image": "valorant-logo",
    "large_text": "VALORANT®"
}
rpc_gamemode_equivalents = config["rpc_gamemode_equivalents"]

def close_rpc():
    try:
        rpc.close()
    except:
        pass
    
if __name__ == "__main__":
    if not is_process_running():
        print("client not running, start the riot client application")
        subprocess.Popen([os.environ['VRPC_RCS'], "--launch-product=valorant", "--launch-patchline=live"])
        while not is_process_running():
            time.sleep(1)

    rpc.connect()

    lockfile = None
    lockfile_wait_cycles = 0
    while (config["fetch_timeout"] <= lockfile_wait_cycles or config["fetch_timeout"] < 0) and lockfile is None and is_process_running():
        print(f"yielding for lockfile data ({lockfile_wait_cycles})")
        lockfile_wait_cycles += 1
        try:
            lockfile = get_lockfile()
        except:
            pass
    
    if lockfile is None:
        print("lockfile fetch timeout exceeded, aborting script")
        close_rpc()
        raise SystemExit(0)

    print(f"LOCKFILE: {lockfile}")

    session = None
    session_wait_cycles = 0
    
    while (config["fetch_timeout"] <= session_wait_cycles or config["fetch_timeout"] < 0) and session is None and is_process_running():
        print(f"yielding for session data ({session_wait_cycles})")
        session_wait_cycles += 1
        try:
            session = get_session(lockfile, config)
        except RiotAuthError:
            print("logged out response fetched, continue to yield")
        except RiotRefuseError:
            print("error code 403 fetched, aborting script")
            session = None
            close_rpc()
            raise SystemExit(0)
        time.sleep(1)

    if session is None:
        print("session fetch timeout exceeded, aborting script")
        close_rpc()
        raise SystemExit(0)
        
    print(f"SESSION: {session}")

    while True:
        time.sleep(config["update_interval"])
        if not is_process_running():
            print("the game process is no longer running, aborting script")
            close_rpc()
            raise SystemExit(0)
        else:
            try:
                network_presence = get_presence(lockfile, session, config)
                game_presence = get_game_presence(network_presence)
                if network_presence["state"] == "away":
                    get_state = ""
                    if game_presence["partyState"] == "MATCHMAKING":
                        get_state = "In Queue"
                        get_start = parse_time(game_presence["queueEntryTime"])
                    else:
                        if game_presence["partySize"] > 1:
                            get_state = "In a Party"
                        else:
                            get_state = "Solo"
                    rpc.update(
                        **rpc_menu_default,
                        pid = int(lockfile["pid"]),
                        details = "Away",
                        party_size = [game_presence["partySize"], game_presence["maxPartySize"]],
                        state = get_state,
                        join = game_presence["partyId"]
                    )
                elif network_presence["state"] in ["chat", "dnd"]:
                    if game_presence["sessionLoopState"] == "MENUS":
                        get_state = ""
                        get_start = None
                        if game_presence["partyState"] == "MATCHMAKING":
                            get_state = "In Queue"
                            get_start = parse_time(game_presence["queueEntryTime"])
                        else:
                            if game_presence["partySize"] > 1:
                                get_state = "In a Party"
                            else:
                                get_state = "Solo"
                        rpc.update(
                            **rpc_menu_default,
                            pid = int(lockfile["pid"]),
                            details = (rpc_gamemode_equivalents[game_presence["queueId"]] if game_presence["queueId"] in rpc_gamemode_equivalents else "Discovery") + " (Lobby)",
                            party_size = [game_presence["partySize"], game_presence["maxPartySize"]],
                            state = get_state,
                            start = get_start,
                            join = game_presence["partyId"]
                        )
                    elif game_presence["sessionLoopState"] in ["INGAME", "PREGAME"]:
                        match_type = (rpc_gamemode_equivalents[game_presence["queueId"]] if game_presence["queueId"] in rpc_gamemode_equivalents else "Discovery")
                        get_start = game_presence["partyVersion"]
                        get_state = ""
                        if game_presence["sessionLoopState"] == "INGAME":
                            #get_state = f"In a Party" # ({game_presence['partyOwnerMatchScoreAllyTeam']}-{game_presence['partyOwnerMatchScoreEnemyTeam']})
                            if game_presence["partySize"] > 1:
                                get_state = "In a Party"
                            else:
                                get_state = "Solo"
                        elif game_presence["sessionLoopState"] == "PREGAME":
                            get_state = "Agent Select"
                        rpc.update(
                            large_image = f"{to_map_name(game_presence['matchMap'], True).lower()}-splash",
                            large_text = f"Playing on {to_map_name(game_presence['matchMap']).upper()}",
                            small_image = f"{match_type.lower()}-icon",
                            small_text = f"In a {match_type.upper()} match",
                            pid = int(lockfile["pid"]),
                            details = f"{to_map_name(game_presence['matchMap'])} ({match_type})",
                            party_size = [game_presence["partySize"], game_presence["maxPartySize"]],
                            state = get_state,
                            start = get_start,
                            join = game_presence["partyId"]
                        )
            except RiotPresenceError:
                pass
    close_rpc()
    raise SystemExit(0)
else:
    print("the game process isn't running, aborting script")