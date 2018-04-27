"""A byte stream wrapper that yields decoded lines and lets you put back lines
to the stream.
"""
from io import BytesIO
from collections import deque

class LineStream(BytesIO):
    """Wraps a byte stream and turns it to a string stream with functionality
    to put lines back to the stream.
    """
    def __init__(self, *args, buffer_size=8, encoding="latin_1", **kwargs):
        """Initialization.

        :param buffer_size: maximum of lines that can be put back.
        :param encoding: encoding that is used to decode the individual lines.
        """
        super().__init__(*args, **kwargs)
        if buffer_size < 8:
            buffer_size = 8
        self._buffer = deque(maxlen=buffer_size)

        self.encoding = encoding

    def __next__(self):
        """Returns the next line in the stream."""
        next_line = super().__next__()
        self._buffer.append(len(next_line))
        return next_line.decode(self.encoding)

    def putback_line(self, count=1):
        """Puts back count lines back into the stream."""
        run_back = 0
        for _ in range(0, count):
            run_back += self._buffer.pop()

        self.seek(-run_back, 1)

    def readline(self, size=-1):
        """Returns the next line in the stream."""
        next_line = super().readline(size)
        self._buffer.append(len(next_line))
        return next_line.decode(self.encoding)
