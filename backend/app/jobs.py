"""In-memory ingest job tracker (status, progress, active jobs)."""
import os
import time
from typing import Any, Dict, List

# Global timeout per ingest job — jobs running longer are marked failed on status read.
INGEST_TIMEOUT_SECONDS = int(os.getenv("INGEST_TIMEOUT_SECONDS", 600))

# In-memory job tracker for background ingest tasks
_ingest_jobs: Dict[str, Dict[str, Any]] = {}

# Track active ingest jobs per collection (collection -> list of active job_ids)
_active_collection_ingests: Dict[str, List[str]] = {}


def _get_collection_active_ingests(collection_name: str) -> List[Dict[str, Any]]:
    """Get all active ingest jobs for a collection."""
    if collection_name not in _active_collection_ingests:
        return []

    active_jobs = []
    for job_id in _active_collection_ingests[collection_name][:]:  # copy to avoid iteration issues
        job_info = _get_job_status(job_id)
        if job_info.get("status") in ["pending", "running"]:
            active_jobs.append(job_info)
        else:
            # Remove completed/failed jobs from active list
            _active_collection_ingests[collection_name].remove(job_id)

    return active_jobs


def _get_job_status(job_id: str) -> Dict[str, Any]:
    """Get status of a background ingest job."""
    if job_id not in _ingest_jobs:
        return {"status": "not_found"}
    job = _ingest_jobs[job_id]
    # Safety net: if job is still marked as running but has exceeded the global
    # ingest timeout since creation, mark it as failed here so that callers
    # never see an endlessly running job.
    try:
        if job.get("status") == "running":
            created_at = job.get("created_at")
            # Legacy jobs without created_at are treated as stale and failed
            if created_at is None:
                created_at = time.time() - (INGEST_TIMEOUT_SECONDS + 1)
                job["created_at"] = created_at
            elapsed = time.time() - created_at
            if elapsed > INGEST_TIMEOUT_SECONDS:
                msg = (
                    f"Ingest job {job_id} exceeded {INGEST_TIMEOUT_SECONDS} "
                    f"seconds (actual ~{int(elapsed)}s); marking as failed by status check"
                )
                job["status"] = "failed"
                job["error"] = msg
                if "progress" in job and isinstance(job["progress"], dict):
                    job["progress"]["message"] = msg
    except Exception:
        # Never let status retrieval fail because of this safety logic.
        pass
    return job


def _create_job(job_id: str, mode: str, target: str, collection: str = None) -> None:
    """Initialize a new ingest job."""
    _ingest_jobs[job_id] = {
        "status": "pending",
        "mode": mode,  # "url", "urls", or "crawl"
        "target": target,  # URL or list representation
        "collection": collection,  # Collection name for this job
        "created_at": time.time(),  # for safety timeout in status endpoint
        "progress": {
            "pages_fetched": 0,
            "chunks_extracted": 0,
            "embeddings_created": 0,
            "points_upserted": 0,
            "message": "Pending"
        },
        "error": None,
        "result": None
    }

    # Track active ingests per collection
    if collection and collection not in _active_collection_ingests:
        _active_collection_ingests[collection] = []
    if collection:
        _active_collection_ingests[collection].append(job_id)
