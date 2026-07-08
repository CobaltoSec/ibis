from __future__ import annotations
import json
import subprocess
from pathlib import Path
import pytest
from ibis import db

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("ibis.db.DB_PATH", db_path)
    db.init_db()
    return db_path


@pytest.fixture
def no_npm(monkeypatch):
    monkeypatch.setattr("ibis.npm.get_weekly_downloads", lambda pkg: None)


@pytest.fixture
def npm_enterprise(monkeypatch):
    monkeypatch.setattr("ibis.npm.get_weekly_downloads", lambda pkg: 100_000)


@pytest.fixture
def condor_flowise_report(tmp_path):
    data = (FIXTURES / "condor_report_flowise.json").read_text()
    p = tmp_path / "report.json"
    p.write_text(data)
    return p


@pytest.fixture
def condor_empty_report(tmp_path):
    data = (FIXTURES / "condor_report_empty.json").read_text()
    p = tmp_path / "report_empty.json"
    p.write_text(data)
    return p


@pytest.fixture
def shrike_dir_two_findings(tmp_path):
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    for name in ["shrike_finding_with_ghsa.json", "shrike_finding_no_ghsa.json"]:
        data = (FIXTURES / name).read_text()
        (findings_dir / name).write_text(data)
    return findings_dir


@pytest.fixture
def shrike_dir_with_collaborator(tmp_path):
    findings_dir = tmp_path / "findings"
    findings_dir.mkdir()
    data = (FIXTURES / "shrike_finding_collaborator.json").read_text()
    (findings_dir / "finding.json").write_text(data)
    return findings_dir


@pytest.fixture
def mock_gh_api(monkeypatch):
    ghsa_payload = json.dumps([
        {
            "ghsa_id": "GHSA-test-0001-abcd",
            "severity": "high",
            "state": "draft",
            "published_at": "2026-01-01T00:00:00Z",
            "vulnerabilities": [
                {"package": {"name": "@microsoft/teams-ai", "ecosystem": "npm"}}
            ],
            "collaborating_users": [{"login": "testuser"}],
        }
    ])

    class FakeResult:
        returncode = 0
        stdout = ghsa_payload
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: FakeResult())
