from __future__ import annotations
import json
import subprocess
from .models import Advisory


class GHSAError(RuntimeError):
    pass


def create_draft(advisory: Advisory) -> str:
    """Create a GHSA draft in CobaltoSec/advisories and return the real ghsa_id."""
    description = advisory.notes or (
        f"Security vulnerability discovered in {advisory.package} via {advisory.source.value}."
    )
    payload: dict = {
        "summary": f"Security vulnerability in {advisory.package}",
        "description": description,
        "severity": advisory.severity,
        "vulnerabilities": [
            {
                "package": {
                    "name": advisory.package,
                    "ecosystem": advisory.ecosystem,
                },
                "vulnerable_version_range": ">= 0.0.1",
            }
        ],
    }
    if advisory.collaborators:
        payload["collaborating_users"] = advisory.collaborators

    result = subprocess.run(
        [
            "gh", "api", "repos/CobaltoSec/advisories/security-advisories",
            "-X", "POST", "-H", "Content-Type: application/json",
            "--input", "-",
        ],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise GHSAError(result.stderr.strip())

    data = json.loads(result.stdout)
    ghsa_id = data.get("ghsa_id")
    if not ghsa_id:
        raise GHSAError(f"Sin ghsa_id en respuesta: {result.stdout[:200]}")
    return ghsa_id
