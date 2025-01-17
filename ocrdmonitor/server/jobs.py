from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from fastapi import APIRouter, Depends, Request, Response
from fastapi.templating import Jinja2Templates

from ocrdmonitor.ocrdcontroller import OcrdController
from ocrdmonitor.processstatus import ProcessStatus
from ocrdmonitor.protocols import Environment, OcrdJob, Repositories


@dataclass
class RunningJob:
    ocrd_job: OcrdJob
    process_status: ProcessStatus


def split_into_running_and_completed(
    jobs: Iterable[OcrdJob],
) -> tuple[list[OcrdJob], list[OcrdJob]]:
    running_ocrd_jobs = [job for job in jobs if job.is_running]
    completed_ocrd_jobs = [job for job in jobs if job.is_completed]
    return running_ocrd_jobs, completed_ocrd_jobs


def wrap_in_running_job_type(
    running_ocrd_jobs: Iterable[OcrdJob],
    job_status: Iterable[ProcessStatus | None],
) -> Iterable[RunningJob]:
    running_jobs = [
        RunningJob(job, process_status)
        for job, process_status in zip(running_ocrd_jobs, job_status)
        if process_status is not None
    ]

    return running_jobs


def create_jobs(
    templates: Jinja2Templates,
    environment: Environment,
) -> APIRouter:
    router = APIRouter(prefix="/jobs")
    controller = OcrdController(environment.controller_server())

    @router.get("/", name="jobs")
    async def jobs(
        request: Request, repositories: Repositories = Depends(environment.repositories)
    ) -> Response:
        job_repository = repositories.ocrd_jobs
        jobs = await job_repository.find_all()
        running, completed = split_into_running_and_completed(jobs)

        job_status = [await controller.status_for(job) for job in running]
        running_jobs = wrap_in_running_job_type(running, job_status)

        now = datetime.now(timezone.utc)
        return templates.TemplateResponse(
            "jobs.html.j2",
            {
                "request": request,
                "running_jobs": sorted(
                    running_jobs,
                    key=lambda x: x.ocrd_job.time_created or now,
                ),
                "completed_jobs": sorted(
                    completed,
                    key=lambda x: x.time_terminated or now,
                ),
            },
        )

    return router
