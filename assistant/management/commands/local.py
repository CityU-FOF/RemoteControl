import getpass, os, logging
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.sessions.models import Session
from assistant.models import Root, Control, Device
from assistant.files import opened

class Command(BaseCommand):
    help='本機管理（不可經網頁呼叫）'
    def add_arguments(self,p):
        p.add_argument('action',choices=['user','add','remove','list','pause','resume','revoke-all','devices','revoke'])
        p.add_argument('value',nargs='?')
        p.add_argument('--label')
    def handle(self,action,value=None,label=None,**opts):
        c,_=Control.objects.get_or_create(pk=1)
        if action=='user':
            if not value: raise CommandError('請指定帳號名稱')
            User=get_user_model()
            user,_=User.objects.get_or_create(username=value)
            password=getpass.getpass('密碼（至少 12 字元）：')
            if password!=getpass.getpass('再次輸入：'): raise CommandError('密碼不同')
            try: validate_password(password,user)
            except ValidationError as e: raise CommandError('; '.join(e.messages))
            user.set_password(password); user.save()
            Device.objects.filter(user=user).update(revoked=True)
        elif action=='add':
            if not value: raise CommandError('請指定完整資料夾路徑')
            raw=Path(os.path.abspath(value))
            if raw==Path(raw.anchor) or raw==Path.home() or raw==Path.home()/'Desktop': raise CommandError('不可分享磁碟根目錄、整個使用者目錄或整個桌面')
            if not raw.is_dir(): raise CommandError('資料夾不存在或無權限')
            st=raw.stat(follow_symlinks=False)
            r=Root(path=str(raw),device=str(st.st_dev),inode=str(st.st_ino),label=label or raw.name)
            try:
                with opened(r,directory=True): pass
                # Reject overlapping roots to avoid confusing scope changes.
                for old in Root.objects.all():
                    try: common=os.path.commonpath([old.path,str(raw)])
                    except ValueError: continue # distinct Windows drives
                    if common in (old.path,str(raw)): raise CommandError('已設定相同或重疊的資料夾')
            except OSError: raise CommandError('無法讀取或包含連結／junction；請選擇實體資料夾')
            r.save()
        elif action=='remove': Root.objects.filter(pk=value).delete()
        elif action=='list':
            for r in Root.objects.all(): self.stdout.write(f'{r.pk}: {r.label} — {r.path}')
        elif action in ('pause','resume'):
            c.paused=action=='pause'; c.generation+=1; c.save()
            Device.objects.update(revoked=True); Session.objects.all().delete()
        elif action=='revoke-all':
            c.generation+=1; c.save(); Device.objects.update(revoked=True); Session.objects.all().delete()
        elif action=='devices':
            for d in Device.objects.filter(revoked=False): self.stdout.write(f'{d.pk}: {d.user.username} {d.created.isoformat()}')
        elif action=='revoke': Device.objects.filter(pk=value).update(revoked=True)
        logging.getLogger('audit').info('local_management action=%s',action)
        self.stdout.write('完成')
