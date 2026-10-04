from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.testclient import TestClient

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'"
        if request.url.scheme == 'https' or request.headers.get('x-forwarded-proto') == 'https':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

app = FastAPI()

# In Starlette, middlewares are executed in reverse order of addition.
# If we want SecurityHeadersMiddleware to run OUTSIDE CORSMiddleware:
# We add SecurityHeadersMiddleware AFTER CORSMiddleware!
app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type', 'Accept', 'Origin', 'X-Requested-With'],
)
app.add_middleware(SecurityHeadersMiddleware)

@app.get('/test')
def test():
    return {'ok': True}

client = TestClient(app)

res_opt = client.options('/test', headers={
    'Origin': 'http://localhost:3000',
    'Access-Control-Request-Method': 'POST',
    'Access-Control-Request-Headers': 'authorization,content-type',
})
print('OPTIONS /test (preflight allowed):')
print('  status:', res_opt.status_code)
print('  CORS Allow-Origin:', res_opt.headers.get('access-control-allow-origin'))
print('  X-Content-Type-Options:', res_opt.headers.get('x-content-type-options'))
print('  X-Frame-Options:', res_opt.headers.get('x-frame-options'))

res_get = client.get('/test', headers={'Origin': 'http://localhost:3000'})
print('GET /test:')
print('  X-Content-Type-Options:', res_get.headers.get('x-content-type-options'))
print('  X-Frame-Options:', res_get.headers.get('x-frame-options'))
