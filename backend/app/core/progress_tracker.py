"""
Simple in-memory progress tracking for PDF processing jobs.

This provides a lightweight way to track progress without complex infrastructure.
For production, you might want to use Redis or a proper job queue.
"""
import time
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class ProgressData:
    """Progress data for a processing job."""
    job_id: str
    current: int = 0
    total: int = 0
    progress_percent: float = 0.0
    successful: int = 0
    errors: int = 0
    current_file: str = ""
    elapsed_time: float = 0.0
    estimated_remaining: Optional[float] = None
    status: str = "running"  # running, completed, failed
    last_updated: float = 0.0


class ProgressTracker:
    """Simple in-memory progress tracker."""
    
    def __init__(self):
        self._jobs: Dict[str, ProgressData] = {}
    
    def create_job(self) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = ProgressData(
            job_id=job_id,
            last_updated=time.time()
        )
        return job_id
    
    def update_progress(self, job_id: str, progress_data: Dict[str, Any]) -> None:
        """Update progress for a job."""
        if job_id not in self._jobs:
            return
        
        job = self._jobs[job_id]
        
        # Update fields from progress_data
        if 'current' in progress_data:
            job.current = progress_data['current']
        if 'total' in progress_data:
            job.total = progress_data['total']
        if 'progress_percent' in progress_data:
            job.progress_percent = progress_data['progress_percent']
        if 'successful' in progress_data:
            job.successful = progress_data['successful']
        if 'errors' in progress_data:
            job.errors = progress_data['errors']
        if 'current_file' in progress_data:
            job.current_file = progress_data['current_file']
        if 'elapsed_time' in progress_data:
            job.elapsed_time = progress_data['elapsed_time']
        if 'estimated_remaining' in progress_data:
            job.estimated_remaining = progress_data['estimated_remaining']
        
        job.last_updated = time.time()
    
    def get_progress(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current progress for a job."""
        if job_id not in self._jobs:
            return None
        
        job = self._jobs[job_id]
        return asdict(job)
    
    def complete_job(self, job_id: str, status: str = "completed") -> None:
        """Mark a job as completed."""
        if job_id in self._jobs:
            self._jobs[job_id].status = status
            self._jobs[job_id].last_updated = time.time()
    
    def cleanup_old_jobs(self, max_age_seconds: int = 3600) -> None:
        """Remove jobs older than max_age_seconds."""
        current_time = time.time()
        expired_jobs = [
            job_id for job_id, job in self._jobs.items()
            if current_time - job.last_updated > max_age_seconds
        ]
        
        for job_id in expired_jobs:
            del self._jobs[job_id]


# Global progress tracker instance
progress_tracker = ProgressTracker()
