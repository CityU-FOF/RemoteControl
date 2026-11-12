import json, logging, os, threading, time, uuid
from datetime import datetime, timezone
from pathlib import Path
from django.contrib.auth import authenticate, login, logout
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST, require_GET
from django.db import close_old_connections
from .models import Root, Control, Device
from .files import opened, entries, Denied
log = logging.getLogger('audit')
JOBS = {}
LOCK = threading.Lock()
SLOTS = threading.BoundedSemaphore(4)
MAX_SCAN = 20000
MAX_RESULTS = 2000

def data(request):
    try:
        value = json.loads(request.body or b'{}')
        if not isinstance(value, dict): raise ValueError()
        return value
    except (ValueError, UnicodeDecodeError): raise Denied('無效請求')

def root_for(value):
    try: return Root.objects.get(pk=int(value))
    except (ValueError, TypeError, Root.DoesNotExist): raise Denied('資料夾不存在或已移除')

def api(fn):
    def wrapped(request):
        try: return fn(request)
        except (OSError, ValueError, TypeError, OverflowError):
            log.warning('file_access_failed')
            return JsonResponse({'error':'無法讀取：檔案或資料夾不存在、離線、無權限，或路徑不允許。'}, status=400)
    return require_POST(wrapped)

def home(request): return render(request, 'index.html', {'signed_in': request.user.is_authenticated})

@require_POST
def signin(request):
    user = authenticate(request, username=request.POST.get('username',''), password=request.POST.get('password',''))
    c, _ = Control.objects.get_or_create(pk=1)
    if user is None or c.paused:
        log.warning('login_failed_or_paused')
        return render(request, 'index.html', {'error': '登入失敗、已限速或本機已暫停。請稍後再試。'}, status=403)
    login(request, user)
    request.session['generation'] = c.generation
    request.session['started'] = time.time()
    request.session.save()
    Device.objects.create(user=user, session_key=request.session.session_key)
    log.info('login_success device=%s', Device.objects.get(session_key=request.session.session_key).pk)
    return redirect('/')

@require_POST
def signout(request):
    Device.objects.filter(session_key=request.session.session_key).update(revoked=True)
    logout(request)
    log.info('logout')
    return redirect('/')

@api
def roots(request):
    result=[]
    for r in Root.objects.all():
        try:
            with opened(r, directory=True): pass
            state='可使用'
        except FileNotFoundError: state='無法讀取：資料夾不存在或網絡磁碟離線'
        except PermissionError: state='無法讀取：目前 Windows 帳戶沒有權限或檔案被鎖定'
        except Denied: state='無法讀取：資料夾已更換或包含不允許的連結'
        except OSError: state='無法讀取：裝置離線或系統錯誤'
        result.append({'id':r.pk, 'label':r.label, 'status':state})
    return JsonResponse({'roots':result})

@api
def devices(request):
    return JsonResponse({'devices': list(Device.objects.filter(user=request.user, revoked=False).values('id','created'))})

@api
def revoke(request):
    d=data(request)
    Device.objects.filter(pk=d.get('id'),user=request.user).update(revoked=True)
    log.info('device_revoked')
    return JsonResponse({'ok':True})

def active(job):
    c=Control.objects.get(pk=1)
    return not job['cancel'].is_set() and not c.paused and c.generation == job['generation'] and Root.objects.filter(pk=job['root']).exists() and Device.objects.filter(session_key=job['owner'],revoked=False).exists()

def worker(job, root, d):
    close_old_connections()
    try:
        pending=[d.get('path','')]
        q=str(d.get('q','')).casefold()
        extension=str(d.get('extension','')).casefold().lstrip('.')
        after=datetime.fromisoformat(d['after']).replace(tzinfo=timezone.utc).timestamp() if d.get('after') else float('-inf')
        before=datetime.fromisoformat(d['before']).replace(tzinfo=timezone.utc).timestamp()+86400 if d.get('before') else float('inf')
        rows=[]
        scanned=0
        errors=0
        while pending:
            if not active(job): break
            folder=pending.pop()
            try:
                for row in entries(root,folder):
                    scanned += 1
                    if scanned % 32 == 0 and not active(job): break
                    if scanned >= MAX_SCAN or time.monotonic()-job['time']>15 or len(rows)>=MAX_RESULTS:
                        job['limited']=True
                        pending=[]
                        break
                    if d.get('recursive') and row['directory']: pending.append(row['path'])
                    if q not in row['name'].casefold(): continue
                    if extension and (row['directory'] or Path(row['name']).suffix.casefold() != '.'+extension): continue
                    if not after <= row['modified'] < before: continue
                    rows.append(row)
            except OSError:
                errors += 1
        key=d.get('sort','name')
        if key not in ('name','modified','size'): raise ValueError()
        rows.sort(key=lambda x: x[key].casefold() if key=='name' else x[key], reverse=d.get('descending') is True)
        with LOCK:
            job['rows']=rows if active(job) else []
            job['errors']=errors
            job['scanned']=scanned
            job['cancelled']=not active(job)
    except (OSError, ValueError, TypeError):
        job['error']='搜尋失敗：請檢查條件及資料夾狀態。'
        log.warning('search_failed')
    finally:
        job['done']=True
        SLOTS.release()
        close_old_connections()

