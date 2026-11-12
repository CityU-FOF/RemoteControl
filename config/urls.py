from django.urls import path
from assistant import views as v
urlpatterns = [path('',v.home),path('signin',v.signin),path('signout',v.signout),path('assets/<path:name>',v.asset),path('api/roots',v.roots),path('api/search',v.search),path('api/results',v.results),path('api/cancel',v.cancel),path('api/download',v.content),path('api/preview',lambda r:v.content(r,preview=True)),path('api/devices',v.devices),path('api/revoke',v.revoke)]
