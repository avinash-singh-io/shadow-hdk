"""Standalone bounded asset installer, launched as an owned process and never imported."""

import base64
import hashlib
import os
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path


def install(url: str, integrity: str, member: str, destination: Path, expected: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix="install-") as temporary:
        directory = Path(temporary)
        archive = directory / "sdk.tgz"
        digest = hashlib.sha512()
        size = 0
        with urllib.request.urlopen(url, timeout=60) as response, archive.open("wb") as output:
            while chunk := response.read(65536):
                size += len(chunk)
                if size > 80 * 1024 * 1024:
                    raise RuntimeError("SDK archive exceeds its pinned asset budget")
                digest.update(chunk)
                output.write(chunk)
        if base64.b64encode(digest.digest()).decode() != integrity:
            raise RuntimeError("SDK archive integrity does not match the pinned release")
        with tarfile.open(archive) as package:
            entry = package.getmember(member)
            if not entry.isfile() or entry.size > 64 * 1024 * 1024:
                raise RuntimeError("SDK binary is not a bounded regular file")
            source = package.extractfile(entry)
            assert source is not None
            data = source.read()
            if hashlib.sha256(data).hexdigest() != expected:
                raise RuntimeError("SDK binary integrity does not match the pinned release")
            staged = directory / "binary"
            staged.write_bytes(data)
            staged.chmod(0o700)
            licence = package.extractfile("package/LICENSE")
            assert licence is not None
            (destination.parent / "LICENSE-agent-browser").write_bytes(licence.read(65536))
            os.replace(staged, destination)


if __name__ == "__main__":
    install(sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]), sys.argv[5])
