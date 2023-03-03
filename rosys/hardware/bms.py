import abc
from typing import Callable, Optional

import numpy as np

from .. import helpers, rosys
from ..event import Event
from .bms_message import BmsMessage
from .bms_state import BmsState
from .expander import ExpanderHardware
from .module import Module, ModuleHardware, ModuleSimulation
from .robot_brain import RobotBrain


class Bms(Module, abc.ABC):
    """The BMS module is a simple example for a representation of real or simulated robot hardware.

    The BMS module provides measured voltages as an event.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.state = BmsState()

        self.VOLTAGE_MEASURED = Event()
        """new voltage measurements are available for processing (argument: list of voltages)"""


class BmsHardware(Bms, ModuleHardware):
    UPDATE_INTERVAL = 5.0

    def __init__(self, robot_brain: RobotBrain, *,
                 expander: Optional[ExpanderHardware] = None,
                 name: str = 'bms',
                 rx_pin: int = 26,
                 tx_pin: int = 27,
                 baud: int = 9600,
                 num: int = 2) -> None:
        self.name = name
        self.expander = expander
        lizard_code = f'''
            {name} = {self.expander.name + "." if self.expander else ""}Serial({rx_pin}, {tx_pin}, {baud}, {num})
            {name}.unmute()
        '''
        super().__init__(robot_brain=robot_brain, lizard_code=lizard_code)
        rosys.on_repeat(self._request, 1.0)
        self.message_hooks[f'{self.expander.name + ": " if self.expander else ""}{self.name}'] = self._handle_bms

    async def _request(self) -> None:
        if rosys.time() > self.state.last_update + self.UPDATE_INTERVAL:
            await self.robot_brain.send(f'{self.name}.send(0xdd, 0xa5, 0x03, 0x00, 0xff, 0xfd, 0x77)')

    def _handle_bms(self, line: str) -> None:
        if self.expander:
            words = line.split()[2:]
        else:
            words = line.split()[1:]
        msg = BmsMessage([int(w, 16) for w in words])
        msg.check()
        result = msg.interpret()
        self.state.percentage = result.get('capacity percent')
        self.state.voltage = result.get('total voltage')
        self.state.current = result.get('current')
        self.state.temperature = np.mean(result['temperatures']) if 'temperatures' in result else None
        self.state.is_charging = (self.state.current or 0) > -0.4
        self.state.last_update = rosys.time()


class BmsSimulation(Bms, ModuleSimulation):
    AVERAGE_VOLTAGE = 25.0
    VOLTAGE_AMPLITUDE = 1.0
    VOLTAGE_FREQUENCY = 0.01
    MIN_VOLTAGE = 22.5
    MAX_VOLTAGE = 27.5
    CHARGING_CURRENT = 1.0
    DISCHARGING_CURRENT = -0.7
    AVERAGE_TEMPERATURE = 20.0
    TEMPERATURE_AMPLITUDE = 1.0
    TEMPERATURE_FREQUENCY = 0.01

    def __init__(self, is_charging: Optional[Callable[[], bool]] = None, fixed_voltage: Optional[float] = None) -> None:
        super().__init__()
        self.is_charging = is_charging
        self.fixed_voltage = fixed_voltage

    def step(self, dt: float) -> None:
        self.state.is_charging = self.is_charging is not None and self.is_charging()
        self.state.voltage = \
            self.AVERAGE_VOLTAGE + self.VOLTAGE_AMPLITUDE * np.sin(self.VOLTAGE_FREQUENCY * rosys.time()) \
            if self.fixed_voltage is None else self.fixed_voltage
        self.state.percentage = helpers.ramp(self.state.voltage, self.MIN_VOLTAGE, self.MAX_VOLTAGE, 0.0, 100.0)
        self.state.current = self.CHARGING_CURRENT if self.state.is_charging else self.DISCHARGING_CURRENT
        self.state.temperature = self.AVERAGE_TEMPERATURE + \
            self.TEMPERATURE_AMPLITUDE * np.sin(self.TEMPERATURE_FREQUENCY * rosys.time())
        self.state.last_update = rosys.time()
