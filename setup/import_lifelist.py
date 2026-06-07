#!/usr/bin/env python3
"""Import an eBird life-list CSV export into picoBird Pro.

The eBird API cannot return your personal life list, so download it from the
eBird website first:

  1. Go to https://ebird.org/lifelist
  2. Choose the region/time you want (e.g. "World", "All years")
  3. Click "Download (CSV)" near the top right

Then run this on the Pi 5:

  python3 setup/import_lifelist.py ~/ebird_world_life_list.csv

It POSTs the file to the local picoBird API, which matches each species against
the synced taxonomy and adds any missing lifers.
"""

import sys
import urllib.request
import uuid
import os

API = os.environ.get("PICOBIRD_API", "http://127.0.0.1:5000")


def main():
    if len(sys.argv) != 2:
        print("usage: import_lifelist.py <ebird_life_list.csv>")
        return 1
    path = sys.argv[1]
    if not os.path.isfile(path):
        print("error: file not found:", path)
        return 1

    with open(path, "rb") as f:
        file_bytes = f.read()

    boundary = uuid.uuid4().hex
    body = (
        ("--%s\r\n" % boundary).encode()
        + b'Content-Disposition: form-data; name="file"; filename="lifelist.csv"\r\n'
        + b"Content-Type: text/csv\r\n\r\n"
        + file_bytes
        + ("\r\n--%s--\r\n" % boundary).encode()
    )

    req = urllib.request.Request(
        API + "/api/lifelist/import",
        data=body,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(r.read().decode())
    except Exception as exc:
        print("import failed:", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
