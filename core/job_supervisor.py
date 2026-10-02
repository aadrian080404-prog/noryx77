"""Bounded long-running job state machine with race-safe cancellation publication."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from threading import RLock
from time import monotonic
from typing import Callable, Any
class JobStatus(str,Enum): QUEUED="queued"; RUNNING="running"; SUCCEEDED="succeeded"; FAILED="failed"; CANCELLED="cancelled"
@dataclass(frozen=True)
class Job:
    job_id:str; status:JobStatus; created_at:float; attempts:int=0; result:Any=None; error:str|None=None
class JobSupervisor:
    def __init__(self,*,max_jobs:int=1024,max_attempts:int=3):
        if max_jobs<1 or max_attempts<1: raise ValueError("invalid_job_limits")
        self.max_jobs,self.max_attempts=max_jobs,max_attempts; self._jobs={}; self._lock=RLock()
    def submit(self,job_id:str)->Job:
        if not isinstance(job_id,str) or not job_id.strip(): raise ValueError("job_id_required")
        with self._lock:
            if job_id in self._jobs: raise ValueError("job_already_exists")
            if len(self._jobs)>=self.max_jobs: raise MemoryError("job_capacity_exceeded")
            j=Job(job_id,JobStatus.QUEUED,monotonic()); self._jobs[job_id]=j; return j
    def run(self,job_id:str,worker:Callable[[],Any])->Job:
        if not callable(worker): raise TypeError("worker_required")
        with self._lock:
            cur=self._jobs.get(job_id)
            if cur is None: raise KeyError("unknown_job")
            if cur.status not in (JobStatus.QUEUED,JobStatus.FAILED): raise RuntimeError("job_not_runnable")
            if cur.attempts>=self.max_attempts: raise RuntimeError("job_attempt_limit")
            running=Job(job_id,JobStatus.RUNNING,cur.created_at,cur.attempts+1); self._jobs[job_id]=running
        try: result=worker()
        except Exception as exc:
            failed=Job(job_id,JobStatus.FAILED,running.created_at,running.attempts,error=type(exc).__name__)
            with self._lock: self._jobs[job_id]=failed
            return failed
        done=Job(job_id,JobStatus.SUCCEEDED,running.created_at,running.attempts,result=result)
        with self._lock: self._jobs[job_id]=done
        return done
    def cancel(self,job_id:str)->Job:
        with self._lock:
            cur=self._jobs.get(job_id)
            if cur is None: raise KeyError("unknown_job")
            if cur.status in (JobStatus.SUCCEEDED,JobStatus.CANCELLED): return cur
            done=Job(job_id,JobStatus.CANCELLED,cur.created_at,cur.attempts); self._jobs[job_id]=done; return done
    def get(self,job_id:str)->Job|None:
        with self._lock: return self._jobs.get(job_id)
