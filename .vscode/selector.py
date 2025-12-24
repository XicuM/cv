import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "")
    name = path.name.lower()

    if '.yaml' in name:
        target = path.stem
        print('Building target', target)
    else: 
        target = ''
        print('Building all CV versions')

    try: subprocess.run(['scons', target], check=True)
    except subprocess.CalledProcessError as e: sys.exit(1)
