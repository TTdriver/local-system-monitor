"""One credential-free GitHub Contents API version check; no GUI work in the worker."""
import base64
import binascii
import json
import queue
import re
import threading
import urllib.request

TIMEOUT_SECONDS = 5

def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', value.strip(), flags=re.ASCII):
        raise ValueError('Expected major.minor.patch')
    return tuple(int(part) for part in value.strip().split('.'))

def available_update(installed, api_url, user_agent, opener=urllib.request.urlopen):
    try:
        current = version_tuple(installed)
        request = urllib.request.Request(api_url, headers={'User-Agent': user_agent + '/' + installed,
            'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'})
        with opener(request, timeout=TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read(16385).decode('utf-8'))
        if payload.get('encoding') != 'base64' or not isinstance(payload.get('content'), str):
            return None
        encoded = ''.join(payload['content'].split())
        remote = base64.b64decode(encoded, validate=True).decode('ascii').strip()
        if len(remote) > 128:
            return None
        return remote if version_tuple(remote) > current else None
    except (OSError, ValueError, KeyError, TypeError, AttributeError, binascii.Error):
        return None

class UpdateCheck:
    def __init__(self, installed, api_url, user_agent, check=available_update):
        self.results = queue.Queue(maxsize=1)
        self._started = False
        self._installed, self._url, self._agent, self._check = installed, api_url, user_agent, check

    def start(self):
        if self._started:
            return
        self._started = True
        threading.Thread(target=self._run, name='launch-update-check', daemon=True).start()

    def _run(self):
        # Always send a completion result, even on failure, so GUI queue polling stops.
        try:
            result = self._check(self._installed, self._url, self._agent)
        except Exception:
            result = None
        self.results.put(result)
