"""Compact source snapshots; archive bytes are verified without executing them."""
import hashlib
from pathlib import Path, PurePosixPath
import zipfile


def write_sources(root, paths, output):
    hashes = {}
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            name=path.resolve().relative_to(root.resolve()).as_posix()
            data=path.read_bytes()
            archive.writestr(name,data)
            hashes[name]=hashlib.sha256(data).hexdigest()
    return hashes


def verify_source(folder, name, expected, current):
    if current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest()==expected:
        return "current"
    key=PurePosixPath(name.replace('\\','/'))
    assert not key.is_absolute() and '..' not in key.parts, "Invalid snapshot path"
    compressed=folder/'sources.zip'
    if compressed.is_file():
        with zipfile.ZipFile(compressed) as archive:
            data=archive.read(key.as_posix())
    else:
        snapshot=(folder/'.sources'/Path(*key.parts)).resolve()
        assert snapshot.is_relative_to((folder/'.sources').resolve()), "Invalid snapshot path"
        assert snapshot.is_file(), f"Source changed and no snapshot exists: {name}"
        data=snapshot.read_bytes()
    assert hashlib.sha256(data).hexdigest()==expected, f"Snapshot changed: {name}"
    return "snapshot; current source differs"
