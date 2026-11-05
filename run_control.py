"""Thread-local run deadlines and provider budgets; never serialized as secrets."""
from contextvars import ContextVar
from contextlib import contextmanager
from http.client import HTTPResponse
import threading,time

CURRENT=ContextVar('vidocq_run_control',default=None)

class RunStopped(ValueError):pass

class RunControl:
    def __init__(self,seconds,cancelled,limit,index_depth=0,extra_snippets=False):
        self.deadline=time.monotonic()+seconds;self.cancelled=cancelled;self.limit=limit;self.counts={};self.lock=threading.Lock();self.index_depth=index_depth;self.extra_snippets=extra_snippets
    def remaining(self,maximum=30):
        if self.cancelled.is_set():raise RunStopped('Investigation cancelled before the next operation.')
        left=self.deadline-time.monotonic()
        if left<=0:raise RunStopped('Investigation deadline reached; partial evidence retained.')
        return max(.01,min(maximum,left))
    def reserve(self,provider):
        self.remaining()
        with self.lock:
            if self.counts.get(provider,0)>=self.limit:raise ValueError('Per-run request limit reached for '+provider+'.')
            self.counts[provider]=self.counts.get(provider,0)+1
    def status(self):return {'requests_by_provider':dict(self.counts),'per_provider_limit':self.limit,'requested_index_depth':self.index_depth,'extra_snippets':self.extra_snippets,'deadline_reached':time.monotonic()>=self.deadline,'notice':'Counts are external parent-app HTTP attempts, excluding loopback polling. Collector backends have separate bounded operations and may fan out. This is not a provider billing receipt.'}

def timeout(default=30):
    value=CURRENT.get();return value.remaining(default) if value else default

def reserve(provider):
    value=CURRENT.get()
    if value:value.reserve(provider)

@contextmanager
def cleanup_scope():
    """Allow only separately bounded cleanup calls after cancellation/deadline."""
    token=CURRENT.set(None)
    try:yield
    finally:CURRENT.reset(token)

def read_bounded(response,maximum):
    control=CURRENT.get()
    if not control or not isinstance(response,HTTPResponse):return response.read(maximum+1)
    chunks=[];received=0
    while received<=maximum:
        remaining=control.remaining(15)
        sock=getattr(getattr(getattr(response,'fp',None),'raw',None),'_sock',None)
        if sock:sock.settimeout(remaining)
        chunk=response.read1(min(65536,maximum+1-received))
        if not chunk:break
        chunks.append(chunk);received+=len(chunk)
    control.remaining()
    return b''.join(chunks)
