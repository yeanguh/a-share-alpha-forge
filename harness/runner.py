from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "harness" / "manifest.json"
DEFAULT_OUTPUT_DIR = ROOT / "tmp" / "harness"


@dataclass
class CheckResult:
    id: str
    name: str
    status: str
    duration_s: float
    detail: str = ""
    command: list[str] | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""


@dataclass
class HarnessReport:
    mode: str
    generated_at: str
    root: str
    summary: dict[str, int]
    capabilities: list[dict[str, Any]]
    results: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.summary.get("failed", 0) == 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["results"] = [asdict(result) for result in self.results]
        payload["ok"] = self.ok
        return payload


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        manifest = json.load(fh)
    if manifest.get("schema_version") != 1:
        raise ValueError(f"unsupported harness manifest schema: {manifest.get('schema_version')}")
    return manifest


def resolve(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def modes_for(requested: str) -> set[str]:
    if requested == "smoke":
        return {"smoke"}
    if requested == "full":
        return {"smoke", "full"}
    if requested == "web":
        return {"smoke", "web"}
    raise ValueError(f"unknown harness mode: {requested}")


def tail(text: str, limit: int = 4000) -> str:
    return text[-limit:] if len(text) > limit else text


def run_process(argv: list[str], timeout: int, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        env={**os.environ, "PYTHONUTF8": "1"},
    )


def check_paths(check: dict[str, Any], manifest: dict[str, Any]) -> CheckResult:
    started = time.time()
    paths = list(check.get("paths", []))
    if check.get("paths_from") == "capabilities":
        paths.extend(capability["path"] for capability in manifest["capabilities"])
        for capability in manifest["capabilities"]:
            if capability["type"].startswith("skill"):
                paths.append(str(Path(capability["path"]) / "SKILL.md"))
    missing = [path for path in paths if not resolve(path).exists()]
    status = "passed" if not missing else "failed"
    detail = "all required paths exist" if not missing else "missing: " + ", ".join(missing)
    return CheckResult(check["id"], check["name"], status, time.time() - started, detail)


def compile_paths(check: dict[str, Any], manifest: dict[str, Any]) -> CheckResult:
    started = time.time()
    paths = list(check.get("paths", []))
    if check.get("paths_from") == "capability_entrypoints":
        for capability in manifest["capabilities"]:
            paths.extend(path for path in capability.get("entrypoints", []) if path.endswith(".py"))
    unique_paths = sorted(dict.fromkeys(paths))
    failures: list[str] = []
    stdout = ""
    stderr = ""
    for path in unique_paths:
        target = resolve(path)
        if not target.exists():
            failures.append(f"{path}: missing")
            continue
        result = run_process([sys.executable, "-m", "py_compile", str(target)], timeout=30)
        stdout += result.stdout
        stderr += result.stderr
        if result.returncode != 0:
            failures.append(path)
    status = "passed" if not failures else "failed"
    detail = f"compiled {len(unique_paths)} python files" if not failures else "failed: " + ", ".join(failures)
    return CheckResult(
        check["id"],
        check["name"],
        status,
        time.time() - started,
        detail,
        command=[sys.executable, "-m", "py_compile"],
        stdout_tail=tail(stdout),
        stderr_tail=tail(stderr),
    )


def command_check(check: dict[str, Any]) -> CheckResult:
    started = time.time()
    argv = list(check["argv"])
    try:
        result = run_process(argv, timeout=int(check.get("timeout_seconds", 120)), cwd=resolve(check.get("cwd", ".")))
        status = "passed" if result.returncode == 0 else "failed"
        detail = f"exit={result.returncode}"
        return CheckResult(
            check["id"],
            check["name"],
            status,
            time.time() - started,
            detail,
            command=argv,
            stdout_tail=tail(result.stdout),
            stderr_tail=tail(result.stderr),
        )
    except subprocess.TimeoutExpired as exc:
        return CheckResult(
            check["id"],
            check["name"],
            "failed",
            time.time() - started,
            f"timed out after {exc.timeout}s",
            command=argv,
            stdout_tail=tail(exc.stdout or ""),
            stderr_tail=tail(exc.stderr or ""),
        )


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((host, port)) == 0


def fetch_json(url: str, timeout: float = 5) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def workbench_check(check: dict[str, Any]) -> CheckResult:
    started = time.time()
    port = int(check.get("port", 8878))
    timeout = int(check.get("timeout_seconds", 45))
    base = f"http://127.0.0.1:{port}"
    proc: subprocess.Popen[str] | None = None
    command = [
        sys.executable,
        "scripts/stock_workbench.py",
        "--port",
        str(port),
        "--no-deps",
        "--no-vibe",
    ]
    try:
        if not is_port_open(port):
            proc = subprocess.Popen(
                command,
                cwd=str(ROOT),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "PYTHONUTF8": "1"},
            )
            deadline = time.time() + timeout
            while time.time() < deadline and not is_port_open(port):
                if proc.poll() is not None:
                    stdout, stderr = proc.communicate(timeout=1)
                    return CheckResult(
                        check["id"],
                        check["name"],
                        "failed",
                        time.time() - started,
                        f"workbench exited early with {proc.returncode}",
                        command=command,
                        stdout_tail=tail(stdout),
                        stderr_tail=tail(stderr),
                    )
                time.sleep(0.2)
        failures = []
        for endpoint in check.get("endpoints", []):
            try:
                fetch_json(base + endpoint)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{endpoint}: {exc}")
        status = "passed" if not failures else "failed"
        detail = "all workbench endpoints returned JSON" if not failures else "; ".join(failures)
        return CheckResult(check["id"], check["name"], status, time.time() - started, detail, command=command)
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def run_check(check: dict[str, Any], manifest: dict[str, Any]) -> CheckResult:
    check_type = check["type"]
    if check_type == "paths":
        return check_paths(check, manifest)
    if check_type == "py_compile":
        return compile_paths(check, manifest)
    if check_type == "command":
        return command_check(check)
    if check_type == "workbench":
        return workbench_check(check)
    raise ValueError(f"unknown check type: {check_type}")


