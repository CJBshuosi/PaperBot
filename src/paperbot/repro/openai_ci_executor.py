from __future__ import annotations

"""
OpenAI Code Interpreter Executor using the Assistants API.

Uses OpenAI's Assistants API with Code Interpreter tool to execute
Python code in a secure sandbox environment.
"""

import json
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

from paperbot.infrastructure.logging.execution_logger import ExecutionLogger
from paperbot.repro.execution_result import ExecutionResult

try:
    from openai import OpenAI  # type: ignore
except Exception as exc:  # pragma: no cover - import guard
    OpenAI = None  # type: ignore
    _OPENAI_IMPORT_ERROR = exc
else:
    _OPENAI_IMPORT_ERROR = None


_IGNORE_DIRS = {
    ".git",
    ".next",
    "node_modules",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}


def _load_openai_key_from_endpoints() -> Tuple[Optional[str], Optional[str]]:
    """Try to load OpenAI API key from model endpoints store.

    Returns:
        Tuple of (api_key, base_url)
    """
    try:
        from paperbot.infrastructure.stores.model_endpoint_store import ModelEndpointStore
        store = ModelEndpointStore(auto_create_schema=False)
        endpoints = store.list_endpoints(enabled_only=True, include_secrets=True)
        for ep in endpoints:
            if ep.get("vendor") == "openai" and ep.get("api_key"):
                key = ep["api_key"]
                if key and not key.startswith("***"):
                    base_url = ep.get("base_url")
                    store.close()
                    return key, base_url
        store.close()
    except Exception:
        pass
    return None, None


def _openai_client() -> Tuple["OpenAI", str, Optional[str]]:
    if OpenAI is None:
        raise RuntimeError("openai library not installed") from _OPENAI_IMPORT_ERROR

    # Try environment variable first
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    # If not in env or is OpenRouter key, try model endpoints
    if not api_key or api_key.startswith("sk-or-"):
        endpoint_key, endpoint_base_url = _load_openai_key_from_endpoints()
        if endpoint_key and not endpoint_key.startswith("sk-or-"):
            api_key = endpoint_key
            base_url = endpoint_base_url

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    # Check for OpenRouter keys - they won't work with Assistants API
    if api_key.startswith("sk-or-"):
        raise RuntimeError(
            "OpenRouter API keys (sk-or-...) don't support OpenAI Assistants API. "
            "Code Interpreter requires a direct OpenAI API key (sk-proj-... or sk-...). "
            "Configure a direct OpenAI key in Settings > Model Endpoints."
        )

    # Don't use custom base_url for OpenAI - it breaks the Assistants API
    # The standard OpenAI base URL is handled automatically by the SDK
    if base_url and "api.openai.com" in base_url:
        base_url = None  # Let SDK use default

    # Force remove OPENAI_BASE_URL from env to prevent SDK from using it
    # This is important when the env has a different base_url than what we want
    env_base_url = os.environ.pop("OPENAI_BASE_URL", None)

    if base_url:
        client = OpenAI(api_key=api_key, base_url=base_url)
    else:
        client = OpenAI(api_key=api_key)

    # Restore env var if it was set (for other code that might need it)
    if env_base_url:
        os.environ["OPENAI_BASE_URL"] = env_base_url

    return client, api_key, base_url


def _zip_project(root: Path, dest: Path) -> int:
    """Zip a project directory, excluding common non-essential directories."""
    if dest.exists():
        dest.unlink()
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
            for name in filenames:
                path = Path(dirpath) / name
                rel = os.path.relpath(path, root)
                zf.write(path, rel)
    return dest.stat().st_size


def _build_runner_code(commands: List[str]) -> str:
    """Build Python code that the assistant will execute."""
    commands_json = json.dumps(commands)
    return f'''
import subprocess
import sys
import os

# Change to /mnt/data where uploaded files are stored
os.chdir("/mnt/data")

# Check if project.zip exists and extract it
import zipfile
if os.path.exists("project.zip"):
    print("Extracting project.zip...")
    with zipfile.ZipFile("project.zip", "r") as zf:
        zf.extractall("project")
    os.chdir("project")
    print(f"Working directory: {{os.getcwd()}}")
    print(f"Files: {{os.listdir('.')}}")

commands = {commands_json}

final_exit_code = 0
for cmd in commands:
    print(f"\\n=== Running: {{cmd}} ===")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(f"[stderr] {{result.stderr}}")
    print(f"[exit_code: {{result.returncode}}]")
    if result.returncode != 0:
        final_exit_code = result.returncode
        break

print(f"\\n=== FINAL_EXIT_CODE: {{final_exit_code}} ===")
'''


