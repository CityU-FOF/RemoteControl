"""Isolated real-browser test, synthetic files only. No password in logs/argv."""
import os, secrets, subprocess, sys, tempfile, time
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
with tempfile.TemporaryDirectory() as temp:
    os.environ['RFA_STATE']=str(Path(temp)/'state')
    os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
    import django
    django.setup()
    from django.core.management import call_command
    from django.contrib.auth import get_user_model
    from assistant.models import Root
    call_command('migrate',verbosity=0)
    password=secrets.token_urlsafe(24)
    get_user_model().objects.create_user('browser-test',password=password)
    folder=Path(temp)/'sample';folder.mkdir()
    (folder/'中文 文件 #& [].txt').write_text('示範文字：測試成功',encoding='utf-8')
    (folder/'report.docx').write_bytes(b'sample only')
    import base64
    (folder/'pixel.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF1sAAAAASUVORK5CYII='))
    pdf=bytearray(b'%PDF-1.4\n')
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    stream=b'BT /F1 24 Tf 30 100 Td (PDF preview test) Tj ET'
    objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
    offsets=[0]
    for i,obj in enumerate(objects,1):
        offsets.append(len(pdf));pdf+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    xref=len(pdf);pdf+=f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode()
    for offset in offsets[1:]:pdf+=f'{offset:010} 00000 n \n'.encode()
    pdf+=f'trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    (folder/'sample.pdf').write_bytes(pdf)
    st=folder.stat();Root.objects.create(label='測試文件',path=str(folder),device=str(st.st_dev),inode=str(st.st_ino))
    server=subprocess.Popen([sys.executable,str(BASE/'serve.py')],cwd=BASE,env=os.environ,stdout=subprocess.DEVNULL,stderr=None)
    try:
        import urllib.request
        for _ in range(100):
            try:
                urllib.request.urlopen('http://127.0.0.1:8765/',timeout=.2);break
            except OSError:time.sleep(.05)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
            context=browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,device_scale_factor=3,accept_downloads=True)
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto('http://127.0.0.1:8765/')
            page.locator('[name=username]').fill('browser-test');page.locator('[name=password]').fill(password)
            page.get_by_role('button',name='登入',exact=True).click()
            try: page.get_by_text('找到 4 項',exact=True).wait_for(timeout=10000)
            except Exception:
                print(page.locator('body').inner_text());print(errors);raise
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'
            page.locator('#query').fill('中文');page.get_by_role('button',name='搜尋／重新整理',exact=True).click()
            page.get_by_text('找到 1 項',exact=True).wait_for()
            page.get_by_role('button',name='預覽',exact=True).click()
            frame=page.frame_locator('[name=documentPreview]')
            frame.get_by_text('示範文字：測試成功',exact=False).wait_for()
            with page.expect_download(timeout=7000) as event:
                page.get_by_role('button',name='下載目前文件',exact=True).tap()

            download=event.value
            assert download.suggested_filename=='中文 文件 #& [].txt'
            assert Path(download.path()).read_text(encoding='utf-8')=='示範文字：測試成功'
            page.locator('#query').fill('pixel');page.get_by_role('button',name='搜尋／重新整理').click()
            page.get_by_role('heading',name='📄 pixel.png').wait_for()
            page.get_by_role('button',name='預覽',exact=True).click()
            frame=page.frame_locator('[name=documentPreview]')
            frame.locator('img').wait_for(timeout=5000)
            assert frame.locator('img').evaluate('(img)=>img.complete && img.naturalWidth===1')
            page.get_by_role('button',name='關閉預覽').click()
            page.locator('#query').fill('sample');page.get_by_role('button',name='搜尋／重新整理').click()
            page.get_by_role('heading',name='📄 sample.pdf').wait_for()
            page.get_by_role('button',name='預覽',exact=True).click()
            page.get_by_text('PDF 第 1 / 1 頁',exact=True).wait_for()
            page.wait_for_function('document.getElementById("pdfCanvas").width>0')
            page.wait_for_function('()=>{const c=document.getElementById("pdfCanvas");const d=c.getContext("2d").getImageData(0,0,c.width,c.height).data;return d.some((v,i)=>i%4===0&&v<100&&d[i+3]===255)}')
            page.get_by_role('button',name='關閉預覽').click()
            page.locator('#query').fill('report');page.get_by_role('button',name='搜尋／重新整理').click()
            try: page.get_by_role('heading',name='📄 report.docx').wait_for(timeout=8000)
            except Exception:
                print('ERROR',page.locator('#status').inner_text(),errors);raise
            assert page.locator('#results').get_by_role('button',name='預覽',exact=True).count()==0
            for width in [375,430,768]:
                page.set_viewport_size({'width':width,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.get_by_role('button',name='查看裝置').click();page.get_by_role('button',name='撤銷',exact=True).wait_for()
            page.get_by_role('button',name='登出此裝置').click();page.get_by_role('button',name='登入',exact=True).wait_for()
            assert not errors, errors
            print('PASS: Chromium mobile 375/390/430/768px, login, search, text/image/PDF canvas preview, Chinese download, Office metadata, devices, logout; no JS errors.')
            browser.close()
    finally:
        server.terminate();server.wait(timeout=10)
