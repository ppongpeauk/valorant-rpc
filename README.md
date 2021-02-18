# Valorant-RPC

Valorant-RPC is a non-native Discord RPC integration for VALORANT.

![alt text](https://github.com/restrafes/valorant-rpc/blob/master/assets/example_1.png?raw=true)
![alt text](https://github.com/restrafes/valorant-rpc/blob/master/assets/example_2.png?raw=true)

## Before Installation
**rpc-extension.exe** will automatically start the Riot Client/VALORANT in the case that neither programs are found to be a running process. If you do not wish to have it run every time you start VALORANT, simply don't follow the instructions below.

## Installation
1. Locate where your Riot Client is (specifically, RiotClientServices.exe.) This is usually located in the same folder where VALORANT is installed
2. Pull up the 'Environment Variables' settings page
3. Add a new system variable, the name being **"VRPC_RCS"** and the value being the full path to the **RiotClientServices.exe** executable (e.g. E:\Games\Riot Games\Riot Client\RiotClientServices.exe)
5. Extract the zip file provided in the 'Releases' tab
6. Place the extracted folder somewhere that's not temporary (e.g. your games folder)
7. Locate your VALORANT shortcut(s), modify the "Target" property under the "Shortcut" tab to be the full path to the **rpc-extension.exe** executable located in the zip file

