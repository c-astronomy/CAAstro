#!/usr/bin/env python3
"""Simple verification script to check project structure and basic syntax."""

import os
import sys

def check_files_exist():
    """Check that all required files exist."""
    required_files = [
        '/workspace/main.py',
        '/workspace/astro_control/app.py',
        '/workspace/astro_control/devices.py',
        '/workspace/astro_control/planetarium.py',
        '/workspace/astro_control/sequencer.py',
        '/workspace/astro_control/focus_widget.py',
        '/workspace/astro_control/guiding_widget.py',
        '/workspace/astro_control/mount_widget.py',
        '/workspace/astro_control/mount_widget.py',
        '/workspace/astro_control/imageviewer.py',
        '/workspace/README.md',
        '/workspace/requirements.txt'
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print("❌ Missing files:")
        for m in missing:
            print(f"  - {m}")
        return False
    else:
        print("✅ All required files exist")
        return True

def check_syntax():
    """Check Python syntax in all Python files."""
    import ast
    
    py_files = [
        '/workspace/main.py',
        '/workspace/astro_control/app.py',
        '/workspace/astro_control/devices.py',
        '/workspace/astro_control/planetarium.py',
        '/workspace/astro_control/sequencer.py',
        '/workspace/astro_control/focus_widget.py',
        '/workspace/astro_control/guiding_widget.py',
        '/workspace/astro_control/mount_widget.py',
        '/workspace/astro_control/imageviewer.py'
    ]
    
    errors = []
    for file in py_files:
        try:
            with open(file, 'r') as f:
                content = f.read()
                ast.parse(content)
        except SyntaxError as e:
            errors.append(f"{file}: {e}")
        except Exception as e:
            errors.append(f"{file}: {type(e).__name__}: {e}")
    
    if errors:
        print("❌ Syntax errors found:")
        for err in errors:
            print(f"  - {err}")
        return False
    else:
        print("✅ All Python files have valid syntax")
        return True

def main():
    print("🔍 Verifying AstroControl project...")
    
    if not check_files_exist():
        sys.exit(1)
    
    if not check_syntax():
        sys.exit(1)
    
    print("\n✅ Project verification complete!")
    print("All files are present and syntax is valid.")
    print("You can now run the application with `python main.py`")

if __name__ == "__main__":
    main()