@api
def search(request):
    d=data(request)
    root=root_for(d.get('root'))
    with opened(root,d.get('path',''),directory=True): pass
    with LOCK:
        for key,j in list(JOBS.items()):
            if time.monotonic()-j['time']>300 or (j['owner']==request.session.session_key and j['done']):
                j['cancel'].set()
                del JOBS[key]
        if len(JOBS)>=32:
            return JsonResponse({'error':'搜尋快取已滿，請稍後再試。'},status=429)
        if any(j['owner']==request.session.session_key and not j['done'] for j in JOBS.values()) or not SLOTS.acquire(blocking=False):
            return JsonResponse({'error':'已有搜尋進行中，請先取消或稍後再試。'},status=429)
        key=uuid.uuid4().hex
        job={'owner':request.session.session_key,'root':root.pk,'generation':request.session['generation'],'time':time.monotonic(),'cancel':threading.Event(),'done':False,'rows':[],'limited':False}
        JOBS[key]=job
    threading.Thread(target=worker,args=(job,root,d),daemon=True).start()
    return JsonResponse({'job':key})

@api
def results(request):
    d=data(request)
    with LOCK: job=JOBS.get(d.get('job'))
    if not job or job['owner']!=request.session.session_key: raise Denied()
    root_for(job['root'])
    if not active(job):
        if not job['cancel'].is_set(): raise Denied()
        return JsonResponse({'done':True,'cancelled':True,'rows':[]})
    page=max(1,int(d.get('page',1)))
    rows=job['rows']
    return JsonResponse({'done':job['done'],'rows':rows[(page-1)*50:page*50], 'total':len(rows),'limited':job['limited'],'errors':job.get('errors',0),'error':job.get('error')})

@api
def cancel(request):
    with LOCK: job=JOBS.get(data(request).get('job'))
    if job and job['owner']==request.session.session_key: job['cancel'].set()
    return JsonResponse({'ok':True})

SAFE = {'.pdf':'application/pdf','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.gif':'image/gif','.webp':'image/webp','.bmp':'image/bmp','.txt':'text/plain; charset=utf-8','.log':'text/plain; charset=utf-8','.csv':'text/plain; charset=utf-8','.md':'text/plain; charset=utf-8'}
@require_POST
def content(request, preview=False):
    f=None
    try:
        root=root_for(request.POST.get('root'))
        relative=request.POST.get('path','')
        suffix=Path(relative).suffix.casefold()
        with opened(root,relative) as fd:
            st=os.fstat(fd)
            if preview and (suffix not in SAFE or st.st_size>20*1024*1024):
                return JsonResponse({'error':'此格式或超過 20 MiB，請下載後用相容 App 開啟。'},status=415)
            f=os.fdopen(os.dup(fd),'rb')
        log.info('%s user=%s root=%s', 'preview' if preview else 'download', request.user.pk, root.pk)
        response=FileResponse(f,as_attachment=not preview,filename=Path(relative).name,content_type=SAFE.get(suffix,'application/octet-stream') if preview else 'application/octet-stream')
        response.block_size = 65536
        original = response.streaming_content
        owner = request.session.session_key
        generation = request.session['generation']
        deadline = min(time.time()+1800, request.session['started']+28800)
        def guarded():
            try:
                for chunk in original:
                    c = Control.objects.get(pk=1)
                    if time.time()>deadline or c.paused or c.generation != generation or not Root.objects.filter(pk=root.pk).exists() or not Device.objects.filter(session_key=owner, revoked=False).exists():
                        break
                    yield chunk
            finally:
                f.close()
        response.streaming_content = guarded()
        response['Content-Length']=st.st_size
        return response
    except (OSError, ValueError, TypeError):
        if f: f.close()
        log.warning('file_access_failed')
        return JsonResponse({'error':'無法讀取檔案：已移除、無權限或路徑不允許。'},status=400)

@require_GET
def asset(request, name):
    base=Path(__file__).parent / 'static'
    if name.startswith('pdfjs/'):
        manifest=json.loads((base.parent.parent / 'pdfjs-vendor.lock.json').read_text())['files']
        if name[6:] not in manifest: return HttpResponse(status=404)
    elif name not in ('app.js','app.css'): return HttpResponse(status=404)
    mime='text/javascript' if name.endswith(('.js','.mjs')) else 'text/css' if name.endswith('.css') else 'application/wasm' if name.endswith('.wasm') else 'application/octet-stream'
    return FileResponse(open(base / name,'rb'),content_type=mime)