def selected_checks(manifest: dict[str, Any], mode: str, only: set[str] | None = None) -> list[dict[str, Any]]:
    requested_modes = modes_for(mode)
    checks = []
    for check in manifest.get("checks", []):
        if only and check["id"] not in only:
            continue
        if requested_modes.intersection(check.get("modes", [])):
            checks.append(check)
    return checks


def run_harness(mode: str, *, checks: set[str] | None = None, manifest_path: Path = DEFAULT_MANIFEST) -> HarnessReport:
    manifest = load_manifest(manifest_path)
    results = [run_check(check, manifest) for check in selected_checks(manifest, mode, checks)]
    summary = {
        "passed": sum(result.status == "passed" for result in results),
        "failed": sum(result.status == "failed" for result in results),
        "skipped": sum(result.status == "skipped" for result in results),
        "total": len(results),
    }
    return HarnessReport(
        mode=mode,
        generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        root=str(ROOT),
        summary=summary,
        capabilities=manifest["capabilities"],
        results=results,
    )


def render_markdown(report: HarnessReport) -> str:
    lines = [
        f"# Harness Report: {report.mode}",
        "",
        f"- Generated: {report.generated_at}",
        f"- Root: `{report.root}`",
        f"- Passed: {report.summary['passed']}",
        f"- Failed: {report.summary['failed']}",
        f"- Total: {report.summary['total']}",
        "",
        "## Checks",
        "",
        "| Check | Status | Duration | Detail |",
        "| --- | --- | ---: | --- |",
    ]
    for result in report.results:
        detail = result.detail.replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{result.id}` | {result.status} | {result.duration_s:.2f}s | {detail} |")
    lines.extend(["", "## Capabilities", "", "| Capability | Type | Path |", "| --- | --- | --- |"])
    for capability in report.capabilities:
        lines.append(f"| `{capability['id']}` | {capability['type']} | `{capability['path']}` |")
    lines.append("")
    return "\n".join(lines)


def write_report(report: HarnessReport, output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"harness_{report.mode}_{stamp}.json"
    md_path = output_dir / f"harness_{report.mode}_{stamp}.md"
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    latest_json = output_dir / f"harness_{report.mode}_latest.json"
    latest_md = output_dir / f"harness_{report.mode}_latest.md"
    latest_json.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_md.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    return json_path, md_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run repository harness checks.")
    parser.add_argument("--mode", choices=("smoke", "full", "web"), default="smoke")
    parser.add_argument("--check", action="append", default=[], help="Run only the named check id. May be repeated.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--list", action="store_true", help="List capabilities and checks without running them.")
    parser.add_argument("--allow-failures", action="store_true", help="Always exit 0 after writing the report.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    manifest_path = resolve(args.manifest)
    manifest = load_manifest(manifest_path)
    if args.list:
        print(json.dumps({"capabilities": manifest["capabilities"], "checks": manifest["checks"]}, ensure_ascii=False, indent=2))
        return 0
    report = run_harness(args.mode, checks=set(args.check) or None, manifest_path=manifest_path)
    json_path, md_path = write_report(report, resolve(args.output_dir))
    print(f"harness mode={report.mode} passed={report.summary['passed']} failed={report.summary['failed']} total={report.summary['total']}")
    print(f"json={json_path.relative_to(ROOT)}")
    print(f"markdown={md_path.relative_to(ROOT)}")
    for result in report.results:
        print(f"{result.status.upper():7} {result.id} {result.duration_s:.2f}s {result.detail}")
    if not report.ok and not args.allow_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
