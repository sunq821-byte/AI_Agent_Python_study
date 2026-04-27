import http.client, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from practice05.skill_client import load_env

env = load_env()
print("BASE_URL:", env.get('BASE_URL'))
print("MODEL:", env.get('MODEL'))
print("TOKEN:", env.get('TOKEN', '')[:20] + "...")

from urllib.parse import urlparse
url = env.get('BASE_URL')
parsed = urlparse(url)
print("scheme:", parsed.scheme)
print("host:", parsed.netloc)
print("path:", parsed.path)

conn = http.client.HTTPSConnection(parsed.netloc, timeout=30)
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {env.get('TOKEN')}"
}
body = json.dumps({
    "model": env.get('MODEL'),
    "messages": [{"role": "user", "content": "hi"}],
    "stream": False,
    "max_tokens": 10
})
conn.request("POST", parsed.path + "/chat/completions", body, headers)
r = conn.getresponse()
print("Status:", r.status)
print("Body:", r.read(500).decode())
conn.close()
