# Copyright (c) 2026 ApeironAILab
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/ApeironAILab/OpenAGI

"""
core/sandbox.py — Secure subprocess REPL for LLM-generated code execution

REQUIREMENT: All LLM-generated code must run in isolated subprocess, NOT exec().

Safety features:
- subprocess.run with timeout (hard kill)
- stdout/stderr capture
- Disallowed import blocking
- Max output truncation
- Isolated working directory
"""
import subprocess
import sys
import tempfile
import os
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Any

log = logging.getLogger("SecureSandbox")

# Modules that are blocked from import in sandboxed code
DEFAULT_BLOCKED_IMPORTS = {
    'os.system', 'os.popen', 'subprocess', 'pty', 'shlex',
    'socket', 'urllib.request', 'http.client', 'ftplib',
    'shutil.rmtree', 'shutil.move', 'shutil.copy',
    '__import__', 'eval', 'exec', 'compile',
    'importlib', 'pkgutil', 'site', 'sysconfig',
}

# Safe stdlib modules allowed
ALLOWED_MODULES = {
    'json', 're', 'math', 'random', 'datetime', 'itertools',
    'collections', 'typing', 'dataclasses', 'enum', 'pathlib',
    'functools', 'operator', 'statistics', 'hashlib', 'string',
    'textwrap', 'unicodedata', 'decimal', 'fractions', 'numbers',
    'abc', 'inspect', 'types', 'copy', 'pprint', 'csv',
}


