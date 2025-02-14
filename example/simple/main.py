import os
import signal
import sys

# both src are necessary to account for execution on docker and on project folder
sys.path.append("../../src")
sys.path.append("./src")
from concurrent.futures import ThreadPoolExecutor
from lugo4py.loader import EnvVarLoader
from lugo4py.mapper import Mapper
from lugo4py.client import NewClientFromConfig
from my_bot import MyBot

PLAYER_POSITIONS = {
    1: {'Col': 0, 'Row': 0},
    2: {'Col': 1, 'Row': 1},
    3: {'Col': 2, 'Row': 2},
    4: {'Col': 2, 'Row': 3},
    5: {'Col': 1, 'Row': 4},
    6: {'Col': 3, 'Row': 1},
    7: {'Col': 3, 'Row': 2},
    8: {'Col': 3, 'Row': 3},
    9: {'Col': 3, 'Row': 4},
    10: {'Col': 4, 'Row': 3},
    11: {'Col': 4, 'Row': 2},
}

if __name__ == "__main__":
    # Set necessary env variables for testing
    if False:
        os.environ['BOT_TEAM'] = 'HOME'
        os.environ['BOT_NUMBER'] = '2'
        os.environ['BOT_GRPC_URL'] = 'localhost:5000'

    # We must load the env vars following the standard defined by the game specs because all bots will receive the
    # arguments in the same format (env vars)

    config = EnvVarLoader()

    # The map will help us to see the field in quadrants (called regions) instead of working with coordinates
    mapper = Mapper(10, 6, config.get_bot_team_side())

    # Our bot strategy defines our bot initial position based on its number
    initialRegion = mapper.get_region(PLAYER_POSITIONS[config.get_bot_number()]['Col'],
                                      PLAYER_POSITIONS[config.get_bot_number()]['Row'])

    # Now we can create the bot. We will use a shortcut to create the client from the config, but we could use the
    # client constructor as well
    lugo_client = NewClientFromConfig(config, initialRegion.get_center())

    my_bot = MyBot(config.get_bot_team_side(), config.get_bot_number(), initialRegion.get_center(), mapper)


    def on_join():
        print("I may run it when the bot is connected to the server")


    executor = ThreadPoolExecutor()
    lugo_client.play_as_bot(executor, my_bot, on_join)
    print("We are playing!")


    def signal_handler(_, __):
        print("Stop requested\n")
        lugo_client.stop()
        sys.exit(0)


    signal.signal(signal.SIGINT, signal_handler)
    lugo_client.wait()
    print("bye!")
