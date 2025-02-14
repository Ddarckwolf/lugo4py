from concurrent.futures import ThreadPoolExecutor

from ..client import LugoClient
from ..mapper import Mapper
from ..snapshot import GameSnapshotReader

PLAYER_POSITIONS = {
    1: {'Col': 0, 'Row': 1},
    2: {'Col': 1, 'Row': 1},
    3: {'Col': 2, 'Row': 1},
    4: {'Col': 3, 'Row': 1},
    5: {'Col': 4, 'Row': 1},
    6: {'Col': 5, 'Row': 1},
    7: {'Col': 6, 'Row': 1},
    8: {'Col': 7, 'Row': 1},
    9: {'Col': 8, 'Row': 1},
    10: {'Col': 9, 'Row': 1},
    11: {'Col': 10, 'Row': 1},
}


def chaser_turn_handler(team_side, player_number, order_set, snapshot):
    reader = GameSnapshotReader(snapshot, team_side)
    order_set.addOrders(reader.makeOrderCatch())
    me = reader.get_player(team_side, player_number)
    if not me:
        raise ValueError("did not find myself in the game")

    order_set.addOrders(reader.make_order_move_max_speed(
        me.getPosition(), snapshot.getBall().getPosition()))
    order_set.setDebugMessage(
        f"{'HOME' if team_side == 0 else 'AWAY'}-{player_number} #{snapshot.turn} - chasing ball")
    return order_set


# @background
def newZombieHelperPlayer(team_side, player_number, game_server_address, executor: ThreadPoolExecutor):
    def zombie_turn_handler(order_set, snapshot):
        # print(f"Zombiw {'HOME' if team_side == 0 else 'AWAY'}-{player_number} got new snapthos")
        order_set.debug_message = f"{'HOME' if team_side == 0 else 'AWAY'}-{player_number} #{snapshot.turn}"
        return order_set

    #
    return newCustomHelperPlayer(team_side, player_number, game_server_address, zombie_turn_handler, executor)


def newChaserHelperPlayer(team_side, player_number, game_server_address):
    return newCustomHelperPlayer(team_side, player_number, game_server_address, chaser_turn_handler)


def newCustomHelperPlayer(team_side, player_number, game_server_address, turn_handler_function,
                          executor: ThreadPoolExecutor):
    try:
        # print(f'Creating {team_side} and {player_number}\n')
        initial_region = Mapper(22, 5, team_side).get_region(
            PLAYER_POSITIONS[player_number]['Col'], PLAYER_POSITIONS[player_number]['Row'])

        lugo_client = LugoClient(
            game_server_address,
            True,
            "",
            team_side,
            player_number,
            initial_region.get_center(),
        )

        def muted():
            None

        # print(f'Vai connectar {team_side} and {player_number}\n')
        lugo_client.play(executor, turn_handler_function, muted)
        return lugo_client
    except Exception as e:
        lugo_client.stop()
        raise e