class SecureSandbox:
    """
    Run Python code in an isolated subprocess.

    Security model:
    - Process isolation via subprocess
    - Timeout enforcement
    - Output limits
    - Import restrictions via import hooks
    - No stdin, no network,
    """

    def __init__(
        self,
        timeout: int = 15,
        max_output: int = 10000,
        max_errors: int = 5000,
        allowed_imports: Optional[set] = None,
        blocked_imports: Optional[set] = None,
        work_dir: str = "./workspace/sandbox"
    ):
        self.timeout = timeout
        self.max_output = max_output
        self.max_errors = max_errors
        self.allowed_imports = allowed_imports or ALLOWED_MODULES
        self.blocked_imports = blocked_imports or DEFAULT_BLOCKED_IMPORTS
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self._debug_log = Path("./workspace/debug_log.md")
        self._debug_log.parent.mkdir(parents=True, exist_ok=True)

    def _generate_safety_header(self) -> str:
        """Generate safety header that blocks dangerous imports."""
        blocked_list = repr(list(self.blocked_imports))
        header = f'''
import sys
import builtins
import os

_BLOCKED_IMPORTS = set({blocked_list})
_original_import = builtins.__import__

def _restricted_import(name, *args, **kwargs):
    if name in _BLOCKED_IMPORTS or any(b in name.split('.') for b in ['subprocess', 'socket', 'urllib', 'http', 'ftplib', 'smtplib']):
        raise ImportError(f"Import '{{name}}' is blocked in sandbox")
    return _original_import(name, *args, **kwargs)

# Replace import
builtins.__import__ = _restricted_import

# Original code follows:
'''
        return header

    def _extract_imports(self, code: str) -> List[str]:
        """Extract import statements from code for validation."""
        imports = []
        # Match 'import X' and 'from X import Y'
        import_pattern = r'^(?:from\s+([\w.]+)|import\s+([\w.,\s]+))'
        for line in code.split('\n'):
            line = line.strip()
            m = re.match(import_pattern, line)
            if m:
                if m.group(1):  # from X import
                    imports.append(m.group(1).split('.')[0])
                elif m.group(2):  # import X, Y
                    for mod in m.group(2).replace(' ', '').split(','):
                        imports.append(mod.split('.')[0])
        return imports

    def _is_code_safe(self, code: str) -> tuple[bool, str]:
        """Pre-flight safety check on code."""
        # Check for dangerous patterns
        dangerous_patterns = [
            (r'os\.system\s*\(', 'os.system call detected'),
            (r'subprocess\.', 'subprocess usage detected'),
            (r'socket\.', 'socket usage detected'),
            (r'__import__\s*\(', 'dynamic import detected'),
            (r'eval\s*\(', 'eval() detected'),
            (r'exec\s*\(', 'exec() detected'),
            (r'open\s*\([\'"]\s*/', 'absolute path file access'),
        ]

        for pattern, reason in dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Security violation: {reason}"

        # Check imports
        imports = self._extract_imports(code)
        for imp in imports:
            if imp in self.blocked_imports:
                return False, f"Import '{imp}' is blocked"

        return True, ""

    def run(
        self,
        code: str,
        timeout: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute Python code in isolated subprocess.

        Args:
            code: Python code to execute
            timeout: Override default timeout (seconds)
            context: Variables to inject into execution context

        Returns:
            {
                success: bool,
                stdout: str,
                stderr: str,
                exit_code: int,
                timeout_hit: bool,
                truncated: bool
            }
        """
        timeout = timeout or self.timeout

        # Pre-flight check
        is_safe, reason = self._is_code_safe(code)
        if not is_safe:
            return {
                'success': False,
                'stdout': '',
                'stderr': f"[SANDBOX] {reason}",
                'exit_code': -1,
                'timeout_hit': False,
                'blocked': True
            }

        # Prepare code with safety header and context
        full_code = self._generate_safety_header()

        # Inject context variables
        if context:
            full_code += f"\n# Injected context\n"
            for key, value in context.items():
                if isinstance(value, str):
                    # Escape quotes
                    escaped = value.replace('"', '\\"').replace("'", "\\'")
                    full_code += f'{key} = "{escaped}"\n'
                elif isinstance(value, (int, float, bool)):
                    full_code += f'{key} = {value}\n'
                else:
                    full_code += f'{key} = {repr(value)}\n'

        full_code += f"\n# --- User Code ---\n{code}\n"

        # Write to temp file
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                suffix='.py',
                delete=False,
                mode='w',
                encoding='utf-8',
                dir=self.work_dir
            ) as f:
                f.write(full_code)
                tmp_path = Path(f.name)

            log.debug(f"[SANDBOX] Executing: {tmp_path.name}")

            # Run in subprocess
            result = subprocess.run(
                [sys.executable, str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.work_dir,
                env={
                    **os.environ,
                    'PYTHONPATH': str(self.work_dir),
                    'PYTHONDONTWRITEBYTECODE': '1',
                }
            )

            stdout = result.stdout[:self.max_output] if len(result.stdout) > self.max_output else result.stdout
            stderr = result.stderr[:self.max_errors] if len(result.stderr) > self.max_errors else result.stderr
            truncated = len(result.stdout) > self.max_output

            outcome = {
                'success': result.returncode == 0,
                'stdout': stdout,
                'stderr': stderr,
                'exit_code': result.returncode,
                'timeout_hit': False,
                'truncated': truncated,
                'blocked': False
            }

            # Log execution
            self._log_execution(code, outcome)

            return outcome

        except subprocess.TimeoutExpired as e:
            stdout = e.stdout[:self.max_output] if e.stdout else ''
            stderr = (e.stderr[:self.max_errors] if e.stderr else '') + "\n[SANDBOX] TIMEOUT"
            outcome = {
                'success': False,
                'stdout': stdout,
                'stderr': stderr,
                'exit_code': -1,
                'timeout_hit': True,
                'truncated': False,
                'blocked': False
            }
            self._log_execution(code, outcome)
            return outcome

        except Exception as e:
            outcome = {
                'success': False,
                'stdout': '',
                'stderr': f"[SANDBOX] Internal error: {str(e)}",
                'exit_code': -1,
                'timeout_hit': False,
                'blocked': False
            }
            self._log_execution(code, outcome)
            return outcome

        finally:
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def _log_execution(self, code: str, outcome: Dict[str, Any]) -> None:
        """Log sandbox execution to debug file."""
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        entry = f"""\n---
**Timestamp:** {timestamp}
**Success:** {outcome.get('success')}
**Exit Code:** {outcome.get('exit_code')}
**Timeout:** {outcome.get('timeout_hit')}
**Blocked:** {outcome.get('blocked', False)}

**Code:**
```python
{code[:500]}
```

**Stderr:**
```
{outcome.get('stderr', 'N/A')[:500]}
```
---
"""
        try:
            with open(self._debug_log, 'a', encoding='utf-8') as f:
                f.write(entry)
        except Exception as e:
            log.debug(f"Failed to write debug log: {e}")

    def attempt_fix(
        self,
        code: str,
        error: str,
        llm_fix_func,
        max_retries: int = 3,
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        On error, attempt to fix code with LLM.

        Args:
            code: Original failing code
            error: Error message from run()
            llm_fix_func: Function that takes (code, error) and returns fixed code
            max_retries: Max retry attempts
            timeout: Per-execution timeout

        Returns:
            Final outcome dict
        """
        current_code = code

        for attempt in range(max_retries):
            log.info(f"[SANDBOX] Auto-fix attempt {attempt + 1}/{max_retries}")

            try:
                current_code = llm_fix_func(current_code, error)
                if not current_code:
                    break
            except Exception as e:
                log.error(f"[SANDBOX] LLM fix failed: {e}")
                break

            outcome = self.run(current_code, timeout=timeout)
            if outcome['success']:
                return {**outcome, 'fixed': True, 'attempts': attempt + 1}

            error = outcome['stderr']

        return {
            'success': False,
            'stdout': '',
            'stderr': f"Failed after {max_retries} fix attempts. Last error: {error[:500]}",
            'exit_code': -1,
            'fixed': False,
            'attempts': max_retries
        }


# Singleton for reuse
_sandbox: Optional[SecureSandbox] = None


def get_sandbox() -> SecureSandbox:
    """Get or create sandbox singleton."""
    global _sandbox
    if _sandbox is None:
        _sandbox = SecureSandbox()
    return _sandbox
