import subprocess
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))
PATH_FILE = os.path.join(BASE, "python_path.txt")
DRIVER = os.path.join(BASE, "ai_driver.py")

# Read which python was used at install time
py_cmd = None
if os.path.exists(PATH_FILE):
    with open(PATH_FILE) as f:
        saved = f.read().strip()
    if saved:
        py_cmd = saved.split()   # e.g. ["py", "-3.11"]

# Fallback: try common versions
if py_cmd is None:
    for ver in ["3.11", "3.12", "3.10"]:
        r = subprocess.run(["py", f"-{ver}", "--version"],
                           capture_output=True)
        if r.returncode == 0:
            py_cmd = ["py", f"-{ver}"]
            break

if py_cmd is None:
    print("Cannot find a suitable Python.")
    print("Please run install.bat first.")
    input("Press Enter to exit...")
    sys.exit(1)

# Check beamngpy is present
r = subprocess.run(py_cmd + ["-c", "import beamngpy"],
                   capture_output=True)
if r.returncode != 0:
    print("beamngpy is not installed.")
    print("Please run install.bat first.")
    input("Press Enter to exit...")
    sys.exit(1)

# Launch the driver GUI
subprocess.run(py_cmd + [DRIVER])
