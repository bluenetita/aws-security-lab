"""Generate and verify SHA-256 checksums of canonical Git blobs."""

import argparse
import hashlib
import subprocess
from pathlib import Path

MANIFEST = b"MANIFEST.sha256"


def git(*args):
    return subprocess.check_output(["git", *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    root = Path(git("rev-parse", "--show-toplevel").decode().strip())

    entries = {}

    for entry in git("ls-files", "--stage", "-z").split(b"\0"):
        if not entry:
            continue

        metadata, path = entry.split(b"\t", 1)
        file_mode, oid, stage = metadata.split()

        if stage != b"0":
            raise SystemExit("ERROR: Unmerged Git index")

        if file_mode not in (b"100644", b"100755"):
            raise SystemExit(f"ERROR: Unsupported file mode: {path!r}")

        if any(c < 32 for c in path) or b"\\" in path:
            raise SystemExit(f"ERROR: Unsupported path: {path!r}")

        entries[path] = oid.decode("ascii")

    if MANIFEST not in entries:
        raise SystemExit("ERROR: Manifest must already be tracked")

    lines = []

    for path in sorted(entries):
        if path == MANIFEST:
            continue

        content = git("cat-file", "blob", entries[path])
        digest = hashlib.sha256(content).hexdigest().encode("ascii")

        lines.append(digest + b"  " + path + b"\n")

    expected = b"".join(lines)

    if args.write:
        (root / MANIFEST.decode()).write_bytes(expected)
        print(f"PASS: Manifest generated with {len(lines)} entries")
    else:
        actual = git("cat-file", "blob", entries[MANIFEST])

        if actual != expected:
            raise SystemExit(
                "FAIL: Manifest does not match the Git index"
            )

        print(f"PASS: All {len(lines)} canonical Git checksums verified")


if __name__ == "__main__":
    main()
