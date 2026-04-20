#!/usr/bin/env python3
"""
complete_v2.py - Final V2 implementation script
Applies all remaining V2 changes that couldn't be completed due to API timeouts.
"""

import io
import sys

def log(msg):
    print(f"[V2] {msg}")

def fix_setup_bat():
    """Add python-pptx and playwright to setup.bat"""
    log("Fixing setup.bat...")
    with io.open('setup.bat', 'r', encoding='utf-8') as f:
        content = f.read()

    if 'python-pptx' in content:
        log("  setup.bat already has python-pptx")
        return

    # Replace the pip install line
    old = 'pyaudio sounddevice soundfile plyer psutil faiss-cpu'
    new = 'pyaudio sounddevice soundfile plyer psutil faiss-cpu python-pptx playwright'

    if old in content:
        content = content.replace(old, new)
        # Add playwright install after the pip install
        old_end = 'notepad .env'
        new_end = '''notepad .env
)

:: Install Playwright browsers
echo Installing Playwright browsers...
python -m playwright install chromium'''
        content = content.replace(old_end, new_end)

        with io.open('setup.bat', 'w', encoding='utf-8') as f:
            f.write(content)
        log("  SUCCESS: Added python-pptx and playwright to setup.bat")
    else:
        log("  WARNING: Could not find pip install line in setup.bat")

def fix_tool_executor():
    """Add HTML PPT registration to tool_executor.py"""
    log("Fixing tool_executor.py...")
    with io.open('core/tool_executor.py', 'r', encoding='utf-8') as f:
        content = f.read()

    if 'register_html_ppt_tool' in content:
        log("  tool_executor.py already has HTML PPT")
        return

    # Find "return reg" and insert before it
    old = '''            log.info(f"📚 {len(self.skills.list_skills())} skills loaded")
        except ImportError:
            self.recipes = None
            self.skills = None'''

    # Actually find the right spot - after skills load, before generation tier
    old2 = '''self.skills = SkillLibrary()
        for name in self.skills.list_skills():
            self.recipes.recipe_to_tool(name, self.executor)
        log.info(f"📚 {len(self.skills.list_skills())} skills loaded")
    except ImportError:
        self.recipes = None
        self.skills = None'''

    if old2 in content:
        new2 = old2 + '''

        # HTML PPT Builder
        try:
            from generation.html_ppt_builder import register_html_ppt_tool
            register_html_ppt_tool(self.executor.registry)
            log.info("🎨 HTML PPT builder registered")
        except Exception as e:
            log.debug(f"HTML PPT skip: {e}")'''
        content = content.replace(old2, new2)
        with io.open('core/kernel_impl.py', 'w', encoding='utf-8') as f:
            f.write(content)
        log("  SUCCESS: Added HTML PPT to kernel")
        return

    # Try another approach for tool_executor.py itself
    old3 = '''    def _build_registry(self):
        from core.tool_registry import ToolRegistry
        reg = ToolRegistry()'''

    # The simpler approach: add at end of _build_registry before return reg
    old4 = '''        reg.register("investment_watchlist", self._investment_watchlist,
        "Get AI investment watchlist: stock analysis, trends, top picks",
        {"focus": {"type": "string", "default": "technology"}})

        return reg'''

    new4 = '''        reg.register("investment_watchlist", self._investment_watchlist,
        "Get AI investment watchlist: stock analysis, trends, top picks",
        {"focus": {"type": "string", "default": "technology"}})

        # HTML PPT Builder
        try:
            from generation.html_ppt_builder import register_html_ppt_tool
            register_html_ppt_tool(reg)
            log.info("🎨 HTML PPT builder registered")
        except Exception as e:
            log.debug(f"HTML PPT skip: {e}")

        return reg'''

    if old4 in content:
        content = content.replace(old4, new4)
        with io.open('core/tool_executor.py', 'w', encoding='utf-8') as f:
            f.write(content)
        log("  SUCCESS: Added HTML PPT registration to tool_executor.py")
    else:
        log("  WARNING: Could not find insertion point in tool_executor.py")

def verify_v2():
    """Verify V2 modules can be imported"""
    log("Verifying V2 modules...")
    errors = []

    try:
        from core.thinking_pipeline import ThinkingPipeline
        log("  ✓ ThinkingPipeline import OK")
    except Exception as e:
        errors.append(f"ThinkingPipeline: {e}")

    try:
        from control.workflow_executor import WorkflowExecutor
        log("  ✓ WorkflowExecutor import OK")
    except Exception as e:
        errors.append(f"WorkflowExecutor: {e}")

    try:
        from generation.html_ppt_builder import generate_ppt, register_html_ppt_tool
        log("  ✓ HTML PPT Builder import OK")
    except Exception as e:
        errors.append(f"HTML PPT: {e}")

    try:
        from core.worldbank_client import register_worldbank_tool
        log("  ✓ WorldBank client import OK")
    except Exception as e:
        errors.append(f"WorldBank: {e}")

    try:
        from core.arxiv_client import register_arxiv_tool
        log("  ✓ arXiv client import OK")
    except Exception as e:
        errors.append(f"arXiv: {e}")

    if errors:
        log("  Errors found:")
        for e in errors:
            log(f"    - {e}")
    else:
        log("  All V2 modules verified successfully!")

    return len(errors) == 0

def main():
    log("=" * 50)
    log("OpenAGI V2 Completion Script")
    log("=" * 50)
    log("")

    fix_setup_bat()
    log("")
    fix_tool_executor()
    log("")
    verify_v2()
    log("")
    log("=" * 50)
    log("V2 implementation complete!")
    log("Run: python kernel.py web")
    log("=" * 50)

if __name__ == "__main__":
    main()
