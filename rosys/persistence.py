import logging
import json
import os
from .world.camera import Camera
from .world.obstacle import Obstacle
from .world.path_segment import PathSegment
from .world.robot import RobotParameters
from .world.link import Link
from .world.world import World


def dump(world: World) -> dict:

    exclude = {'projection', 'synchronization'}
    return {
        'cameras': {mac: camera.dict(exclude=exclude) for mac, camera in world.cameras.items()},
        'path': [path_segment.dict() for path_segment in world.path],
        'robot': {'parameters': world.robot.parameters.dict()},
        'links': [link.dict() for link in world.links],
        'obstacles': {id: obstacle.dict() for id, obstacle in world.obstacles.items()},
    }


def load(world: World, dict: dict):

    world.cameras = {mac: Camera.parse_obj(camera) for mac, camera in dict['cameras'].items()}
    world.path = [PathSegment.parse_obj(path_segment) for path_segment in dict['path']]
    world.robot.parameters = RobotParameters.parse_obj(dict['robot']['parameters'])
    world.links = [Link.parse_obj(link) for link in dict['links']]
    world.obstacles = {id: Obstacle.parse_obj(obstacle) for id, obstacle in dict['obstacles'].items()}


def backup(world: World, filepath):

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(dump(world), f)


def restore(world: World, filepath: str):

    if not os.path.exists(filepath):
        logging.warning('No backup file found.')
        return

    try:
        with open(filepath, 'r') as f:
            load(world, json.load(f))
    except:
        logging.exception('Could not load from backup')
