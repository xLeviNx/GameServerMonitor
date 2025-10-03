import time
from typing import TYPE_CHECKING
import aiohttp
import zlib
import json
from discordgsm.protocols.protocol import Protocol

if TYPE_CHECKING:
    from discordgsm.gamedig import GamedigResult

class Fika(Protocol):
    name = "fika"

    async def query(self):
        """Query the Fika server"""
        host, port = str(self.kv["host"]), int(str(self.kv["port"]))
        session_id = self.kv.get("session_id", "")  # Optional session ID
        VERSION_PATH = "/launcher/server/version" # From SPT server/project/src/routers/static/LauncherStaticRouters.ts - gets SPT version Number (also used as up/down status)
        PRESENCE_PATH = "/fika/presence/get" # From Fika-Plugin/Fika.Core/Networking/Http/FikaRequestHander.cs - gets list of players and their activities
        serverVersion = None
        presenceData = None

        async with aiohttp.ClientSession() as session:
            # Start timing for ping
            start = time.time()
            headers = {"Cookie": f"PHPSESSID={session_id}"} if session_id else {}
            
            # Make request for SPT Version / check if server is running
            async with session.get(
                f"http://{host}:{port}{VERSION_PATH}",
                headers=headers,
                timeout=self.timeout
            ) as versionResponse:
                if not versionResponse.ok:
                    raise Exception(f"HTTP {versionResponse.status}")
                serverVersion = json.loads(zlib.decompress(await versionResponse.read()))
            
            # Make request for player information
            async with session.get(
                f"http://{host}:{port}{PRESENCE_PATH}",
                headers=headers,
                timeout=self.timeout
            ) as presenceResponse:
                #if not presenceResponse.ok:
                    #raise Exception(f"HTTP {presenceResponse.status}")
                presenceData = json.loads(zlib.decompress(await presenceResponse.read()))
                
            # Calculate ping
            ping = int((time.time() - start) * 1000)

            # Activity mapping
            activity_map = {
                0: "Menu",
                1: "Raid",
                2: "Stash",
                3: "Hideout",
                4: "Flea"
            }

            # Location mapping
            location_map = {
                "factory4_day": "Factory",
                "factory4_night": "Factory",
                "bigmap": "Customs",
                "laboratory": "Labs",
                "woods": "Woods",
                "interchange": "Interchange",
                "lighthouse": "Lighthouse",
                "reservbase": "Reserve",
                "shoreline": "Shoreline",
                "tarkovstreets": "Streets"
            }

            players = []
            # Process players
            if presenceData:
                for player in presenceData:
                    player_info = {
                        "name": str(player["nickname"]) + " in " + str(activity_map.get(player["activity"], "Unknown")),
                        "raw": {
                            "level": player["level"],
                            "activity": activity_map.get(player["activity"], "Unknown"),
                            "activityStarted": player["activityStartedTimestamp"]
                        }
                    }

                    # Add raid information if available
                    if player.get("raidInformation"):
                        raid_info = player["raidInformation"]
                        player_info["raw"]["raid"] = {
                            "location": location_map.get(raid_info["location"], raid_info["location"]),
                            "side": "Scav" if raid_info["side"] == "Savage" else "PMC" if raid_info["side"] == "Pmc" else raid_info["Side"],
                            "time": raid_info["time"]
                        }
                        player_info["name"] += " as " + str(player_info["raw"]["raid"]["side"]) + " at "+ str(player_info["raw"]["raid"]["location"])
            
                    players.append(player_info)

            with open('output.txt', 'a') as f:
                f.write(str(players))

            # Construct the result
            result: GamedigResult = {
                "name": f"Fika SPT v{str(serverVersion)}",
                "map": "",
                "password": False,
                "numplayers": len(players),
                "numbots": 0,
                "maxplayers": 5,
                "players": players,
                "bots": [],
                "connect": f"{host}:{port}",
                "ping": ping,
                "raw": {}
            }
            return result
