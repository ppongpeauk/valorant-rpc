print("loading VALORANT RPC extension by restrafes")
# import libraries
import os, subprocess
import asyncio, psutil
import pypresence, time
import json
from psutil import AccessDenied
from utils import get_lockfile, get_session, get_presence, get_game_presence, parse_time, to_map_name
from exception import RiotAuthError, RiotTimeoutError, RiotPresenceError, RiotRefuseError
import pystray
from pystray import Icon as icon, Menu as menu, MenuItem as item
from PIL import Image, ImageDraw
import threading
# for hiding the console window
import ctypes
# for future threading
event_loop = asyncio.get_event_loop()
# load configuration
global config, rpc, systray, systray_thread
with open("config.json", "r") as configfile:
    config = json.load(configfile)
    configfile.close()

def close_program():
    global systray, rpc
    rpc.close()
    systray.stop()
    raise SystemExit(0) # stop everything and close the process

# hide the console window if debug is off
window_shown = config["debug"]
kernel32 = ctypes.WinDLL('kernel32')
user32 = ctypes.WinDLL('user32')
if not config["debug"]:
    try:
        hWnd = kernel32.GetConsoleWindow()
        user32.ShowWindow(hWnd, 0)
    except:
        pass

# console visibility toggle functionality
def tray_window_toggle(icon, item):
    try:
        global window_shown
        window_shown = not item.checked
        hWnd = kernel32.GetConsoleWindow()
        if window_shown:
            user32.ShowWindow(hWnd, 1)
        else:
            user32.ShowWindow(hWnd, 0)
    except:
        pass

print("initializing systray object")
def run_systray():
    global systray, window_shown
    systray_image = Image.open("favicon.ico")
    systray_menu = menu(
        item('Show Debug Window', tray_window_toggle, checked=lambda item: window_shown),
        item('Quit', close_program),
        item('by restrafes', tray_window_toggle, enabled=False),
    )
    systray = pystray.Icon("VALORANT RPC", systray_image, "VALORANT RPC", systray_menu)
    systray.run()
print("done initializing the systray object")

def is_process_running(required_processes=["VALORANT-Win64-Shipping.exe", "RiotClientServices.exe"]):
    processes = []
    for proc in psutil.process_iter():
        try:
            processes.append(proc.name())
        except (PermissionError, AccessDenied):
            pass # some processes are high-level and cannot have its attributes accessed!
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
if __name__ == "__main__":
    if not is_process_running():
        print("client not running, launching the riot client application..")
        subprocess.Popen([os.environ['VRPC_RCS'], "--launch-product=valorant", "--launch-patchline=live"])
        while not is_process_running():
            time.sleep(1)
            
    rpc.connect()
    systray_thread = threading.Thread(target=run_systray)
    systray_thread.start()

    lockfile = None
    lockfile_wait_cycles = 0
    while (config["fetch_timeout"] <= lockfile_wait_cycles or config["fetch_timeout"] < 0) and lockfile is None and is_process_running():
        print(f"waiting for lockfile data ({lockfile_wait_cycles})")
        lockfile_wait_cycles += 1
        try:
            lockfile = get_lockfile()
        except:
            pass
    
    if lockfile is None:
        print("lockfile fetch timeout exceeded, stopping script")
        close_program()

    print(f"LOCKFILE: {lockfile}")

    session = None
    session_wait_cycles = 0
    
    while (config["fetch_timeout"] <= session_wait_cycles or config["fetch_timeout"] < 0) and session is None and is_process_running():
        print(f"waiting for session data ({session_wait_cycles})")
        session_wait_cycles += 1
        try:
            session = get_session(lockfile, config)
        except RiotAuthError:
            print("logged out response fetched, continue to yield")
        except RiotRefuseError:
            print("error code 403 fetched, stopping script")
            session = None
            close_program()
        time.sleep(1)

    if session is None:
        print("session fetch timeout exceeded, stopping script")
        close_program()
    print(f"SESSION: {session}")

    while True:
        time.sleep(config["update_interval"])
        if not is_process_running():
            print("the game process is no longer running, stopping script")
            close_program()
            break
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
                        state = get_state
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
                            start = get_start
                        )
                    elif game_presence["sessionLoopState"] in ["INGAME", "PREGAME"]:
                        match_type = (rpc_gamemode_equivalents[game_presence["queueId"]] if game_presence["queueId"] in rpc_gamemode_equivalents else "Discovery")
                        get_start = game_presence["partyVersion"]
                        get_state = ""
                        if game_presence["sessionLoopState"] == "INGAME":
                            #get_state = f"In a Party" # 
                            if game_presence["partySize"] > 1:
                                get_state = "In a Party"
                            else:
                                get_state = "Solo"
                        elif game_presence["sessionLoopState"] == "PREGAME":
                            get_state = "Agent Select"
                        rpc.update(
                            large_image = f"{to_map_name(config, game_presence['matchMap'], True).lower()}-splash",
                            large_text = f"{to_map_name(config, game_presence['matchMap'])}",
                            small_image = f"{match_type.lower()}-icon",
                            small_text = f"{match_type}",
                            pid = int(lockfile["pid"]),
                            details = f"{match_type}: {game_presence['partyOwnerMatchScoreAllyTeam']} - {game_presence['partyOwnerMatchScoreEnemyTeam']}",
                            party_size = [game_presence["partySize"], game_presence["maxPartySize"]],
                            state = get_state,
                            start = get_start
                        )
            except RiotPresenceError:
                pass
    close_program()
else:
    print("the game process isn't running, stopping script")