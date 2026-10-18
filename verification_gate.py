"""Verification gate for STACY results and critical state transitions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    status: str
    checks: dict[str, bool]
    issues: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "checks": dict(self.checks),
            "issues": list(self.issues),
            "evidence": list(self.evidence),
        }


def verify_result(result: Any) -> VerificationResult:
    """Validate the minimum CORE response contract before confirmation."""
    checks = {
        "result_is_dict": isinstance(result, dict),
        "type_valid": False,
        "response_nonempty": False,
        "sources_valid": True,
    }
    issues: list[str] = []
    evidence: list[str] = []

    if not isinstance(result, dict):
        return VerificationResult(False, "invalid", checks, ["resultado não é um objeto"], evidence)

    result_type = result.get("tipo")
    response = result.get("resposta")
    checks["type_valid"] = isinstance(result_type, str) and bool(result_type.strip())
    checks["response_nonempty"] = isinstance(response, str) and bool(response.strip())

    if not checks["type_valid"]:
        issues.append("tipo de resultado ausente ou inválido")
    if not checks["response_nonempty"]:
        issues.append("resposta vazia")

    sources = result.get("fontes")
    if sources is not None:
        if not isinstance(sources, list):
            checks["sources_valid"] = False
            issues.append("fontes não são uma lista")
        else:
            for source in sources:
                if not isinstance(source, dict) or not isinstance(source.get("url"), str) or not source["url"].strip():
                    checks["sources_valid"] = False
                    issues.append("fonte sem URL válida")
                    break

    if checks["response_nonempty"]:
        evidence.append("resposta não vazia")
    if checks["sources_valid"]:
        evidence.append("metadados de fontes válidos")

    ok = all(checks.values())
    return VerificationResult(ok, "verified" if ok else "failed", checks, issues, evidence)


def run_with_verification(operation: Callable[[], Any]) -> tuple[Any, VerificationResult]:
    """Run a callable and convert exceptions into an explicit failed state."""
    try:
        result = operation()
    except Exception as exc:  # verification boundary must not leak crashes
        report = VerificationResult(
            False,
            "exception",
            {"operation_completed": False},
            [f"{type(exc).__name__}: {exc}"],
            [],
        )
        return None, report
    return result, verify_result(result)
