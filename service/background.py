"""Module for handling asynchronous background tasks"""
import asyncio
from asyncio.subprocess import PIPE, Process
from abc import ABC, abstractmethod
from queue import Queue

from .responses import RequestResponse, ErrorResponse


class BackgroundTask(ABC):
    """Tasks started asynchronously in the background, notifying the
     requester"""

    def __init__(self, period=1):
        self._period = period
        self._task = None
        self._periodical_task = None

    @abstractmethod
    async def background(self, *args, **kwargs):
        """Method defining what and how it runs in the background"""
        pass

    async def run(self, *args, **kwargs):
        """Strarts the task"""
        self._task = await self.background(*args, **kwargs)
        self._periodical_task = asyncio.ensure_future(self.send_periodically())
        asyncio.ensure_future(self.wait())
        return self._send_notification()

    async def send_periodically(self):
        """Sending the progress periodically"""
        while True:
            await asyncio.sleep(self._period)
            await self._send_periodically()

    @abstractmethod
    async def _send_periodically(self):
        pass

    async def send_notification(self):
        """Sending the first notification"""
        return await self._send_notification()

    @abstractmethod
    def _send_notification(self):
        pass

    @abstractmethod
    async def wait(self):
        """Method to call to wait until the task has finished"""
        pass


class BackgroundSubProcess(BackgroundTask):
    """Subprocesses asynchronously in the background, notifying the requester
    """
    cmd = ""
    cwd = None
    period = 1

    def __init__(self, request_id, websocket, *args, **kwargs):
        self.request_id = request_id
        self.proc: Process = None
        self.stdout_queue = Queue()
        self.stderr_queue = Queue()
        self.websocket = websocket
        super().__init__(*args, **kwargs)

    def _prepare_cmd(self, *args, cwd=None, **kwargs):
        """Prepares the command. Override if this should work without
         websockets"""
        if cwd is not None:
            self.cwd = cwd
        return self._parse_args(*args, **kwargs)

    @abstractmethod
    def _parse_args(self, *args, **kwargs):
        """How to parse arguments"""
        pass

    async def background(self, *args, **kwargs):
        self._prepare_cmd(*args, **kwargs)
        # Create the subprocess, redirect the standard output into a pipe
        self.proc = await asyncio.create_subprocess_exec(
            *self.cmd, cwd=self.cwd, stdout=PIPE, stderr=PIPE)
        asyncio.ensure_future(self._read())
        asyncio.ensure_future(self._read_stderr())
        return self.proc

    async def _read(self):
        """Reads subprocess data"""
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                break
            self.stdout_queue.put(line)

    async def _read_stderr(self):
        """Reads subprocess data"""
        while True:
            line = await self.proc.stderr.readline()
            if not line:
                break
            self.stderr_queue.put(line)

    async def _send_periodically(self):
        while not self.stdout_queue.empty():
            line = self.stdout_queue.get()
            response = RequestResponse(
                self.request_id, line.decode('utf-8'), complete=False)
            await self.websocket.send(str(response))

    def _send_notification(self):
        return "Subprocess %d started" % self.proc.pid

    async def wait(self):
        """Waits until the background process finishes

        :return: returncode of the background process
        """
        return_code = await self.proc.wait()
        return await self._send_result(return_code)

    async def _send_result(self, return_code):
        if return_code != 0:
            response = ErrorResponse(500, self.request_id, return_code,
                                     'execution failed',
                                     data={'return_code': return_code,
                                           'message': str(self.stderr_queue.get())})
        else:
            result_messages = []
            while not self.stdout_queue.empty():
                line = str(self.stdout_queue.get())
                result_messages.append(line)
            response = RequestResponse(self.request_id, {
                'return_code': 0,
                'messages': result_messages})
        return await self.websocket.send(str(response))