class OpenAICodeInterpreterExecutor:
    """
    Execute code using OpenAI's Assistants API with Code Interpreter.

    This uses the official Assistants API which provides a secure
    Python execution environment with file upload/download support.
    """

    def __init__(self, *, model: str = "gpt-4o"):
        self.model = model
        self.max_zip_bytes = int(os.getenv("PAPERBOT_CI_MAX_ZIP_BYTES", "50000000"))  # 50MB

    def run(
        self,
        workdir: Path,
        commands: List[str],
        *,
        run_id: str,
        logger: ExecutionLogger,
        timeout_sec: int = 300,
    ) -> ExecutionResult:
        """
        Execute commands in OpenAI Code Interpreter sandbox.

        Args:
            workdir: Directory containing code to execute
            commands: List of shell commands to run
            run_id: Unique run identifier for logging
            logger: ExecutionLogger instance
            timeout_sec: Maximum execution time

        Returns:
            ExecutionResult with status, logs, and exit code
        """
        start = time.time()

        if not workdir.exists() or not workdir.is_dir():
            return ExecutionResult(status="error", exit_code=1, error="project_dir not found")

        try:
            client, api_key, base_url = _openai_client()
            logger.log(run_id, "info", f"[v4] Using OpenAI API (key: {api_key[:20]}..., base_url={base_url})", source="system")
        except RuntimeError as e:
            return ExecutionResult(status="error", exit_code=1, error=str(e))

        tmp_dir = Path(tempfile.mkdtemp(prefix="paperbot-ci-"))
        zip_path = tmp_dir / "project.zip"
        assistant_id = None
        thread_id = None
        file_id = None

        try:
            # Zip the project
            size = _zip_project(workdir, zip_path)
            if size > self.max_zip_bytes:
                return ExecutionResult(
                    status="error",
                    exit_code=1,
                    error=f"project zip too large: {size} bytes (max: {self.max_zip_bytes})",
                )

            logger.log(run_id, "info", f"Uploading project ({size} bytes)", source="system")

            # Upload the project zip file
            try:
                with open(zip_path, "rb") as f:
                    file_response = client.files.create(file=f, purpose="assistants")
                    file_id = file_response.id
                logger.log(run_id, "info", f"File uploaded: {file_id}", source="system")
            except Exception as upload_err:
                logger.log(run_id, "error", f"File upload failed: {upload_err}", source="system")
                raise

            # Create an assistant with code interpreter
            try:
                assistant = client.beta.assistants.create(
                    name=f"PaperBot Runner {run_id}",
                    instructions=(
                        "You are a code execution assistant. Execute the provided Python code exactly as given. "
                        "Do not explain, just run the code and show the output."
                    ),
                    model=self.model,
                    tools=[{"type": "code_interpreter"}],
                )
                assistant_id = assistant.id
                logger.log(run_id, "info", f"Assistant created: {assistant_id}", source="system")
            except Exception as asst_err:
                logger.log(run_id, "error", f"Assistant creation failed: {asst_err}", source="system")
                raise

            # Create a thread with the file attached
            thread = client.beta.threads.create(
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Run the following Python code exactly. Show ALL output including print statements.\n\n"
                            "```python\n"
                            + _build_runner_code(commands)
                            + "\n```"
                        ),
                        "attachments": [
                            {
                                "file_id": file_id,
                                "tools": [{"type": "code_interpreter"}]
                            }
                        ]
                    }
                ]
            )
            thread_id = thread.id
            logger.log(run_id, "info", f"Thread created: {thread_id}", source="system")

            # Run the assistant
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id,
            )

            # Poll for completion
            poll_interval = 2
            deadline = time.time() + timeout_sec
            while True:
                if time.time() > deadline:
                    # Try to cancel the run
                    try:
                        client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
                    except Exception:
                        pass
                    return ExecutionResult(
                        status="failed",
                        exit_code=1,
                        error=f"Timeout after {timeout_sec}s",
                        duration_sec=time.time() - start,
                    )

                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                status = run.status

                if status == "completed":
                    break
                elif status in ("failed", "cancelled", "expired"):
                    error_msg = getattr(run, "last_error", None)
                    if error_msg:
                        error_msg = str(error_msg)
                    else:
                        error_msg = f"Run {status}"
                    return ExecutionResult(
                        status="error",
                        exit_code=1,
                        error=error_msg,
                        duration_sec=time.time() - start,
                    )
                elif status == "requires_action":
                    # This shouldn't happen for code interpreter, but handle it
                    return ExecutionResult(
                        status="error",
                        exit_code=1,
                        error="Run requires action (unexpected for code interpreter)",
                        duration_sec=time.time() - start,
                    )

                time.sleep(poll_interval)

            # Get the messages from the thread
            messages = client.beta.threads.messages.list(thread_id=thread_id, order="asc")

            output_text = ""
            for msg in messages.data:
                if msg.role == "assistant":
                    for content in msg.content:
                        if content.type == "text":
                            output_text += content.text.value + "\n"

            # Log the output
            for line in output_text.splitlines():
                if line.strip():
                    logger.log(run_id, "info", line, source="stdout")

            # Parse exit code from output
            exit_code = 0
            for line in output_text.splitlines():
                if "FINAL_EXIT_CODE:" in line:
                    try:
                        exit_code = int(line.split("FINAL_EXIT_CODE:")[1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass
                    break

            status = "success" if exit_code == 0 else "failed"
            duration = time.time() - start

            return ExecutionResult(
                status=status,
                exit_code=exit_code,
                duration_sec=duration,
                logs=output_text,
            )

        except Exception as exc:
            logger.log(run_id, "error", f"Code Interpreter failed: {exc}", source="system")
            return ExecutionResult(
                status="error",
                exit_code=1,
                error=str(exc),
                duration_sec=time.time() - start,
            )

        finally:
            # Cleanup: delete assistant, thread, and file
            if client:
                if assistant_id:
                    try:
                        client.beta.assistants.delete(assistant_id)
                    except Exception:
                        pass
                if thread_id:
                    try:
                        client.beta.threads.delete(thread_id)
                    except Exception:
                        pass
                if file_id:
                    try:
                        client.files.delete(file_id)
                    except Exception:
                        pass
            shutil.rmtree(tmp_dir, ignore_errors=True)
