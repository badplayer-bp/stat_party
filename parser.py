import struct
import datetime
import sqlite3
import os

# "constants"
DB_FILENAME = "statparty.db"
CONFIG_FILENAME = "statparty"

FILE_VERSION = 4

SHORT = ('H', 2)
INT = ('I', 4)
BYTE = ('B', 0)
FLOAT = ('f', 4)

RESULTS = {
    0: "Missions Win",
    1: "Spy Timeout",
    2: "Spy Shot",
    3: "Civilian Shot",
    4: "In Progress"
}

GAME_TYPE = {
    0: "Known",
    1: "Pick",
    2: "Any"
}

MAPS = {
    2646981470: "Courtyard",
    775418203: "Moderne",
    378490722: "Library",
    1870767448: "Veranda",
    1903409343: "Gallery",
    1527912741: "Ballroom",
    998637555: "Pub",
    441894305: "High-rise",
    2419248674: "Terrace",
    498961985: "Balcony"
}

MISSIONS = {
    0: "Bug Ambassador",
    1: "Contact Double Agent",
    2: "Transfer Microfilm",
    3: "Swap Statue",
    4: "Inspect Target",
    5: "Seduce Target",
    6: "Purloin Guest List",
    7: "Fingerprint Ambassador"
}

SELECTED = 0x40
PICKED = 0x44
COMPLETED = 0x48

MISSION_STATES = {
    0x40: "Selected",
    0x44: "Picked",
    0x48: "Completed"
}

class ReplayParser:

    def __init__(self, filename):
        self.filename = filename
        self.bytes_read = None

    def unpack_value(self, val_type, offset):
        read_bytes = self.bytes_read[offset:(offset + val_type[1])]
        return struct.unpack(val_type[0], read_bytes)[0]

    def parse(self):
        with open(self.filename, "rb") as f:
            self.bytes_read = f.read(80 + 2 * 33)

        if not self.bytes_read[:4].decode() == "RPLY":
            print("Invalid file format detected, skipping " + 
                  self.filename)
            return None
        
        if not self.unpack_value(INT, 0x04) == FILE_VERSION:
            print("Only version 4 replay files supported, skipping " + 
                  self.filename)
            return None

        spy_name_len = self.bytes_read[0x2E]
        sniper_name_len = self.bytes_read[0x2F]
        spy_name = self.bytes_read[0x54:(0x54 + spy_name_len)].decode()
        sniper_name = self.bytes_read[0x54 + spy_name_len:
            (0x54 + spy_name_len + sniper_name_len)].decode()

        result = RESULTS[self.unpack_value(INT, 0x34)]
        map_ = MAPS[self.unpack_value(INT, 0x3C)]

        missions = dict()
        for address in MISSION_STATES:
            missions[address] = set()
            mission_data = self.unpack_value(INT, address)
            for offset in MISSIONS:
                if mission_data & (1 << offset):
                    missions[address].add(MISSIONS[offset])
        
        start_time = datetime.datetime.fromtimestamp(
            self.unpack_value(INT, 0x28))
        duration = int(self.unpack_value(FLOAT, 0x14))

        return {'spy': spy_name,
                'sniper': sniper_name,
                'start_time': start_time,
                'duration': duration,
                'map' : map_,
                'result': result,
                'missions': missions
                }

class DBHandler:

    def __init__(self, filename):
        self.filename = filename
       #self.connection = sqlite3.connect(filename)


def main():
    replay_dir = os.getenv("LOCALAPPDATA")
    track_matches = None
    track_spectations = None

    if replay_dir is None:
        print("Unable to locate Local App Data directory. " + 
              "StatParty current only supports Windows systems.")
        raise SystemExit(0)
    replay_dir += "\\SpyParty\\replays"
    parsed_dirs = set()

    first_run = False if os.path.isfile(replay_dir + 
        '\\{0}'.format(CONFIG_FILENAME)) else True

    if first_run:
        choices = ['y', 'n', '']
        fo = open(replay_dir + '\\{0}'.format(CONFIG_FILENAME), 'w')
        print("No config file found, assuming this is " + 
              "your first time running StatParty.")
        
        while track_matches not in choices:
            track_matches = input("Would you like to track standard " + 
                                  "matches? (Y/n): ").strip().lower()
        track_matches = False if track_matches == 'n' else True
        
        while track_spectations not in choices:
            track_spectations = input("Would you like to track spectated " + 
                                      "matches? (y/N): ").strip().lower()
        track_spectations = True if track_spectations == 'y' else False
        
        last_checked_time = datetime.datetime.now().timestamp()
        fo.writelines([repr(last_checked_time) + "\n", repr(track_matches) +
                      "\n", repr(track_spectations)])
        fo.close()
    else:
        print("Reading config file.")
        fo = open(replay_dir + "\\{0}".format(CONFIG_FILENAME), 'r+')
        last_checked_time = float(fo.readline())
        track_matches = True if fo.readline() == "True" else False
        track_spectations = True if fo.readline() == "True" else False
        fo.seek(0,0)
        fo.writelines([repr(datetime.datetime.now().timestamp()) + "\n"])
        fo.close()
    if track_matches: parsed_dirs.add("\\Matches")
    if track_spectations: parsed_dirs.add("\\Spectations")

    db = DBHandler(replay_dir + "\\" + DB_FILENAME)

    for parsed_dir in parsed_dirs:
        for root, dir, file in os.walk(replay_dir + parsed_dir):
            for f in file:
                full_path = os.path.join(root,f)
                if first_run or (os.path.getmtime(full_path) > last_checked_time
                               and '.replay' in f):
                    replay = ReplayParser(os.path.join(root, f))
                    parsed_data = replay.parse()
                    print("Spy name: {0} Sniper name: {1}".format(
                        parsed_data["spy"], parsed_data["sniper"]))
                    print("Map: {0} Result: {1}".format(
                        parsed_data["map"], parsed_data["result"]))
                    print("Start time {0}: Duration: {1}".format(
                        parsed_data["start_time"], parsed_data["duration"]))
                    print("Missions (picked): {}".format(
                                        parsed_data["missions"][PICKED]))
                    print("Missions (selected): {}".format(
                                        parsed_data["missions"][SELECTED]))
                    print("Missions (completed): {}".format(
                                        parsed_data["missions"][COMPLETED])) 

    raise SystemExit(0)


if __name__ == '__main__':
    main()


            

