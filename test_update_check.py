import base64
import io
import json
import threading
import unittest
from update_check import available_update, version_tuple, UpdateCheck

URL='https://api.github.com/repos/TTdriver/example/contents/VERSION'
class Checks(unittest.TestCase):
    def response(self, version):
        return io.BytesIO(json.dumps({'encoding':'base64','content':base64.b64encode(version.encode()).decode()+'\n'}).encode())
    def test_version_comparisons_and_silence(self):
        for remote, expected in [('1.1.10','1.1.10'),('1.1.2',None),('1.0.99',None),('v1.2.3',None),('1.2',None),('1.2.3\nextra',None),('١.2.3',None)]:
            calls=[]
            def opener(request, timeout):
                calls.append((request,timeout));return self.response(remote)
            self.assertEqual(available_update('1.1.2',URL,'DesktopTest',opener),expected)
            self.assertEqual(len(calls),1);self.assertEqual(calls[0][1],5)
            self.assertIn('DesktopTest',calls[0][0].get_header('User-agent'))
            self.assertIsNone(calls[0][0].get_header('Authorization'))
    def test_unavailable_and_invalid_content(self):
        def unavailable(*args,**kwargs):raise OSError('offline')
        self.assertIsNone(available_update('1.1.2',URL,'DesktopTest',unavailable))
        for payload in [{},{'encoding':'base64','content':'***'},{'encoding':'utf-8','content':'1.2.3'}]:
            self.assertIsNone(available_update('1.1.2',URL,'DesktopTest',lambda *a,**k:io.BytesIO(json.dumps(payload).encode())))
    def test_once_background_queue(self):
        calls=[];main=threading.get_ident()
        def check(*args):calls.append(threading.get_ident());return '1.1.10'
        controller=UpdateCheck('1.1.2',URL,'DesktopTest',check);controller.start();controller.start()
        self.assertEqual(controller.results.get(timeout=1),'1.1.10');self.assertEqual(len(calls),1);self.assertNotEqual(calls[0],main)

if __name__=='__main__':unittest.main()
