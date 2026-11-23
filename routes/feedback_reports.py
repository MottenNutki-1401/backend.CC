from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from services.feedback_reports import (
    FeedbackServiceError,
    artifact_path,
    create_job,
    get_job,
    process_job,
    run_connectivity_test,
    verify_model_access,
)


router = APIRouter(prefix="/feedback-reports", tags=["feedback-reports"])


@router.get("/configuration")
async def get_configuration():
    """Report safe configuration state; never return the key value."""
    try:
        result = verify_model_access()
        return result
    except FeedbackServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/connectivity-test")
async def connectivity_test():
    """Run one bounded sample feedback request; this may consume a few tokens."""
    try:
        return run_connectivity_test()
    except FeedbackServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/jobs", status_code=202)
async def start_report_job(data: dict, background_tasks: BackgroundTasks):
    try:
        job_id = create_job(
            data.get("assignment_title", "Writing Assignment"),
            data.get("texts"),
            data.get("files"),
            data.get("student_names"),
        )
    except FeedbackServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(process_job, job_id)
    return {
        "job_id": job_id,
        "status": "queued",
        "progress_url": "/feedback-reports/jobs/{}".format(job_id),
    }


@router.get("/jobs/{job_id}")
async def report_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Report job not found.")
    return job


@router.get("/jobs/{job_id}/download")
async def download_report_bundle(job_id: str):
    path = artifact_path(job_id, "zip")
    if not path:
        raise HTTPException(status_code=404, detail="Report bundle is not ready or was not found.")
    return FileResponse(path, filename="copycatch_feedback_reports.zip", media_type="application/zip")


@router.get("/jobs/{job_id}/teacher.pdf")
async def download_teacher_overview(job_id: str):
    path = artifact_path(job_id, "teacher_pdf")
    if not path:
        raise HTTPException(status_code=404, detail="Teacher overview is not ready or was not found.")
    return FileResponse(path, filename="teacher_overview.pdf", media_type="application/pdf")


@router.get("/jobs/{job_id}/summary.csv")
async def download_assessment_summary(job_id: str):
    path = artifact_path(job_id, "summary_csv")
    if not path:
        raise HTTPException(status_code=404, detail="Assessment summary is not ready or was not found.")
    return FileResponse(path, filename="assessment_summary.csv", media_type="text/csv")


@router.get("/jobs/{job_id}/students/{student_id}.pdf")
async def download_student_report(job_id: str, student_id: str):
    path = artifact_path(job_id, "student_pdf", student_id=student_id)
    if not path:
        raise HTTPException(status_code=404, detail="Student report is not ready or was not found.")
    return FileResponse(path, filename="student_feedback.pdf", media_type="application/pdf")
