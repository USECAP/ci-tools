"""Module for asynchronous RPC responses"""
import json
from collections import OrderedDict

from jsonrpcserver.response import Response
from jsonrpcserver import status


def sort_response(response):
    """
    Sort the keys in a JSON-RPC response object.

    This has no effect other than making it nicer to read.

    Example::

        >>> json.dumps(sort_response({'id': 2, 'result': 5, 'jsonrpc': '2.0'}))
        {"jsonrpc": "2.0", "result": 5, "id": 1}

    :param response: JSON-RPC response, in dictionary form.
    :return: The same response, sorted in an ``OrderedDict``.
    """
    root_order = ['jsonrpc', 'result', 'error', 'id', 'complete']
    error_order = ['code', 'message', 'data']
    req = OrderedDict(sorted(
        response.items(), key=lambda k: root_order.index(k[0])))
    if 'error' in response:
        req['error'] = OrderedDict(sorted(
            response['error'].items(), key=lambda k: error_order.index(k[0])))
    return req


class RequestResponse(Response, dict):
    """
    Response returned from a Request.

    Returned from processing a successful request with an ``id`` member,
    (indicating that a payload is expected back).
    """
    #: The recommended HTTP status code.
    http_status = status.HTTP_OK

    def __init__(self, request_id, result, complete=True):
        """
        :param request_id:
            Matches the original request's id value.
        :param result:
            The payload from processing the request. If the request was a
            JSON-RPC notification (i.e. the request id is ``None``), the result
            must also be ``None`` because notifications don't require any data
            returned.
        """
        # Ensure we're not responding to a notification with data
        if request_id is None:
            raise ValueError(
                'Requests must have an id, use NotificationResponse instead')
        super(RequestResponse, self).__init__(
            {'jsonrpc': '2.0', 'result': result, 'id': request_id,
             'complete': complete})

    def __str__(self):
        """JSON-RPC response string."""
        return json.dumps(sort_response(self))


class ErrorResponse(Response, dict):
    """
    Error response.

    Returned if there was an error while processing the request.
    """
    def __init__(self, http_status,  # pylint: disable=too-many-arguments
                 request_id, code, message, data=None):
        """
        :param http_status:
            The recommended HTTP status code.
        :param request_id:
            Must be the same as the value as the id member in the Request
            Object. If there was an error in detecting the id in the Request
            object (e.g. Parse error/Invalid Request), it MUST be Null.
        :param code:
            A Number that indicates the error type that occurred. This MUST be
            an integer.
        :param message:
            A string providing a short description of the error, eg.  "Invalid
            params"
        :param data:
            A Primitive or Structured value that contains additional information
            about the error. This may be omitted.
        """
        super(ErrorResponse, self).__init__(
            {'jsonrpc': '2.0', 'error': {'code': code, 'message': message},
             'id': request_id, 'complete': True})
        #: Holds extra information about the error.
        if data:
            self['error']['data'] = data
        #: The recommended HTTP status code. (the status code depends on the
        #: error)
        self.http_status = http_status

    def __str__(self):
        """JSON-RPC response string."""
        return json.dumps(sort_response(self))
