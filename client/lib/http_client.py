"""Tiny HTTP client for MicroPython (no urequests dependency required)."""

import socket
import json as _json


class HTTPError(Exception):
    def __init__(self, status: int, body: str = ""):
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body   = body


def _parse_response(sock) -> tuple[int, dict, bytes]:
    """Read HTTP/1.1 response from socket; return (status, headers, body)."""
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(256)
        if not chunk:
            break
        buf += chunk

    header_raw, _, rest = buf.partition(b"\r\n\r\n")
    lines = header_raw.decode().split("\r\n")
    status = int(lines[0].split()[1])
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            k, _, v = line.partition(":")
            headers[k.strip().lower()] = v.strip()

    # Read remaining body based on Content-Length.
    body = rest
    clen = int(headers.get("content-length", 0))
    while len(body) < clen:
        chunk = sock.recv(min(1024, clen - len(body)))
        if not chunk:
            break
        body += chunk

    return status, headers, body


class HTTPClient:
    def __init__(self, host: str, port: int = 80, timeout: int = 10):
        self.host    = host
        self.port    = port
        self.timeout = timeout

    def _request(self, method: str, path: str, body: bytes | None = None,
                 content_type: str = "application/json") -> bytes:
        addr = socket.getaddrinfo(self.host, self.port)[0][-1]
        s = socket.socket()
        s.settimeout(self.timeout)
        s.connect(addr)
        try:
            req = (
                f"{method} {path} HTTP/1.1\r\n"
                f"Host: {self.host}:{self.port}\r\n"
                f"Connection: close\r\n"
            )
            if body is not None:
                req += f"Content-Type: {content_type}\r\nContent-Length: {len(body)}\r\n"
            req += "\r\n"
            s.send(req.encode())
            if body:
                s.send(body)

            status, _headers, resp_body = _parse_response(s)
        finally:
            s.close()

        if status >= 400:
            raise HTTPError(status, resp_body.decode("utf-8", "replace"))
        return resp_body

    def get(self, path: str) -> bytes:
        return self._request("GET", path)

    def get_json(self, path: str):
        return _json.loads(self.get(path))

    def post_json(self, path: str, data: dict):
        body = _json.dumps(data).encode()
        resp = self._request("POST", path, body=body)
        return _json.loads(resp)

    def patch_json(self, path: str, data: dict):
        body = _json.dumps(data).encode()
        resp = self._request("PATCH", path, body=body)
        return _json.loads(resp)

    def delete(self, path: str) -> int:
        self._request("DELETE", path)
        return 204
