import argparse
import contextlib
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Build MLflow package.")
    parser.add_argument(
        "--package-type",
        help="Package type to build. Default is 'dev'.",
        choices=["skinny", "release", "dev"],
        default="dev",
    )
    parser.add_argument(
        "--sha",
        help="If specified, include the SHA in the wheel name as a build tag.",
    )
    return parser.parse_args()


@contextlib.contextmanager
def restore_changes():
    try:
        yield
    finally:
        subprocess.check_call(
            [
                "git",
                "restore",
                "README.md",
                "pyproject.toml",
            ]
        )


def main():
    args = parse_args()

    # Clean up build artifacts generated by previous builds
    for path in map(
        Path,
        [
            "build",
            "dist",
            "mlflow.egg-info",
            "skinny/dist",
            "skinny/mlflow_skinny.egg_info",
        ],
    ):
        if not path.exists():
            continue
        if path.is_file():
            path.unlink()
        else:
            shutil.rmtree(path)

    with restore_changes():
        pyproject = Path("pyproject.toml")
        if args.package_type == "release":
            pyproject.write_text(Path("pyproject.release.toml").read_text())

        SKINNY_DIR = Path("skinny")
        IS_SKINNY = args.package_type == "skinny"
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "build",
                SKINNY_DIR if IS_SKINNY else ".",
            ]
        )

        DIST_DIR = Path("dist")
        DIST_DIR.mkdir(exist_ok=True)
        if IS_SKINNY:
            # Move `skinny/dist/*` to `dist/`
            for src in (SKINNY_DIR / "dist").glob("*"):
                dst = DIST_DIR / src.name
                if dst.exists():
                    dst.unlink()
                src.rename(dst)

    if args.sha:
        # If build succeeds, there should be one wheel in the dist directory
        wheel = next(DIST_DIR.glob("mlflow*.whl"))
        name, version, rest = wheel.name.split("-", 2)
        build_tag = f"0.sha.{args.sha}"  # build tag must start with a digit
        wheel.rename(wheel.with_name(f"{name}-{version}-{build_tag}-{rest}"))


if __name__ == "__main__":
    main()
