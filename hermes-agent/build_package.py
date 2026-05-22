"""
Hermes Agent - Windows Standalone Package
==========================================

This script creates a standalone zip package for Windows 7 deployment.
"""

import os
import zipfile
import shutil
from datetime import datetime

def create_package():
    """Create a standalone zip package."""
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    os.chdir(base_dir)
    
    package_name = f"hermes-agent-v2-win7"
    timestamp = datetime.now().strftime("%Y%m%d")
    zip_name = f"{package_name}-{timestamp}.zip"
    
    print("=" * 60)
    print("  Hermes Agent - Package Builder")
    print("=" * 60)
    
    # Files to include (relative to project root)
    include_patterns = [
        # Python source
        (".", ["agent", "memory", "tools", "session.py", "requirements.txt", "run.bat", "start.bat", "README.md"]),
        # Config
        (".", ["config"], True),  # include subdirs
        # IO
        (".", ["io"], True),
        # Wiki
        (".", ["wiki"], True),
        # Skills
        (".", ["skills"], True),
        # Tests (for reference)
        (".", ["tests"], True),
    ]
    
    # Files/dirs to exclude
    exclude = {
        "__pycache__",
        ".pytest_cache",
        ".git",
        ".DS_Store",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".egg-info",
        "node_modules",
    }
    
    def should_include(path):
        """Check if path should be included."""
        path_lower = path.lower()
        for exc in exclude:
            if exc.startswith("*"):
                if path_lower.endswith(exc[1:]):
                    return False
            else:
                if exc in path:
                    return False
        return True
    
    print(f"\n[INFO] Creating package: {zip_name}")
    
    # Create zip
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        count = 0
        for root, dirs, files in os.walk('.'):
            # Filter excluded dirs
            dirs[:] = [d for d in dirs if d not in exclude]
            
            for file in files:
                if file in exclude or file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = file_path[2:] if file_path.startswith('./') else file_path
                
                if should_include(file_path):
                    zf.write(file_path, arcname)
                    count += 1
    
    # Get zip size
    zip_size = os.path.getsize(zip_name) / 1024 / 1024
    
    print(f"\n[OK] Package created: {zip_name}")
    print(f"     Files included: {count}")
    print(f"     Package size: {zip_size:.2f} MB")
    
    # Extract to a folder for easy access
    extract_dir = f"{package_name}-{timestamp}"
    extract_path = os.path.join(base_dir, extract_dir)
    
    print(f"\n[INFO] Extracting to: {extract_dir}/")
    
    with zipfile.ZipFile(zip_name, 'r') as zf:
        zf.extractall(extract_dir)
    
    print(f"[OK] Package ready at: {extract_path}")
    
    return zip_name, extract_path


def verify_package(extract_path):
    """Verify the package contents."""
    print("\n" + "=" * 60)
    print("  Package Verification")
    print("=" * 60)
    
    # Check key files exist
    key_files = [
        "agent/loop_v2.py",
        "memory/core.py",
        "tools/registry.py",
        "session.py",
        "run.bat",
        "start.bat",
        "requirements.txt",
        "README.md",
    ]
    
    missing = []
    for f in key_files:
        full_path = os.path.join(extract_path, f)
        if not os.path.exists(full_path):
            missing.append(f)
    
    if missing:
        print(f"\n[FAIL] Missing files:")
        for m in missing:
            print(f"     - {m}")
        return False
    else:
        print(f"\n[OK] All key files present ({len(key_files)} files)")
    
    # Try importing
    print("\n[INFO] Testing imports...")
    sys.path.insert(0, extract_path)
    
    try:
        import agent.loop_v2
        import memory.core
        import tools
        print("[OK] All imports work")
        return True
    except Exception as e:
        print(f"[FAIL] Import error: {e}")
        return False
    finally:
        sys.path.pop(0)


def main():
    zip_name, extract_path = create_package()
    
    if verify_package(extract_path):
        print("\n" + "=" * 60)
        print("  SUCCESS - Package Ready for Deployment")
        print("=" * 60)
        print(f"\n  Location: {extract_path}")
        print(f"  Package: {zip_name}")
        print("\n  To deploy on Windows 7:")
        print("  1. Copy this folder to the target machine")
        print("  2. Run start.bat or run.bat")
        print("  3. Ensure Python 3.7+ is installed")
        print("  4. Run: pip install -r requirements.txt (if needed)")
    else:
        print("\n[FAIL] Package verification failed!")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())