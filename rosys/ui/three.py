from rosys.world.robot import RobotShape
from typing import Callable
import time
from nicegui.elements.custom_view import CustomView
from nicegui.elements.element import Element
from ..world.pose import Pose
from ..world.image import Image
from ..world.camera import Camera
from ..world.spline import Spline


class ThreeView(CustomView):

    def __init__(self, *, follow_robot: bool, robot_shape: RobotShape, on_click: Callable):

        super().__init__('three', __file__, ['three.min.js', 'OrbitControls.js'],
                         robots={}, robot_shape=robot_shape.dict(), follow_robot=follow_robot,
                         images=[], path=[], path_time=0)

        self.on_click = on_click
        self.allowed_events = ['onClick']
        self.initialize(temp=False, onClick=self.handle_click)

    def handle_click(self, msg):

        if self.on_click is not None:
            return self.on_click(msg)
        return False


class Three(Element):

    def __init__(self, *, robot_shape: RobotShape, follow_robot: bool = True, on_click: Callable = None):

        super().__init__(ThreeView(follow_robot=follow_robot, robot_shape=robot_shape, on_click=on_click))

    def set_robot(self, id: str, color: str, pose: Pose):

        new_pose = pose.dict() | {'color': color}
        del new_pose['time']
        if self.view.options.robots.get(id) == new_pose:
            return False
        self.view.options.robots[id] = new_pose

    def update_images(self, images: list[Image], cameras: dict[str, Camera]):

        latest_images = {image.mac: image for image in images}
        self.view.options.images = [
            image.dict() | {'camera': cameras[image.mac].dict()}
            for image in latest_images.values()
            if image.mac in cameras and cameras[image.mac].projection is not None
        ]

    def update_path(self, path: list[Spline]):

        new_path = [spline.dict() for spline in path]
        if self.view.options.path == new_path:
            return False
        self.view.options.path = new_path
        self.view.options.path_time = time.time()
