import json, os, tempfile, time, threading
from pathlib import Path
from unittest.mock import patch
from django.test import TransactionTestCase, Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from assistant.models import Root, Device, Control
from assistant.files import opened
from assistant import views

class SecurityTests(TransactionTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'allowed';self.path.mkdir()
        self.outside=Path(self.temp.name)/'allowed-other';self.outside.mkdir()
        (self.outside/'secret.txt').write_text('outside secret')
        for name in ['中文 文件 #& [].txt','same.txt','special + % file.txt','sample.svg','bad.html']:
            (self.path/name).write_text('<script>alert(1)</script>中文',encoding='utf-8')
        (self.path/'sub').mkdir();(self.path/'sub'/'same.txt').write_text('second')
        (self.path/'big.bin').touch()
        with (self.path/'big.bin').open('wb') as f: f.truncate(25*1024*1024)
        st=self.path.stat();self.root=Root.objects.create(label='文件',path=str(self.path),device=str(st.st_dev),inode=str(st.st_ino))
        self.user=get_user_model().objects.create_user('reader',password='sample-long-password-192')
        self.client=Client(HTTP_HOST='localhost')
        self.assertEqual(self.client.post('/signin',{'username':'reader','password':'sample-long-password-192'}).status_code,302)
    def tearDown(self):
        for j in list(views.JOBS.values()):j['cancel'].set()
        deadline=time.monotonic()+3
        while any(not j['done'] for j in views.JOBS.values()) and time.monotonic()<deadline:time.sleep(.01)
        views.JOBS.clear()
        self.temp.cleanup()
    def api(self,route,d=None,client=None):return (client or self.client).post('/api/'+route,json.dumps(d or {}),content_type='application/json')
    def search(self,**kwargs):
        r=self.api('search',{'root':self.root.pk,**kwargs});self.assertEqual(r.status_code,200,r.content)
        job=r.json()['job']; deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            result=self.api('results',{'job':job})
            self.assertEqual(result.status_code,200,result.content)
            if result.json()['done']:return result.json(),job
            time.sleep(.02)
        self.fail('search did not finish')
    def file(self,name,preview=False):return self.client.post('/api/'+('preview' if preview else 'download'),{'root':self.root.pk,'path':name})
    def test_chinese_partial_names_duplicate_sort_and_filters(self):
        d,_=self.search(q='文',recursive=True);self.assertEqual(d['total'],1);self.assertEqual(d['rows'][0]['name'],'中文 文件 #& [].txt')
        d,_=self.search(q='same',recursive=True,extension='TXT',sort='size',descending=True)
        self.assertEqual({r['path'] for r in d['rows']},{'same.txt','sub/same.txt'})
        d,_=self.search(after='2100-01-01');self.assertEqual(d['total'],0)
        response=self.file('中文 文件 #& [].txt');self.assertIn('filename*=utf-8',response['Content-Disposition']);self.assertIn('中文'.encode(),b''.join(response.streaming_content))
    def test_all_interfaces_require_auth(self):
        anon=Client(HTTP_HOST='localhost')
        for route in ['roots','search','results','cancel','devices','revoke','preview','download']:
            with self.subTest(route=route):self.assertEqual(self.api(route,client=anon).status_code,403)
    def test_revoked_device_all_interfaces(self):
        Device.objects.update(revoked=True)
        for route in ['roots','search','results','cancel','devices','revoke','preview','download']:
            with self.subTest(route=route):self.assertEqual(self.api(route).status_code,403)
    def test_removed_root(self):
        d,job=self.search();rid=self.root.pk;self.root.delete()
        self.assertEqual(self.api('results',{'job':job}).status_code,400)
        self.assertEqual(self.api('search',{'root':rid}).status_code,400)
        for route in ['preview','download']:self.assertEqual(self.client.post('/api/'+route,{'root':rid,'path':'same.txt'}).status_code,400)
        self.assertEqual(self.api('roots').json()['roots'],[])
    def test_traversal_and_encoded_bypasses(self):
        for name in ['../allowed-other/secret.txt','/etc/passwd','..\\allowed-other\\secret.txt','%2e%2e/secret.txt','%252e%252e/secret.txt','C:/secret.txt','same.txt:stream','sub/../same.txt','sub//same.txt','same.txt.','NUL']:
            with self.subTest(name=name):
                self.assertEqual(self.file(name).status_code,400)
                self.assertEqual(self.file(name,True).status_code,400)
                self.assertEqual(self.api('search',{'root':self.root.pk,'path':name}).status_code,400)
    def test_symlink_directory_file_escape(self):
        try:
            (self.path/'escape').symlink_to(self.outside,target_is_directory=True)
            (self.path/'linked.txt').symlink_to(self.outside/'secret.txt')
        except OSError:self.skipTest('OS does not allow symlink creation')
        self.assertEqual(self.file('escape/secret.txt').status_code,400)
        self.assertEqual(self.file('linked.txt').status_code,400)
        d,_=self.search(recursive=True);self.assertNotIn('secret.txt',[r['name'] for r in d['rows']]);self.assertNotIn('linked.txt',[r['name'] for r in d['rows']])
    def test_replaced_root_identity(self):
        self.path.rename(self.path.with_name('old'));self.path.mkdir();(self.path/'same.txt').write_text('replaced')
        self.assertEqual(self.file('same.txt').status_code,400)
        self.assertIn('無法讀取',self.api('roots').json()['roots'][0]['status'])
    def test_missing_permission_and_offline(self):
        (self.path/'same.txt').unlink();self.assertEqual(self.file('same.txt').status_code,400)
        with patch('assistant.views.opened',side_effect=PermissionError()):self.assertEqual(self.file('中文 文件 #& [].txt').status_code,400)
        self.path.rename(self.path.with_name('offline'));self.assertIn('無法讀取',self.api('roots').json()['roots'][0]['status'])
    def test_large_stream_and_revocation_midstream(self):
        r=self.file('big.bin');self.assertTrue(r.streaming);self.assertEqual(int(r['Content-Length']),25*1024*1024)
        iterator=iter(r.streaming_content);self.assertLess(len(next(iterator)),1024*1024)
        Device.objects.update(revoked=True);self.assertEqual(b''.join(iterator),b'')
    def test_preview_active_formats_and_limits(self):
        for name in ['sample.svg','bad.html','big.bin']:self.assertEqual(self.file(name,True).status_code,415)
        r=self.file('中文 文件 #& [].txt',True);self.assertTrue(r['Content-Type'].startswith('text/plain'));self.assertIn('sandbox',r['Content-Security-Policy']);r.close()
        r=self.file('sample.svg');self.assertIn('attachment',r['Content-Disposition']);self.assertEqual(r['Content-Type'],'application/octet-stream');r.close()
    def test_search_cancel_and_job_owner(self):
        original=views.entries
        def slow(*args):
            for row in original(*args):time.sleep(.03);yield row
        with patch('assistant.views.entries',slow):
            r=self.api('search',{'root':self.root.pk,'recursive':True});job=r.json()['job']
            self.assertEqual(self.api('cancel',{'job':job}).status_code,200)
            self.assertTrue(self.api('results',{'job':job}).json()['cancelled'])
        self.client.post('/signout');self.client.post('/signin',{'username':'reader','password':'sample-long-password-192'})
        self.assertEqual(self.api('results',{'job':job}).status_code,400)
    def test_pagination_limit(self):
        for i in range(75):(self.path/f'doc-{i}.txt').touch()
        d,job=self.search();self.assertEqual(len(d['rows']),50)
        d=self.api('results',{'job':job,'page':2}).json();self.assertGreater(len(d['rows']),0)
        with patch('assistant.views.MAX_SCAN',5):
            d,_=self.search();self.assertTrue(d['limited'])
    def test_csrf_and_method_restrictions(self):
        c=Client(enforce_csrf_checks=True,HTTP_HOST='localhost');self.assertEqual(c.post('/signin',{}).status_code,403)
        for route in ['roots','search','preview','download','revoke']:self.assertEqual(self.client.get('/api/'+route).status_code,405)
    def test_pause_and_revoke_all(self):
        call_command('local','pause',verbosity=0);self.assertEqual(self.api('roots').status_code,403)
        call_command('local','resume',verbosity=0);self.assertEqual(self.api('roots').status_code,403)
        self.client.post('/signin',{'username':'reader','password':'sample-long-password-192'})
        call_command('local','revoke-all',verbosity=0);self.assertEqual(self.api('roots').status_code,403)
    def test_absolute_and_idle_expiry(self):
        s=self.client.session;s['started']=time.time()-28801;s.save();self.assertEqual(self.api('roots').status_code,403)
    def test_login_rate_limit(self):
        c=Client(HTTP_HOST='localhost')
        for _ in range(5):self.assertIn(c.post('/signin',{'username':'reader','password':'wrong'}).status_code,(403,429))
        self.assertEqual(c.post('/signin',{'username':'reader','password':'sample-long-password-192'}).status_code,429)
    def test_logout(self):
        self.client.post('/signout');self.assertEqual(self.api('roots').status_code,403)
    def test_local_scope_restrictions(self):
        from django.core.management.base import CommandError
        for path in [Path.home(),Path(self.path.anchor),Path.home()/'Desktop']:
            with self.assertRaises(CommandError):call_command('local','add',str(path))

    def test_stream_stops_on_root_removal(self):
        r=self.file('big.bin');it=iter(r.streaming_content);next(it)
        self.root.delete();self.assertEqual(b''.join(it),b'')
    def test_real_permission_denied(self):
        if os.name=='nt' or (hasattr(os,'geteuid') and os.geteuid()==0):self.skipTest('POSIX ordinary-user permission test only')
        p=self.path/'same.txt';p.chmod(0)
        try:self.assertEqual(self.file('same.txt').status_code,400)
        finally:p.chmod(0o600)
    def test_windows_junction_escape(self):
        if os.name!='nt':self.skipTest('Requires Windows 11; not validated by Linux')
        import subprocess
        link=self.path/'junction'
        subprocess.run(['cmd','/c','mklink','/J',str(link),str(self.outside)],check=True,capture_output=True)
        try:
            self.assertEqual(self.file('junction/secret.txt').status_code,400)
            self.assertEqual(self.api('search',{'root':self.root.pk,'path':'junction'}).status_code,400)
        finally:os.rmdir(link)

    def test_safe_preview_content_types(self):
        import base64
        (self.path/'pixel.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF1sAAAAASUVORK5CYII='))
        (self.path/'sample.pdf').write_bytes(b'%PDF-1.4\n%%EOF')
        (self.path/'report.docx').write_bytes(b'not parsed')
        for name,mime in [('pixel.png','image/png'),('sample.pdf','application/pdf')]:
            r=self.file(name,True);self.assertEqual(r.status_code,200);self.assertEqual(r['Content-Type'],mime)
            self.assertIn('inline',r['Content-Disposition']);self.assertTrue(b''.join(r.streaming_content))
        self.assertEqual(self.file('report.docx',True).status_code,415)
    def test_inflight_search_removed_root_and_session(self):
        entered=threading.Event();release=threading.Event()
        original=views.entries
        def delayed(*args):
            entered.set();release.wait(2)
            yield from original(*args)
        with patch('assistant.views.entries',delayed):
            r=self.api('search',{'root':self.root.pk});job=r.json()['job']
            self.assertTrue(entered.wait(2))
            self.root.delete();release.set()
            self.assertEqual(self.api('results',{'job':job}).status_code,400)

    def test_idle_session_expired(self):
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        from datetime import timedelta
        Session.objects.filter(session_key=self.client.session.session_key).update(expire_date=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.api('roots').status_code,403)
