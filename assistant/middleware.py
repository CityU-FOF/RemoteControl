import logging, time
from django.http import JsonResponse
from .models import Control, Device
log = logging.getLogger('audit')
class Access:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        if request.path.startswith('/api/'):
            c, _ = Control.objects.get_or_create(pk=1)
            allowed = request.user.is_authenticated and time.time()-request.session.get('started',0)<28800 and not c.paused and request.session.get('generation') == c.generation and Device.objects.filter(session_key=request.session.session_key, revoked=False, user=request.user).exists()
            if not allowed:
                log.warning('authorization_denied')
                return JsonResponse({'error': '請重新登入，或由公司電腦恢復存取。'}, status=403)
        response = self.get_response(request)
        response['Cache-Control'] = 'no-store'
        response['Referrer-Policy'] = 'same-origin'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['Content-Security-Policy'] = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; worker-src 'self'; frame-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'self'; base-uri 'none'"
        if request.path == '/api/preview':
            response['Content-Security-Policy'] = "sandbox; default-src 'none'; frame-ancestors 'self'"
        return response
