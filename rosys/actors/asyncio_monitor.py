from dataclasses import dataclass
import re
import shutil
import os
import html
import rosys
from .actor import Actor
from collections import defaultdict


@dataclass
class Measurement:
    time: str
    millis: int
    name: str
    details: str


color_pattern = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]')
warning_pattern = re.compile(r"(.*) \[WARNING\].*Executing(.*)took (.*) seconds")
task_pattern = re.compile(r".*name=['\"](.*)['\"] coro=<(.*)> .*")


class AsyncioMonitor(Actor):
    interval: float = 10

    def __init__(self) -> None:
        super().__init__()
        self.timings: dict[str, list[Measurement]] = defaultdict(list)
        self.log_position = None

    async def step(self):
        await super().step()
        logfile = os.path.expanduser('~/.rosys/debug.log')
        if not os.path.isfile(logfile):
            self.log.warning('could not find debug.log')
            return
        self.parse_log(logfile)

    def parse_log(self, log):
        if self.log_position is None:  # NOTE only messgages generated after startup should be analyzed
            self.log_position = os.path.getsize(log)
        if os.path.getsize(log) < self.log_position:  # NOTE detect beginning of new log file
            self.log_position = 0
        with open(log, 'r') as f:
            f.seek(self.log_position)
            warnings = list(filter(lambda line: 'asyncio/base_events.py' in line, f))
            for warning in warnings:
                message = AsyncioMonitor.parse_async_warning(warning)
                if message:
                    self.timings[message.name].append(message)
            self.log_position = f.tell()

    @staticmethod
    def parse_async_warning(msg: str):
        if 'rosys/actors/asyncio_monitor.py' in msg:
            return  # NOTE we ignore our own messages
        warning = color_pattern.sub('', msg)
        match_warning = warning_pattern.match(warning)
        if match_warning is None:
            return
        time = match_warning.group(1)
        millis = int(float(match_warning.group(3))*1000)
        description = match_warning.group(2)
        if 'TimerHandle' in description:
            name = 'TimerHandle'
            details = description
        else:
            match_task = task_pattern.match(description)
            if match_task is None:
                self.log.warning(f'could not parse task "{warning}"')
                return
            name = match_task.group(1)
            details = match_task.group(2)
        return Measurement(time=time, name=name, millis=millis, details=details)
