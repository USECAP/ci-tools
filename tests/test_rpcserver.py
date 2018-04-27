"""Tests to test the rpc server and client"""
import asyncio
import asyncio.subprocess
import functools
import time


import websockets
from jsonrpcserver import methods
from jsonrpcclient.exceptions import ReceivedErrorResponse
from jsonrpcclient.request import Request

from service import AsyncRequests, WebSocketsClient, BackgroundSubProcess
from service.methods import method_instance
from service import server


WAITING_MSG = "waiting"
HOST = "localhost"
PORT = 5001

TEST_MESSAGE = "test_msg"
SUBPROCESS_STARTED_REGEX = r"Subprocess [0-9]* started"


async def handle_client(stop, port=PORT):
    """Handle for the RPC client"""
    async with websockets.connect('ws://%s:%d' % (HOST, port)) as websocket:
        client = WebSocketsClient(websocket)
        request = Request('ping', duration=3, period=1, message=TEST_MESSAGE)
        response = await client.send(request)
        print('Waiting for event with the id %d' % response['id'])
        await client.wait()
        stop.set_result(None)


async def handle_server(websocket, path):  # pylint: disable=unused-argument
    """Handle for the RPC server"""

    @methods.add
    async def ping_background():  # pylint: disable=unused-variable
        """Function which runs in the background if ping is requested"""
        time.sleep(10)
        print("this happened in the background")
        return 'pong'

    @methods.add
    async def ping():  # pylint: disable=unused-variable
        """Function which returns immediately telling that the background job
        is running"""
        return WAITING_MSG

    request = await websocket.recv()
    request = AsyncRequests(request, websocket)
    response = await request.dispatch(methods)
    assert response['result'] == WAITING_MSG
    assert response['complete'] is False
    if not response.is_notification:
        await websocket.send(str(response))


async def handle_server_obj(websocket, path, stop):  # pylint: disable=unused-argument
    """Handle for the RPC server"""

    class BackgroundSleep(BackgroundSubProcess):
        """Simply runs a shellscript with a loop of sleeps"""
        cmd = ["./scripts/sleep_loop.sh"]
        cwd = "tests"

        def _parse_args(self, *args, duration, message):  # pylint: disable=arguments-differ
            self.cmd = self.cmd + [str(duration), message]

    method_instance.add(BackgroundSleep, name='ping')

    request = await websocket.recv()
    request = AsyncRequests(request, websocket)
    response = await request.dispatch(method_instance)
    if not response.is_notification:
        await websocket.send(str(response))
    await request.wait()

    await stop
    await websocket.close()


def test_background_rpc():
    """Tests to make a simple server/client connection"""
    loop = asyncio.get_event_loop()
    stop = asyncio.Future()
    port = PORT
    server_handler = functools.partial(handle_server_obj, stop=stop)
    start_server = websockets.serve(server_handler, HOST, port)
    loop.run_until_complete(start_server)
    loop.run_until_complete(handle_client(stop, port))


def test_server():
    """Testing the server executable"""
    asyncio.get_event_loop().run_until_complete(server.handler())


async def handle_client_ci_build(stop, port):
    """Handle for the RPC client"""
    async with websockets.connect('ws://%s:%d' % (HOST, port)) as websocket:
        client = WebSocketsClient(websocket)
        request = Request('ci_build', build_command="make",
                          project_path="tests",
                          period=1)
        response = await client.send(request)
        print('Waiting for event with the id %d' % response['id'])
        try:
            await client.wait()
        except ReceivedErrorResponse as exception:
            print(exception.message)
        request = Request('ci_vulnscan', project_path="tests", period=1)
        response = await client.send(request)
        print('Waiting for event with the id %d' % response['id'])
        try:
            await client.wait()
        except ReceivedErrorResponse as exception:
            print(exception.message)
        stop.set_result(None)


def test_rpc_server():
    """Tests the rpc server binary"""
    port = PORT + 1
    loop = asyncio.get_event_loop()
    proc = loop.run_until_complete(
        asyncio.create_subprocess_exec(*['ci-server', str(port)], stderr=None,
                                       stdout=None))
    loop.run_until_complete(asyncio.sleep(1))
    stop = asyncio.Future()
    loop.run_until_complete(handle_client_ci_build(stop, port))
    loop.run_until_complete(stop)
    proc.kill()


if __name__ == '__main__':
    test_rpc_server()
