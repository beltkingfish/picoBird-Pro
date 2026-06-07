"""
Minimal raw-socket HTTP client for MicroPython (no urequests dependency).
"""
import socket
import json as _json


def get(host, port, path, timeout=8):
    """GET http://host:port/path — returns parsed JSON dict or None."""
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(addr)
        request = "GET {} HTTP/1.0\r\nHost: {}:{}\r\nConnection: close\r\n\r\n".format(
            path, host, port)
        s.send(request.encode())
        raw = b""
        while True:
            chunk = s.recv(512)
            if not chunk:
                break
            raw += chunk
    finally:
        s.close()

    # Strip HTTP headers
    sep = raw.find(b"\r\n\r\n")
    if sep == -1:
        return None
    body = raw[sep + 4:].decode()
    try:
        return _json.loads(body)
    except Exception:
        return None


def post(host, port, path, data, timeout=8):
    """POST JSON data — returns parsed JSON dict or None."""
    body = _json.dumps(data).encode()
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(addr)
        headers = (
            "POST {} HTTP/1.0\r\n"
            "Host: {}:{}\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: {}\r\n"
            "Connection: close\r\n\r\n"
        ).format(path, host, port, len(body))
        s.send(headers.encode() + body)
        raw = b""
        while True:
            chunk = s.recv(512)
            if not chunk:
                break
            raw += chunk
    finally:
        s.close()

    sep = raw.find(b"\r\n\r\n")
    if sep == -1:
        return None
    try:
        return _json.loads(raw[sep + 4:].decode())
    except Exception:
        return None
