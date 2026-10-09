from threading import Event, Thread

import pytest

from core.job_supervisor import JobStatus, JobSupervisor


@pytest.mark.parametrize("raises", [False, True])
def test_cancel_is_terminal_against_late_worker_completion(raises):
    supervisor = JobSupervisor()
    supervisor.submit("job-1")
    started = Event()
    release = Event()
    result = {}

    def worker():
        started.set()
        if not release.wait(timeout=3):
            raise TimeoutError("test_release_not_signalled")
        if raises:
            raise RuntimeError("late worker failure")
        return "late result"

    thread = Thread(target=lambda: result.setdefault("job", supervisor.run("job-1", worker)))
    thread.start()
    try:
        assert started.wait(timeout=2)
        cancelled = supervisor.cancel("job-1")
        assert cancelled.status is JobStatus.CANCELLED
    finally:
        release.set()
        thread.join(timeout=3)

    assert not thread.is_alive(), "worker thread did not terminate"
    assert result["job"].status is JobStatus.CANCELLED
    assert supervisor.get("job-1").status is JobStatus.CANCELLED
