import json
import time
import urllib.error
import urllib.request
import uuid


class ProtocolError(RuntimeError):
    pass


class HttpTransport:
    def __init__(self, base_url='http://127.0.0.1:2026', timeout=5.0):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def post(self, path, payload):
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        req = urllib.request.Request(self.base_url + path, data=data, headers={'Content-Type':'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise ProtocolError(f'{path} failed: {exc}') from exc


class SimulatorClient:
    def __init__(self, robot_id, transport=None, arena_id='default', retry_count=2):
        if not robot_id or any(ord(ch) < 32 for ch in robot_id):
            raise ValueError('robot_id must be a non-empty visible string')
        self.robot_id = robot_id
        self.arena_id = arena_id
        self.transport = transport or HttpTransport()
        self.retry_count = retry_count
        self.current_channel = 1
        self.sequence = 0
        self.virtual_time_s = 0.0

    def _base(self, kind):
        self.sequence += 1
        return {'arena_id':self.arena_id,'robot_id':self.robot_id,'request_id':f'{kind}-{self.sequence}-{uuid.uuid4().hex[:8]}'}

    def _send(self, path, payload):
        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                response = self.transport.post(path, payload)
                break
            except ProtocolError as exc:
                last_error = exc
                if attempt >= self.retry_count:
                    raise
                time.sleep(0.15 * (attempt + 1))
        else:
            raise last_error
        if response.get('accepted') is not True:
            raise ProtocolError(f'{path} rejected: {response}')
        self.virtual_time_s = response.get('virtual_time_s', self.virtual_time_s)
        return response

    def enter(self):
        return self._send('/enter', self._base('enter'))

    def measure(self, position, channel):
        payload = self._base('measure')
        payload.update({'position':{'x':float(position[0]),'y':float(position[1])},'channel':int(channel)})
        result = self._send('/measure', payload)
        self.current_channel = int(channel)
        return result

    def clear(self, position, channel):
        payload = self._base('clear')
        payload.update({'position':{'x':float(position[0]),'y':float(position[1])},'channel':int(channel)})
        return self._send('/clear', payload)

    def exit(self):
        return self._send('/exit', self._base('exit'))
