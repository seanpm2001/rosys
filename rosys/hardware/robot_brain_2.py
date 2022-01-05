from ..world import Velocity
from .hardware import Hardware


class RobotBrain2(Hardware):

    async def configure(self):
        await super().configure()
        filepath = 'lizard.txt'
        with open(filepath) as f:
            expander = False
            await self.send(f'!-')
            for line in f.read().splitlines():
                if line == '---':
                    expander = True
                    await self.send('!>!-')
                else:
                    if expander:
                        await self.send(f'!>!+{line}')
                    else:
                        await self.send(f'!+{line}')
            if expander:
                await self.send(f'!>!.')
                await self.send(f'!>core.restart()')
            await self.send(f'!.')
            await self.restart()

    async def restart(self):
        await super().restart()
        await self.send(f'core.restart()')

    async def drive(self, linear: float, angular: float):
        super().drive(linear, angular)
        await self.send(f'wheels.speed({linear}, {angular})')

    async def stop(self):
        await super().stop()
        await self.send('wheels.off()')

    async def update(self):
        await super().update()
        millis = None
        while True:
            line = self.check(await self.communication.read())
            if line is None:
                break
            words = line.split()
            if not words:
                continue
            first = words.pop(0)
            if first not in ['core', '!"core']:
                continue
            millis = float(words.pop(0))
            if self.world.robot.clock_offset is None:
                continue
            self.world.robot.hardware_time = millis / 1000 + self.world.robot.clock_offset
            self.parse(words)
        if millis is not None:
            self.world.robot.clock_offset = self.world.time - millis / 1000

    def parse(self, words: list[str]):
        self.world.robot.odometry.append(Velocity(
            linear=float(words.pop(0)),
            angular=float(words.pop(0)),
            time=self.world.robot.hardware_time,
        ))

    async def send(self, msg: str):
        await self.communication.send_async(self.augment(msg))

    def augment(self, line: str) -> str:
        checksum = 0
        for c in line:
            checksum ^= ord(c)
        return f'{line}@{checksum:02x}'

    def check(self, line: str) -> str:
        if line[-3:-2] == '@':
            check = int(line[-2:], 16)
            line = line[:-3]
            checksum = 0
            for c in line:
                checksum ^= ord(c)
            if checksum != check:
                return None
        return line
