"""Module for running the JSON-RPC server"""
import asyncio
import logging
import sys

import websockets
from websockets.exceptions import ConnectionClosed

from settings import WS_HOST, WS_PORT

from .background import BackgroundSubProcess
from .methods import method_instance
from .requests import AsyncRequests


# Internal logger
LOGGER = logging.getLogger(name=__name__)


async def handle_server(websocket, path):  # pylint: disable=unused-argument
    """Handle for the RPC server"""

    class CIBuild(BackgroundSubProcess):
        """Executed ci-build with a custom build command"""
        cmd = ["ci-build"]

        def _parse_args(self, *args, # pylint: disable=arguments-differ
                        build_command: str = None,
                        project_path: str = None):
            if not build_command:
                raise Exception("No build command given")
            if not project_path:
                raise Exception("No project path given")
            args = ['--project-path', project_path, build_command]
            self.cmd = self.cmd + args
    method_instance.add(CIBuild, name="ci_build")

    class CIVulnScan(BackgroundSubProcess):
        """Executed ci-build with a custom build command"""
        cmd = ["ci-vulnscan"]

        def _parse_args(self, *args, # pylint: disable=arguments-differ
                        project_path: str = None):
            if not project_path:
                raise Exception("No project path given")
            args = ['--project-path', project_path]
            self.cmd = self.cmd + args
    method_instance.add(CIVulnScan, name="ci_vulnscan")

    while True:
        try:
            request = await websocket.recv()
            request = AsyncRequests(request, websocket)
            response = await request.dispatch(method_instance)
            if not response.is_notification:
                await websocket.send(str(response))
        except ConnectionClosed as exception:
            print("Client connection closed %s" % exception.reason)
            break


async def handler(stop=None, port=WS_PORT):
    """Starts the server and waits if necessary"""
    server = websockets.serve(handle_server, WS_HOST, port)
    await server
    LOGGER.warning("Server started on %s:%s", WS_HOST, port)

    if stop:
        await stop


def main():
    """The main function starting the server and running forever"""
    try:
        port = int(sys.argv[1])
    except IndexError:
        port = WS_PORT

    loop = asyncio.get_event_loop()
    loop.run_until_complete(handler(port=port))
    loop.run_forever()


if __name__ == "__main__":
    main()
