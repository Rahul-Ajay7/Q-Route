"""Compressed historical sources must remain verifiable after cleanup."""
import hashlib
import zipfile

import pytest

from team_benchmark.provenance import write_sources, verify_source


def test_snapshot_survives_source_move_and_uses_exact_recorded_bytes(tmp_path):
    source=tmp_path/'module.py'
    source.write_bytes(b'original source\n')
    hashes=write_sources(tmp_path,[source],tmp_path/'sources.zip')
    assert verify_source(tmp_path,'module.py',hashes['module.py'],source)=='current'
    source.unlink()
    assert verify_source(tmp_path,'module.py',hashes['module.py'],source).startswith('snapshot;')
    assert not (tmp_path/'.sources').exists()


def test_corrupt_snapshot_and_path_escape_are_rejected(tmp_path):
    with zipfile.ZipFile(tmp_path/'sources.zip','w') as z:
        z.writestr('module.py',b'changed')
    expected=hashlib.sha256(b'original').hexdigest()
    with pytest.raises(AssertionError,match='Snapshot changed'):
        verify_source(tmp_path,'module.py',expected,tmp_path/'missing.py')
    with pytest.raises(AssertionError,match='Invalid snapshot path'):
        verify_source(tmp_path,'../module.py',expected,tmp_path/'missing.py')
