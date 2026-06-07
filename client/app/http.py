"""
Minimal raw-socket HTTP client for MicroPython (no urequests dependency).

Hardened for the Pico's limited RAM and flaky field WiFi:
- caps the response size so a runaway body can't exhaust the heap
- guards header / status-line parsing against malformed responses
- never lets a decode/parse error crash the UI (returns None instead)
- always closes the socket
"""
import socket
import json as _json

# Protect the Pico heap — refuse to buffer responses larger than this.
MAX_RESPONSE = 48 * 1024  # 48 KB

_SAFE = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~"


def as_list(data, key="results"):
    """Normalize an API response to a list.

    Some endpoints return a bare JSON array (observations) while others wrap
    rows in an object (search/lifelist: {"results": [...]}). This accepts
    either and always returns a list.
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        v = data.get(key)
        if isinstance(v, list):
            return v
    return []


def quote(s):
    """Percent-encode a string for safe use in a URL query value.

    MicroPython has no urllib.parse, so this is a minimal RFC-3986 encoder.
    """
    out = []
    for ch in s:
        if ch in _SAFE:
            out.append(ch)
        else:
            for b in ch.encode("utf-8"):
                out.append("%{:02X}".format(b))
    return "".join(out)


def _read_response(s):
    """Read a full HTTP response from socket *s*, return parsed JSON or None."""
    raw = b""
    while True:
        try:
            chunk = s.recv(512)
        except Exception:
            return None
        if not chunk:
            break
        raw += chunk
        if len(raw) > MAX_RESPONSE:
            # Body too large for the Pico — bail rather than OOM.
            return None

    # Split headers / body.
    sep = raw.find(b"\r\n\r\n")
    if sep == -1:
        return None

    # Check the status line (e.g. "HTTP/1.0 200 OK").
    head = raw[:sep]
    try:
        status_line = head.split(b"\r\n", 1)[0]
        parts = status_line.split()
        status = int(parts[1]) if len(parts) >= 2 else 0
    except Exception:
        return None
    if not (200 <= status < 300):
        return None

    body = raw[sep + 4:]
    try:
        text = body.decode()
    except Exception:
        # Malformed / non-UTF-8 body — don't crash the caller.
        return None
    try:
        return _json.loads(text)
    except Exception:
        return None


def get(host, port, path, timeout=8):
    """GET http://host:port/path — returns parsed JSON or None on any failure."""
    try:
        addr = socket.getaddrinfo(host, port)[0][-1]
    except Exception:
        return None
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(addr)
        request = "GET {} HTTP/1.0\r\nHost: {}:{}\r\nConnection: close\r\n\r\n".format(
            path, host, port)
        s.send(request.encode())
        return _read_response(s)
    except Exception:
        return None
    finally:
        try:
            s.close()
        except Exception:
            pass


def _send_body(host, port, path, data, method, timeout):
    """Shared JSON body sender for POST/PATCH — returns parsed JSON or None."""
    try:
        body = _json.dumps(data).encode()
        addr = socket.getaddrinfo(host, port)[0][-1]
    except Exception:
        return None
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect(addr)
        headers = (
            "{} {} HTTP/1.0\r\n"
            "Host: {}:{}\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: {}\r\n"
            "Connection: close\r\n\r\n"
        ).format(method, path, host, port, len(body))
        s.send(headers.encode() + body)
        return _read_response(s)
    except Exception:
        return None
    finally:
        try:
            s.close()
        except Exception:
            pass


def post(host, port, path, data, timeout=8):
    """POST JSON data — returns parsed JSON or None on any failure."""
    return _send_body(host, port, path, data, "POST", timeout)


def patch(host, port, path, data, timeout=8):
    """PATCH JSON data — returns parsed JSON or None on any failure."""
    return _send_body(host, port, path, data, "PATCH", timeout)
