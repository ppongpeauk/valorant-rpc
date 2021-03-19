print("""
[VALORANT-RPC] by restrafes
The source code for this project can be found at: https://github.com/restrafes/valorant-rpc
""")
# import libraries
import os, sys, subprocess, psutil
import asyncio, threading
import pypresence, time
import json

from psutil import AccessDenied
from utils import get_lockfile, get_session, get_presence, get_game_presence, parse_time, to_map_name
from exception import RiotAuthError, RiotTimeoutError, RiotPresenceError, RiotRefuseError

import pystray, ctypes
from pystray import Icon as icon, Menu as menu, MenuItem as item
from PIL import Image, ImageDraw
from tkinter import Tk, PhotoImage, messagebox

if __name__ == "__main__":
    # load configuration
    global config, rpc, systray, systray_thread
    
    # window for messageboxes (and maybe other things in the future???)
    tkinter_window = Tk()
    tkinter_window.iconphoto(False, PhotoImage(file="resources/favicon.png"))
    tkinter_window.withdraw() # hide root window

    try:
        # open config
        with open("config.json", "r") as config_file:
            config = json.load(config_file)
            config_file.close()

        # main exit process method
        def exit_program():
            global systray, rpc
            rpc.close()
            systray.stop()
            sys.exit() # close the process

        # hide the console window if debug is off
        window_shown = config["debug"]
        kernel32, user32 = ctypes.WinDLL('kernel32'), ctypes.WinDLL('user32')
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
                user32.ShowWindow(hWnd, window_shown)
            except:
                pass

        def run_systray():
            global systray, window_shown
            systray_menu = menu(
                item('VALORANT-RPC by restrafes', tray_window_toggle, enabled=False),
                item('Show Debug Window', tray_window_toggle, checked=lambda item: window_shown),
                item('Quit', exit_program)
            )
            systray = pystray.Icon("VALORANT RPC", Image.open("resources/favicon.ico"), "VALORANT RPC", systray_menu)
            systray.run()

        def is_process_running(required_processes=["VALORANT-Win64-Shipping.exe", "RiotClientServices.exe"]):
            processes = []
            for proc in psutil.process_iter():
                try:
                    processes.append(proc.name())
                except (PermissionError, AccessDenied):
                    pass # some processes are higher than user-level and cannot have its attributes accessed
            for process in required_processes:
                if process in processes:
                    return True
            return False

        # discord rpc implementation
        rpc = pypresence.Presence(client_id=str(config["client_id"]))
        rpc_menu_default = {"large_image": "valorant-logo", "large_text": "VALORANT®"}
        rpc_gamemode_equivalents = config["rpc_gamemode_equivalents"]

        # if this is a clean run, start valorant and wait for authentication
        # TODO possibly auto-detect the install directory instead of having the end-user create an environment path :]
        if not is_process_running():
            print("VALORANT not running, launching Riot Client...")
            subprocess.Popen([
                    os.environ['VRPC_RCS'],
                    "--launch-product=valorant",
                    "--launch-patchline=live"
                ])
            while not is_process_running():
                time.sleep(1)

        # connect rpc
        rpc.connect()

        # create a thread for systray
        systray_thread = threading.Thread(target=run_systray)
        systray_thread.start()

        # yield for the lockfile containing all necessary credentials for the local riot api
        lockfile, lockfile_wait_cycles = None, 0
        while (config["fetch_timeout"] <= lockfile_wait_cycles or config["fetch_timeout"] < 0) and lockfile is None and is_process_running():
            print(f"Waiting for LOCKFILE data... (Cycle #{lockfile_wait_cycles})")
            lockfile_wait_cycles += 1
            try:
                lockfile = get_lockfile()
            except:
                pass
        if lockfile is None: # close the program if a timeout is set and reached and no lockfile is detected
            print("LOCKFILE fetching timeout exceeded, exiting script...")
            exit_program()
        print(f"LOCKFILE: {lockfile}")

        # yield for session data from the local riot api
        session, session_wait_cycles = None, 0
        while (config["fetch_timeout"] <= session_wait_cycles or config["fetch_timeout"] < 0) and session is None and is_process_running():
            print(f"Waiting for game session data... (Cycle #{session_wait_cycles})")
            session_wait_cycles += 1
            try:
                session = get_session(lockfile, config)
            except RiotAuthError:
                print("Logged out response received, continue to yield...")
            except RiotRefuseError:
                print("Error 403 received, exiting script...")
                session = None
                exit_program()
            time.sleep(1)
        if session is None: # close the program if a timeout is set and reached and no session is detected
            print("Game session fetch timeout exceeded, exiting script...")
            exit_program()
        print(f"Session: {session}")

        # main script
        while is_process_running():
            time.sleep(config["update_interval"])
            network_presence = get_presence(lockfile, session, config)
            game_presence = get_game_presence(network_presence)
            if network_presence["state"] == "away": # if the game is idle on the menu screen
                get_state = "In a Party" if game_presence["partySize"] > 1 else "Solo"
                rpc.update(
                    **rpc_menu_default,
                    details = "Away",
                    party_size = [game_presence["partySize"], game_presence["maxPartySize"]],
                    state = get_state,
                    small_image = "away",
                    small_text = "Away"
                )
            else: # if the player is in the lobby or in-game
                if game_presence["sessionLoopState"] == "MENUS": # if the player is on the menu screem
                    get_state = ""
                    get_start = None
                    if game_presence["partyState"] == "MATCHMAKING":
                        get_state = "In Queue"
                        get_start = parse_time(game_presence["queueEntryTime"])
                    else:
                        get_state = "In a Party" if game_presence["partySize"] > 1 else "Solo"

                    rpc.update(
                        **rpc_menu_default,
                        details = (rpc_gamemode_equivalents[game_presence["queueId"]] if game_presence["queueId"] in rpc_gamemode_equivalents else "Discovery") + " (Lobby)",
                        party_size = [game_presence["partySize"], game_presence["maxPartySize"]],
                        state = get_state,
                        start = get_start
                    )
                elif game_presence["sessionLoopState"] in ["INGAME", "PREGAME"]: # if the player is on the agent select screen or in a round
                    match_type = (rpc_gamemode_equivalents[game_presence["queueId"]] if game_presence["queueId"] in rpc_gamemode_equivalents else "Discovery")
                    get_start = game_presence["partyVersion"]
                    get_state = ""
                    if game_presence["sessionLoopState"] == "INGAME":
                        get_state = "In a Party" if game_presence["partySize"] > 1 else "Solo"
                    elif game_presence["sessionLoopState"] == "PREGAME":
                        get_state = "Agent Select"
                        
                    rpc.update(
                        details = f"{match_type}: {game_presence['partyOwnerMatchScoreAllyTeam']} - {game_presence['partyOwnerMatchScoreEnemyTeam']}",
                        party_size = [game_presence["partySize"], game_presence["maxPartySize"]],
                        state = get_state,
                        start = get_start,
                        large_image = f"{to_map_name(config, game_presence['matchMap'], True).lower()}-splash",
                        large_text = f"{to_map_name(config, game_presence['matchMap'])}",
                        small_image = f"{match_type.lower()}-icon",
                        small_text = f"{match_type}"
                    )
        print("The game process is no longer running, exiting script...")
        exit_program()
    except RuntimeError:
        pass # don't error out when the event loop is closed
    except Exception as program_exception:
        print(f"THERE WAS AN ERROR WHILE RUNNING THE PROGRAM: {program_exception}")
        messagebox.showerror(title="VALORANT RPC by restrafes", message=f"There was a problem while running the program:\n{program_exception}")
        sys.exit()