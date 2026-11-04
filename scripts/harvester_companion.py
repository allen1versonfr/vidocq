"""GPL-2.0-only companion over the separately pinned theHarvester runtime.
Vidocq communicates over authenticated loopback IPC; no upstream code is imported by Vidocq.
"""
import argparse,asyncio,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from companion_scope import harvester_request,HARVESTER_COMMIT

def configure(data):
    data=Path(data).resolve();data.mkdir(parents=True,exist_ok=True)
    os.environ.update(THEHARVESTER_RUN_DB=str(data/'runs.sqlite'),THEHARVESTER_RUN_ARTIFACTS=str(data/'run-artifacts'),THEHARVESTER_SCHEDULE_DB=str(data/'schedules.sqlite'),THEHARVESTER_SCHEDULER='disabled')
    from theHarvester.lib import core
    # Never read/write the user's ~/.theHarvester credentials or proxy configuration.
    core.CONFIG_DIRS=[core.DATA_DIR];core.Core.quiet=True
    return data

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int);parser.add_argument('--data',required=True);parser.add_argument('--execute');parser.add_argument('--database');args=parser.parse_args()
    data=configure(args.data)
    if args.execute:
        if Path(args.database).resolve()!=data/'runs.sqlite':raise ValueError('Worker database outside managed scope.')
        from theHarvester.lib.api.run_worker import _child_execute
        asyncio.run(_child_execute(args.execute,data/'runs.sqlite'));return
    from theHarvester.lib.api.api import create_app
    from theHarvester.lib.api.runtime import ApiRuntime
    from theHarvester.lib.api.run_worker import RunWorker
    from theHarvester.lib.api.schedule_service import SchedulerService
    from theHarvester.lib.api.run_store import RunStore
    class ReadyRuntime(ApiRuntime):
        async def start(self):
            await RunStore().initialize()
            await super().start()
    class Worker(RunWorker):
        async def _default_process_factory(self,run_id,database,artifact_dir):
            command=[sys.executable]+([] if getattr(sys,'frozen',False) else [str(Path(__file__).resolve())])+['--data',str(data),'--execute',run_id,'--database',str(database)]
            process=await asyncio.create_subprocess_exec(*command,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,creationflags=0x08000200 if os.name=='nt' else 0)
            self._process_groups[process]=process.pid;return process
    def runtime():
        worker=Worker();return ReadyRuntime(worker=worker,scheduler=SchedulerService(worker))
    upstream=create_app(runtime_factory=runtime)
    class Gate:
        async def __call__(self,scope,receive,send):
            if scope['type']!='http':return await upstream(scope,receive,send)
            import hmac,re
            headers=dict(scope['headers']);key=os.environ.get('THEHARVESTER_API_KEY','').encode()
            async def reply(code,value):
                body=json.dumps(value).encode();await send({'type':'http.response.start','status':code,'headers':[(b'content-type',b'application/json')]});await send({'type':'http.response.body','body':body})
            if not key or not hmac.compare_digest(headers.get(b'x-api-key',b''),key):return await reply(401,{'error':'Authentication required.'})
            path=scope['path'];method=scope['method']
            if method=='GET' and path=='/api/about':return await reply(200,{'service':'vidocq-harvester','protocol':1,'commit':HARVESTER_COMMIT,'passive_only':True})
            allowed=(method=='GET' and path=='/api/v1/sources') or (method=='GET' and re.fullmatch(r'/api/v1/runs/[0-9a-f-]{36}',path)) or (method=='POST' and re.fullmatch(r'/api/v1/runs/[0-9a-f-]{36}/cancel',path))
            if method=='POST' and path=='/api/v1/runs':
                body=b''
                while True:
                    event=await receive();body+=event.get('body',b'')
                    if len(body)>16000:return await reply(413,{'error':'Request too large.'})
                    if not event.get('more_body'):break
                try:harvester_request(json.loads(body))
                except (ValueError,TypeError):return await reply(400,{'error':'Only bounded passive P0 domain runs are permitted.'})
                async def replay():return {'type':'http.request','body':body,'more_body':False}
                return await upstream(scope,replay,send)
            if not allowed:return await reply(403,{'error':'Endpoint outside managed scope.'})
            return await upstream(scope,receive,send)
    import uvicorn
    uvicorn.run(Gate(),host='127.0.0.1',port=args.port,log_level='error',access_log=False,loop='asyncio',lifespan='on')

if __name__=='__main__':
    import multiprocessing
    multiprocessing.freeze_support();main()
