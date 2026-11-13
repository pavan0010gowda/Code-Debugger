import os
import sys
import tempfile
import time
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class SandboxResult:
    """Structured result returned from executing code inside the isolated sandbox."""
    success: bool
    returncode: int
    stdout: str
    stderr: str
    execution_time_sec: float
    error_type: Optional[str] = None
    summary: str = ""


class CodeExecutionSandbox:
    """
    Isolated execution sandbox for running Python code and unit tests.
    Executes the snippet in a discrete temporary subprocess with strict timeouts.
    """

    def __init__(self, timeout_sec: int = 8):
        self.timeout_sec = timeout_sec

    def execute(self, code: str, test_code: Optional[str] = None) -> SandboxResult:
        """
        Execute Python code and optional test assertions in an isolated subprocess.
        
        Args:
            code: The source code / refactored code to test.
            test_code: Optional test suite (e.g. unittest or assert statements)
            
        Returns:
            SandboxResult with execution status, outputs, and runtime diagnostics.
        """
        full_script = code
        if test_code and test_code.strip():
            full_script = f"{code}\n\n# --- AUTOMATED TEST SUITE ---\n{test_code}"

        # Create a temporary file in a secure temp directory
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"sandbox_run_{int(time.time() * 1000)}.py")

        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(full_script)

            start_time = time.perf_counter()
            process = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=self.timeout_sec,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            elapsed = time.perf_counter() - start_time

            is_success = (process.returncode == 0)
            summary = "Execution completed successfully with zero errors." if is_success else f"Execution failed with exit code {process.returncode}."

            error_type = None
            if not is_success:
                stderr_lower = process.stderr.lower()
                if "assertionerror" in stderr_lower:
                    error_type = "AssertionError"
                elif "syntaxerror" in stderr_lower:
                    error_type = "SyntaxError"
                elif "zerodivisionerror" in stderr_lower:
                    error_type = "ZeroDivisionError"
                elif "indexerror" in stderr_lower:
                    error_type = "IndexError"
                elif "keyerror" in stderr_lower:
                    error_type = "KeyError"
                elif "typeerror" in stderr_lower:
                    error_type = "TypeError"
                elif "nameerror" in stderr_lower:
                    error_type = "NameError"
                else:
                    error_type = "RuntimeError"

            return SandboxResult(
                success=is_success,
                returncode=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                execution_time_sec=round(elapsed, 4),
                error_type=error_type,
                summary=summary
            )

        except subprocess.TimeoutExpired:
            return SandboxResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"TimeoutExpired: Execution exceeded safety threshold of {self.timeout_sec}s. Possible infinite loop.",
                execution_time_sec=float(self.timeout_sec),
                error_type="TimeoutExpired",
                summary=f"Execution timed out after {self.timeout_sec} seconds."
            )
        except Exception as ex:
            return SandboxResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=f"Sandbox system error: {str(ex)}",
                execution_time_sec=0.0,
                error_type=type(ex).__name__,
                summary=f"Sandbox failure: {str(ex)}"
            )
        finally:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass

