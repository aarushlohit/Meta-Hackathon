import subprocess
import sys
from pathlib import Path


TEST_FILES = [
    "test_env.py",
    "test_parser.py",
    "test_api.py",
    "test_inference.py",
    "test_tasks.py",
    "test_docker_runtime.py",
]


def run_one(test_file: str) -> bool:
    cmd = [sys.executable, "-m", "pytest", test_file, "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    print(f"\n=== {test_file} ===")
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())

    passed = result.returncode == 0
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    return passed


def main() -> int:
    root = Path(__file__).resolve().parent

    missing = [f for f in TEST_FILES if not (root / f).exists()]
    if missing:
        print("Missing required test files:")
        for item in missing:
            print(f"- {item}")
        return 2

    passed = 0
    failed = 0

    for test_file in TEST_FILES:
        ok = run_one(test_file)
        if ok:
            passed += 1
        else:
            failed += 1

    print("\n=== SUMMARY ===")
    print(f"PASS: {passed}")
    print(f"FAIL: {failed}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
