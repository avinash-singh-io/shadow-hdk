import json, os
from proxy.http.proxy import HttpProxyBasePlugin
from proxy.http.exception import HttpRequestRejected
class Origins(HttpProxyBasePlugin):
 def check(self,request):
  allowed=json.loads(os.environ.get('HDK67_ALLOWED_PORTS','[]'))
  if request.host != b'127.0.0.1' or request.port not in allowed:
   raise HttpRequestRejected(status_code=403,reason=b'Origin denied')
  return request
 def before_upstream_connection(self,request):return self.check(request)
 def handle_client_request(self,request):return self.check(request)
