from __future__ import annotations
import json
import subprocess
import pytest
from ibis import resolver


def test_resolve_repo_from_map():
    assert resolver.resolve_repo("flowise") == "FlowiseAI/Flowise"


def test_resolve_repo_owner_slash_format():
    assert resolver.resolve_repo("langgenius/dify") == "langgenius/dify"


def test_resolve_repo_explicit_overrides_map(monkeypatch):
    result = resolver.resolve_repo("flowise", explicit="my-org/my-fork")
    assert result == "my-org/my-fork"


def test_resolve_repo_unknown_returns_none():
    assert resolver.resolve_repo("completamente-desconocido-xyz") is None


def test_resolve_top_contributor_happy_path(monkeypatch):
    response = json.dumps([{"login": "topdev", "contributions": 500}])

    class FakeResult:
        returncode = 0
        stdout = response
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    assert resolver.resolve_top_contributor("FlowiseAI/Flowise") == "topdev"


def test_resolve_top_contributor_api_error_returns_none(monkeypatch):
    class FakeResult:
        returncode = 1
        stdout = ""
        stderr = "Not Found"

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: FakeResult())
    assert resolver.resolve_top_contributor("nonexistent/repo") is None
