import json
import os
from urllib.parse import urlparse, urlsplit

from tabsdata.api.tabsdata_server import TabsdataServer


def resolve_login_credentials():
    try:
        json_path = os.path.expanduser("~/.tabsdata/connection.json")
        url = json.load(open(json_path))["url"] if os.path.exists(json_path) else None
        port = urlparse(url).port
        base = urlsplit(url)
        host = f"{base.scheme}://{base.netloc}"
        return {"url": host, "port": port}
    except:
        return {"url": "127.0.0.1:2457", "port": "2457"}


res = resolve_login_credentials()
url = res["url"]
x = TabsdataServer(url, "admin", "tabsdata", "sys_admin")

f = x.get_function("airport", "flight_pub")
print(f)

snippet = f.kwargs.get("snippet")
print(snippet)
