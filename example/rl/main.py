import random
import sys
import signal
import threading

from example.rl.my_bot import MyBotTrainer, TRAINING_PLAYER_NUMBER
from src.lugo4py.protos import server_pb2
from src.lugo4py.rl.training_controller import TrainingController
from src.lugo4py.rl.gym import Gym
from src.lugo4py.client import LugoClient
from src.lugo4py.rl.remote_control import RemoteControl
from src.lugo4py.mapper import Mapper
from src.lugo4py.snapshot import DIRECTION
from typing import Tuple, Callable, Awaitable, Any
import grpc
import asyncio
import os
from src.lugo4py.loader import EnvVarLoader
from concurrent.futures import ThreadPoolExecutor
# Training settings
train_iterations = 50
steps_per_iteration = 600

grpc_address = "localhost:5000"
grpc_insecure = True

stop = threading.Event()

def my_training_function(training_ctrl: TrainingController, stopEvent: threading.Event):
    print("Let's train")

    possible_actions = [
        DIRECTION.FORWARD,
        DIRECTION.BACKWARD,
        DIRECTION.LEFT,
        DIRECTION.RIGHT,
        DIRECTION.BACKWARD_LEFT,
        DIRECTION.BACKWARD_RIGHT,
        DIRECTION.FORWARD_RIGHT,
        DIRECTION.FORWARD_LEFT,
    ]
    scores = []
    for i in range(train_iterations):
        try:
            scores.append(0)
            training_ctrl.setEnvironment({"iteration": i})

            for j in range(steps_per_iteration):
                if stopEvent.is_set():
                    training_ctrl.stop()
                    stop.set()
                    print("trainning stopped")
                    return

                sensors = training_ctrl.getState()

                # The sensors would feed our training model, which would return the next action
                action = possible_actions[random.randint(
                    0, len(possible_actions) - 1)]

                # Then we pass the action to our update method
                result = training_ctrl.update(action)
                # Now we should reward our model with the reward value
                scores[i] += result["reward"]
                if result["done"]:
                    # No more steps
                    print(f"End of train_iteration {i}, score:", scores[i])
                    break

        except Exception as e:
            print("error during trainning session:", e)

    training_ctrl.stop()
    print("Training is over, scores:", scores)
    stop.set()

if __name__ == "__main__":

    team_side = server_pb2.Team.Side.HOME
    print('main: Training bot team side = ', team_side)
    # The map will help us see the field in quadrants (called regions) instead of working with coordinates
    # The Mapper will translate the coordinates based on the side the bot is playing on
    map = Mapper(20, 10, server_pb2.Team.Side.HOME)

    # Our bot strategy defines our bot initial position based on its number
    initial_region = map.getRegion(5, 4)

    # Now we can create the bot. We will use a shortcut to create the client from the config, but we could use the
    # client constructor as well
    lugo_client = LugoClient(
        grpc_address,
        grpc_insecure,
        "",
        team_side,
        TRAINING_PLAYER_NUMBER,
        initial_region.getCenter()
    )
    # The RemoteControl is a gRPC client that will connect to the Game Server and change the element positions
    rc = RemoteControl()
    rc.connect(grpc_address)  # Pass address here

    bot = MyBotTrainer(rc)

    gymExecutor = ThreadPoolExecutor()
    # Now we can create the Gym, which will control all async work and allow us to focus on the learning part
    gym = Gym(gymExecutor, rc, bot, my_training_function, {"debugging_log": False})

    # First, starting the game server
    # If you want to train playing against another bot, then you should start the other team first.
    # If you want to train using two teams, you should start the away team, then start the training bot, and finally start the home team

    WithZombiePlayers = gym.withZombiePlayers(grpc_address)

    playersExecutor = ThreadPoolExecutor(22)
    WithZombiePlayers.start(lugo_client, playersExecutor)


    def signal_handler(sig, frame):
        print("Stop requested\n")
        lugo_client.stop()
        gym.stop()
        playersExecutor.shutdown(wait=True)
        gymExecutor.shutdown(wait=True)

    signal.signal(signal.SIGINT, signal_handler)

    stop.wait()
