from fastapi import FastAPI

app = FastAPI()

@app.get('/')
async def root():
    return {'status': 'ok', 'msg': 'minimal app working'}

@app.get('/api/v1/health')
async def health():
    return {'status': 'ok', 'app': 'ShiftSathi API', 'env': 'vercel-minimal'}

@app.api_route('/{path_name:path}', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
async def catch_all(path_name: str):
    return {'path': path_name, 'msg': 'caught by minimal app'}
