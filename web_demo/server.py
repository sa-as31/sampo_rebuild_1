import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description="Serve the UAV demo backend through Django.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8080, type=int)
    args = parser.parse_args()

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_django.settings")

    from django.core.management import execute_from_command_line

    address = f"{args.host}:{args.port}"
    print(f"Serving Django backend at http://{address}")
    execute_from_command_line(["manage.py", "runserver", address, "--noreload"])


if __name__ == "__main__":
    main()
