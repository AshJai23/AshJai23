"""Local FastAPI interface. Start from the project directory, loopback only."""
from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from service import BusyError, RuntimeSetupError, build_runtime

ROOT=Path(__file__).resolve().parent
HEADERS={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
         'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"}
class RequestLimit:
    """Reject oversized HTTP bodies before JSON/Pydantic parsing, including chunked requests."""
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope.get('method')!='POST' or scope.get('path')!='/v1/ask':
            return await self.app(scope,receive,send)
        chunks=[];total=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            block=message.get('body',b'');total+=len(block)
            if total>8192:
                return await JSONResponse(status_code=413,content={'detail':'Request body exceeds 8 KiB'},headers=HEADERS)(scope,receive,send)
            chunks.append(block)
            if not message.get('more_body',False):break
        sent=False
        async def bounded_receive():
            nonlocal sent
            if not sent:
                sent=True
                return {'type':'http.request','body':b''.join(chunks),'more_body':False}
            return await receive()
        await self.app(scope,bounded_receive,send)

class Ask(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    question:str=Field(min_length=1,max_length=500)
    @field_validator('question')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('Question cannot be blank')
        return value

def create_app(runtime=None, loader=build_runtime):
    @asynccontextmanager
    async def lifespan(app):
        app.state.runtime=runtime
        app.state.startup_error=None
        app.state.setup=None
        if runtime is None:
            try:
                mode=os.environ.get('W01_RETRIEVAL','hybrid')
                generation=os.environ.get('W01_GENERATION','on')
                if generation not in ('on','off'):raise ValueError('Invalid generation mode')
                app.state.runtime=loader(mode=mode,with_generation=generation=='on')
            except RuntimeSetupError as exc:
                app.state.startup_error=type(exc).__name__
                app.state.setup={"code":exc.code,"action":exc.action}
            except Exception as exc:
                # Keep diagnostics coarse: no user data, filesystem paths or secrets.
                app.state.startup_error=type(exc).__name__
        yield
        app.state.runtime=None
    app=FastAPI(title='W01 UK Retail Copilot — local research prototype',version='0.2.0',lifespan=lifespan)
    app.add_middleware(RequestLimit)
    @app.exception_handler(RequestValidationError)
    async def invalid(_request,exc):
        return JSONResponse(status_code=422,content={'detail':'Invalid request: provide only a nonblank question of at most 500 characters.'},headers=HEADERS)
    @app.get('/',response_class=HTMLResponse,include_in_schema=False)
    def home():return HTMLResponse((ROOT/'web/index.html').read_text(),headers=HEADERS)
    @app.get('/assets/app.js',include_in_schema=False)
    def javascript():return Response((ROOT/'web/app.js').read_text(),media_type='text/javascript',headers=HEADERS)
    @app.get('/v1/health')
    def health():
        active=getattr(app.state,'runtime',None)
        return JSONResponse(status_code=200 if active else 503,content={
            'status':'ready' if active else 'not_ready','retrieval':active.retrieval_mode if active else None,
            'local_generation_enabled':active.generator is not None if active else False,
            'source':active.source if active else None,
            'error':getattr(app.state,'startup_error',None),
            'setup':getattr(app.state,'setup',None),
            'notice':'Local historical-data prototype; generation may be rejected. Not live sales.'},headers=HEADERS)
    @app.get('/v1/metrics')
    def metrics():
        active=getattr(app.state,'runtime',None)
        if active is None:raise HTTPException(503,'Runtime unavailable; follow local setup instructions')
        return JSONResponse(active.metrics(),headers=HEADERS)
    @app.post('/v1/ask')
    def ask(request:Ask):
        active=getattr(app.state,'runtime',None)
        if active is None:raise HTTPException(503,'Runtime unavailable; no fallback answer generated')
        try:return JSONResponse(active.ask(request.question),headers=HEADERS)
        except BusyError:raise HTTPException(429,'Local inference is busy; retry later',headers={'Retry-After':'5'})
        except Exception:raise HTTPException(503,'Workflow failed; no fallback answer generated')
    return app

app=create_app()
