from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ReviewIssueDetail(BaseModel):
    severity: str | None = None
    issue_type: str | None = None
    location: str | None = None
    fix_hint: str | None = None
    detail: dict[str, Any] | None = None


class ReviewReportSummary(BaseModel):
    path: str
    status: str
    issues: list[str | ReviewIssueDetail]


class ReviewSummary(BaseModel):
    course_id: str
    report_count: int
    issue_count: int
    reports: list[ReviewReportSummary]
