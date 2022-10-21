import os
from typing import Optional

import rosys
from nicegui import ui
from rosys.event import Event

from .communication import Communication, SerialCommunication


class RobotBrain:
    '''This module manages the communication with a [Zauberzeug Robot Brain](https://zauberzeug.com/robot-brain.html).

    It expects a communication object, which is used for the actual read and write operations.
    Besides providing some basic methods like configuring or restarting the microcontroller, it augments and verifies checksums for each message.
    '''

    def __init__(self, communication: Communication) -> None:
        self.LINE_RECEIVED = Event()
        '''a line has been received from the microcontroller (argument: line as string)'''

        self.communication = communication
        self.waiting_list: dict[str, Optional[str]] = {}

        self.clock_offset: Optional[float] = None
        self.hardware_time: Optional[float] = None
        self.flash_params = []

    async def configure(self, filepath: str = 'lizard.txt') -> None:
        await self.send(f'!-')
        with open(filepath) as f:
            for line in f.read().splitlines():
                await self.send(f'!+{line}')
        await self.send(f'!.')
        await self.restart()

    async def restart(self) -> None:
        await self.send(f'core.restart()')

    async def read_lines(self) -> list[tuple[float, str]]:
        lines: list[tuple[float, str]] = []
        millis = None
        while True:
            unchecked = await self.communication.read()
            line = check(unchecked)
            if not line:
                break
            words = line.split()
            if not words:
                continue
            first = words.pop(0)
            if first in self.waiting_list:
                self.waiting_list[first] = line
            if first == 'core':
                millis = float(words.pop(0))
                if self.clock_offset is None:
                    continue
                self.hardware_time = millis / 1000 + self.clock_offset
            self.LINE_RECEIVED.emit(line)
            lines.append((self.hardware_time, line))
        if millis is not None:
            self.clock_offset = rosys.time() - millis / 1000
        return lines

    async def send(self, msg: str) -> None:
        await self.communication.send(augment(msg))

    async def send_and_await(self, msg: str, ack: str, *, timeout: float = float('inf')) -> Optional[str]:
        self.waiting_list[ack] = None
        await self.send(msg)
        t0 = rosys.time()
        while self.waiting_list.get(ack) is None and rosys.time() < t0 + timeout:
            await rosys.sleep(0.1)
        return self.waiting_list.pop(ack) if ack in self.waiting_list else None

    async def flash(self) -> None:
        assert isinstance(self.communication, SerialCommunication)
        with ui.dialog() as dialog, ui.card():
            status = ui.markdown('.... flashing ....')
        dialog.open()
        dialog.page.update()
        self.communication.disconnect()
        output = await rosys.run.sh(['./flash.py'] + self.flash_params, timeout=60, working_dir=os.path.expanduser('~/.lizard'))
        status.set_content(f'```\n{output}\n```')
        self.communication.connect()

    def developer_ui(self) -> None:
        ui.label('Lizard')
        ui.button('Configure', on_click=self.configure).props('outline')
        ui.button('Restart', on_click=self.restart).props('outline')
        ui.button('Flash', on_click=self.flash).props('outline')


def augment(line: str) -> str:
    checksum = 0
    for c in line:
        checksum ^= ord(c)
    return f'{line}@{checksum:02x}'


def check(line: Optional[str]) -> str:
    if line is None:
        return ""
    if line[-3:-2] == '@':
        check = int(line[-2:], 16)
        line = line[:-3]
        checksum = 0
        for c in line:
            checksum ^= ord(c)
        if checksum != check:
            return None
    return line
