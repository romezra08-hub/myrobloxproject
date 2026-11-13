"""Rebuild every pet: its Roblox file, its texture and its review sheet, then the line-up picture.

    python models/build_all.py              # all pets
    python models/build_all.py fox puppy    # only these (the line-up still shows every pet)
"""
import glob
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def pets():
    """Every pet with a current script: pets/<name>.py, leaving out the kept practice rounds (<name>_v3.py)."""
    names = [os.path.basename(p)[:-3] for p in glob.glob(os.path.join(HERE, "pets", "*.py"))]
    return sorted(n for n in names if "_v" not in n)


def main():
    for name in sys.argv[1:] or pets():
        subprocess.run([sys.executable, os.path.join(HERE, "pets", name + ".py"),
                        "--export", os.path.join(HERE, "export", name + ".fbx"),
                        "--review", os.path.join(HERE, "preview", name + ".png")], check=True, stdout=subprocess.DEVNULL)
        shutil.rmtree(os.path.join(HERE, "preview", name + "_views"), ignore_errors=True)
        print("built", name, flush=True)
    subprocess.run([sys.executable, os.path.join(HERE, "lineup.py")], check=True, stdout=subprocess.DEVNULL)
    print("line-up rendered", flush=True)


if __name__ == "__main__":
    main()
