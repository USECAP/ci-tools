"""Module for asynchronous RPC requests"""
import asyncio

from jsonrpcserver.async_dispatcher import AsyncRequests as AsyncRequests_
from jsonrpcserver.async_request import AsyncRequest as AsyncRequest_
from jsonrpcserver.request_utils import (validate_arguments_against_signature,
                                         get_method)
from jsonrpcserver.response import NotificationResponse, BatchResponse
from jsonrpcserver import config

from .responses import Response, RequestResponse
from .background import BackgroundTask


class AsyncRequest(AsyncRequest_):
    """
    Represents an asynchronous JSON-RPC Request object based on websockets

    Encapsulates a JSON-RPC request, providing details such as the method name,
    arguments, and whether it's a request or a notification, and provides a
    ``process`` method to execute the request.
    In comparison to the Request from the jsonsonrpcserver Request, this
    Request is asynchronous and allows to send requests to the client
    """
    def __init__(self, request, websocket, context=None):
        self.websocket = websocket
        self.futures = []
        super().__init__(request, context)

    async def call(self, methods):
        # Validation or parsing may have failed in __init__, in which case
        # there's no point calling. It would've already set the response.
        if not self.response:
            # Handles setting the result/exception of the call
            with self.handle_exceptions():
                class_ = self.get_method(methods)
                if issubclass(class_, BackgroundTask):
                    period = self.kwargs.pop('period') if 'period' in self.kwargs else 1
                    obj = class_(self.request_id, self.websocket,
                                 period=period)
                    result = await obj.run(
                        *(self.args or []),
                        **self.kwargs
                    )
                    fut = asyncio.ensure_future(obj.wait())
                    self.futures.append(fut)
                else:
                    # Get the method object from a list (raises MethodNotFound)
                    foreground, background = self.get_methods(methods)
                    # Ensure the arguments match the method's signature
                    validate_arguments_against_signature(
                        foreground, self.args, self.kwargs)
                    validate_arguments_against_signature(
                        background, self.args, self.kwargs)
                    asyncio.ensure_future(self.async_response(background))
                    result = await foreground(
                        *(self.args or []), **(self.kwargs or {}))
                # Set the response
                if self.is_notification:
                    self.response = NotificationResponse()
                else:
                    self.response = RequestResponse(self.request_id, result,
                                                    complete=False)
        # Ensure the response has been set before returning it
        assert isinstance(self.response, Response), 'Invalid response type'
        return self.response

    async def async_response(self, proc):
        """Respond asynchronously

        :param proc: procedure called
        :return: The response
        """
        result = await proc(*(self.args or []), **(self.kwargs or {}))
        response = RequestResponse(self.request_id, result)
        await self.websocket.send(str(response))
        return response

    def get_methods(self, methods):
        """
        Find and return a callable representing the method for this request.

        :param methods: List or dictionary of named functions
        :raises MethodNotFound: If no method is found
        :returns: Callable representing the method
        """
        return (
            get_method(methods, self.method_name),
            get_method(methods, self.method_name + "_background")
        )

    async def wait(self):
        """Waits until all started tasks are finished"""
        return await asyncio.wait(self.futures)


class AsyncRequests(AsyncRequests_):
    """A collection of Asynchronous request objects."""
    def __init__(self, requests, websocket, request_type=AsyncRequest):
        self.websocket = websocket
        self.futures = []
        super(AsyncRequests, self).__init__(requests, request_type=request_type)

    async def dispatch(self, methods, context=None):
        """
        Process a JSON-RPC request.

        Calls the requested method(s), and returns the result.

        :param methods: Collection of methods to dispatch to. Can be a ``list``
            of functions, a ``dict`` of name:method pairs, or a ``Methods``
            object.
        :param context: Optional context object which will be passed through to
            the RPC methods.
        """
        # Init may have failed to parse the request, in which case the response
        # would already be set
        if not self.response:
            # Batch request
            if isinstance(self.requests, list):
                # First convert each to a Request object
                requests = [
                    self.request_type(r, context=context) for r in self.requests
                ]
                # Call each request
                response = await asyncio.gather(
                    *[r.call(methods) for r in requests]
                )
                for request in self.requests:
                    self.futures.extend(request.futures)
                # Remove notification responses (as per spec)
                response = [r for r in response if not r.is_notification]
                # If the response list is empty, return nothing
                self.response = BatchResponse(response) if response else NotificationResponse()
            # Single request
            else:
                # Convert to a Request object
                request = self.request_type(self.requests, self.websocket,
                                            context=context)
                # Call the request
                self.response = await request.call(methods)
                self.futures.extend(request.futures)
        assert self.response, 'Response must be set'
        assert self.response.http_status, 'Must have http_status set'
        if config.log_responses:
            self.log_response(self.response)
        return self.response

    async def wait(self):
        """Waits until all started tasks are finished"""
        return await asyncio.wait(self.futures)
