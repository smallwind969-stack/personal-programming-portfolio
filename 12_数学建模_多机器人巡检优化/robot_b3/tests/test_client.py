import unittest
from unittest.mock import patch

from robot_b3.client import HttpTransport, ProtocolError, SimulatorClient


class FakeTransport:
    def __init__(self):
        self.calls = []
    def post(self, path, payload):
        self.calls.append((path, payload))
        if path == '/enter':
            return {'accepted': True, 'virtual_time_s': 0, 'remaining_real_duration_s': 1200}
        return {'accepted': True, 'virtual_time_s': 5, 'measure_result': 'no_signal'}


class ClientTests(unittest.TestCase):
    def test_connection_reset_is_retryable_protocol_error(self):
        with patch('urllib.request.urlopen',side_effect=ConnectionResetError('reset')):
            with self.assertRaises(ProtocolError):
                HttpTransport().post('/enter',{})

    def test_clear_leaves_measurement_channel_unchanged(self):
        tr=FakeTransport(); c=SimulatorClient('TEAM1',tr)
        c.enter(); c.measure((0,0),7); c.clear((0,0),4)
        self.assertEqual(c.current_channel,7)
    def test_network_retry_reuses_identical_request_id(self):
        class Flaky:
            def __init__(self): self.payloads=[]
            def post(self,path,payload):
                self.payloads.append(dict(payload))
                if len(self.payloads)==1: raise ProtocolError('temporary disconnect')
                return {'accepted':True,'virtual_time_s':0,'remaining_real_duration_s':1200}
        tr=Flaky(); SimulatorClient('TEAM1',tr,retry_count=1).enter()
        self.assertEqual(tr.payloads[0],tr.payloads[1])

    def test_measure_updates_current_channel(self):
        tr = FakeTransport(); c = SimulatorClient('TEAM1', tr)
        c.enter(); c.measure((0, 0), 7)
        self.assertEqual(c.current_channel, 7)
        self.assertNotEqual(tr.calls[0][1]['request_id'], tr.calls[1][1]['request_id'])

    def test_rejected_response_raises(self):
        class Reject:
            def post(self, path, payload):
                return {'accepted': False, 'virtual_time_s': 0}
        with self.assertRaises(ProtocolError):
            SimulatorClient('TEAM1', Reject()).enter()


if __name__ == '__main__':
    unittest.main()
