"""Local-only entrypoint. No configurable external bind or proxy trust."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
from django.core.wsgi import get_wsgi_application
from waitress import serve
if __name__ == '__main__':
    serve(get_wsgi_application(),host='127.0.0.1',port=8765,threads=8,clear_untrusted_proxy_headers=True,max_request_body_size=16384)
