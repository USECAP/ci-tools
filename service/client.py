"""Code for the RPC client (usually needed for testing)
"""
import json

from jsonrpcclient.websockets_client import WebSocketsClient as Client
from jsonrpcclient import exceptions, config


class WebSocketsClient(Client):
    """WebSocket client based on the client from jsonrpcclient
    """

    def __init__(self, *args, **kwargs):
        self.waiting_for = {}
        self.responses = []
        super().__init__(*args, **kwargs)

    async def wait(self):
        """Waits for the uncompleted responses
        """
        while True:
            message = await self.socket.recv()
            response = self._process_response(message)
            self.responses.append(response)
            if not self.waiting_for:
                break
        return

    def _process_response(self, response, log_extra=None, log_format=None):
        """
        Process the response and return the 'result' portion if present.

        :param response: The JSON-RPC response string to process.
        :return: The response string, or None
        """
        if response:
            # Log the response before processing it
            self._log_response(response, log_extra, log_format)
            # If it's a json string, parse to object
            if isinstance(response, str):
                try:
                    response = json.loads(response)
                except ValueError:
                    raise exceptions.ParseResponseError()
            # Validate the response against the Response schema (raises
            # jsonschema.ValidationError if invalid)
            if config.validate:
                self._validator.validate(response)
            if isinstance(response, list):
                # Batch request - just return the whole response
                return response
            else:
                # If the response was 'error', raise to ensure it's handled
                if 'error' in response and response['error'] is not None:
                    raise exceptions.ReceivedErrorResponse(
                        response['error'].get('code'),
                        response['error'].get('message'),
                        response['error'].get('data'))

                # if a non-completed response is set, wait for it
                if not response['complete']:
                    self.waiting_for[response['id']] = 1
                elif response['id'] in self.waiting_for:
                    print("Response with id %d retrieved" % response['id'])
                    del self.waiting_for[response['id']]

                # All was successful, return just the result part
                return response
        # No response was given
        return None
