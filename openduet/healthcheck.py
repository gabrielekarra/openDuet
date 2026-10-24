"""Small loopback HTTP probe for containers, independent of outbound proxies."""

from __future__ import annotations

import socket
import sys


def healthy(port: int, timeout: float = 3.0) -> bool:
    if not 1 <= port <= 65535:
        return False
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout) as connection:
            connection.sendall(b"GET /health HTTP/1.0\r\nHost: localhost\r\n\r\n")
            with connection.makefile("rb") as response:
                status = response.readline(4096).split()
                return (
                    len(status) >= 2
                    and status[0] in {b"HTTP/1.0", b"HTTP/1.1"}
                    and status[1] == b"200"
                )
    except (OSError, ValueError):
        return False


if __name__ == "__main__":
    try:
        port = int(sys.argv[1])
    except (IndexError, ValueError):
        sys.exit(1)
    sys.exit(0 if healthy(port) else 1)
