from pydantic import BaseModel
from typing import Tuple
import numpy as np


class Pose(BaseModel):

    x: float = 0
    y: float = 0
    yaw: float = 0

    def __str__(self):
        return '%.3f, %.3f, %.1f deg' % (self.x, self.y, np.rad2deg(self.yaw))

    def tuple(self) -> Tuple:
        return (self.x, self.y, self.yaw)
