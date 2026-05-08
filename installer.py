import subprocess
import sys
import os

BASE = os.path.dirname(os.path.abspath(__file__))

def run(cmd):
    return subprocess.run(cmd, shell=True).returncode == 0

def query(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.returncode, r.stdout.strip()

print()
print("=" * 45)
print("  BeamNG AI Driver - Installer")
print("=" * 45)
print()

# ── Step 1: find all available pythons ──────────
print("Scanning installed Python versions...")
print()

candidates = []
for ver in ["3.11", "3.12", "3.10", "3.9", "3.8"]:
    code, out = query(f"py -{ver} --version")
    if code == 0:
        code2, bits = query(
            f'py -{ver} -c "import struct; print(struct.calcsize(chr(80))*8)"'
        )
        bits = bits.strip() if code2 == 0 else "?"
        print(f"  Found Python {ver}  ({bits}-bit)  ->  {out}")
        candidates.append((ver, bits))

print()

# ── Step 2: pick best 64-bit python ─────────────
best = None
for ver, bits in candidates:
    if bits == "64":
        best = ver
        break

if best is None:
    # Check if we only have 32-bit
    if candidates:
        print("=" * 45)
        print("  ERROR: Only 32-bit Python found!")
        print("=" * 45)
        print()
        print("scipy (needed by beamngpy) has NO 32-bit")
        print("Windows packages. You need 64-bit Python.")
        print()
    else:
        print("=" * 45)
        print("  ERROR: No compatible Python found!")
        print("=" * 45)
        print()

    print("Please install Python 3.11 (64-bit):")
    print()
    print("  https://www.python.org/ftp/python/3.11.15/python-3.11.15-amd64.exe")
    print()
    print("During install: CHECK  'Add Python to PATH'")
    print("Then run install.bat again.")
    print()
    input("Press Enter to exit...")
    sys.exit(1)

print(f"Using Python {best} (64-bit)")
print()

# ── Step 3: clean old installs everywhere ───────
print("Cleaning old installs from all Python versions...")
pkgs = "beamngpy pythonnet proxy_tools scipy numpy"
for ver, _ in candidates:
    subprocess.run(f"py -{ver} -m pip uninstall -y {pkgs}",
                   shell=True, capture_output=True)
print("Done.")
print()

# ── Step 4: install dependencies ────────────────
PY = ["py", f"-{best}"]

steps = [
    (["numpy", "scipy"],   "numpy + scipy  (64-bit binary)"),
    (["pythonnet"],        "pythonnet"),
    (["pynput"],           "pynput  (global hotkey)"),
    (["beamngpy"],         "beamngpy"),
]

for pkglist, label in steps:
    print(f"Installing {label}...")
    # First try binary-only (no compilation needed)
    args = PY + ["-m", "pip", "install", "--only-binary", ":all:"] + pkglist
    ok = subprocess.run(args).returncode == 0
    if not ok:
        # Fallback: allow source build
        args2 = PY + ["-m", "pip", "install"] + pkglist
        ok = subprocess.run(args2).returncode == 0
    if not ok:
        print()
        print(f"ERROR: Failed to install {label}")
        input("Press Enter to exit...")
        sys.exit(1)
    print()

# ── Step 5: verify ───────────────────────────────
print("Verifying beamngpy import...")
code, out = query(
    f'py -{best} -c "import beamngpy; print(beamngpy.__version__)"'
)
if code != 0:
    print("ERROR: beamngpy could not be imported after install.")
    input("Press Enter to exit...")
    sys.exit(1)

print(f"  beamngpy {out}  OK")
print()

# Save the chosen python so the launcher uses the same one
with open(os.path.join(BASE, "python_path.txt"), "w") as f:
    f.write(f"py -{best}")

print("=" * 45)
print("  SUCCESS! Installation complete.")
print("  Now run: launch_driver.bat")
print("=" * 45)
print()
input("Press Enter to exit...")
