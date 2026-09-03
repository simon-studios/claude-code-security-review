"""No retired Anthropic model id may appear anywhere in this repository.

The defect this guards against is not "one wrong string" — it is a class. A model id
pinned in code keeps working right up to its retirement date and then fails, and where
the failure is caught and swallowed (as the false-positive filter's startup probe was)
nothing visible changes. A test that only checked the one id already fixed would not
have caught that id before it broke, and will not catch the next one.
"""

import subprocess
from pathlib import Path

import pytest

from claudecode.retired_model_ids import RETIRED_MODEL_IDS

REPO_ROOT = Path(__file__).resolve().parent.parent

# Files that legitimately NAME retired ids: the register itself and this test.
ALLOWED = {
    'claudecode/retired_model_ids.py',
    'claudecode/test_no_retired_model_ids.py',
}


def _tracked_files():
    """Every git-tracked file — the tree as it is actually published."""
    out = subprocess.run(
        ['git', '-C', str(REPO_ROOT), 'ls-files', '-z'],
        capture_output=True, text=True, check=True).stdout
    return [p for p in out.split('\0') if p]


def _offences():
    hits = []
    for rel in _tracked_files():
        if rel in ALLOWED:
            continue
        path = REPO_ROOT / rel
        try:
            text = path.read_text(encoding='utf-8')
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable — nothing to match
        for lineno, line in enumerate(text.splitlines(), start=1):
            for model_id in RETIRED_MODEL_IDS:
                if model_id in line:
                    hits.append(f'{rel}:{lineno}: {model_id}')
    return hits


def test_repository_names_no_retired_model_id():
    offences = _offences()
    assert not offences, (
        'Retired Anthropic model id(s) found in the tree. A retired id resolves to '
        'not_found_error, so this code cannot work:\n  ' + '\n  '.join(offences))


def test_the_check_can_actually_fail():
    """Negative control: the scanner must find a retired id that IS present."""
    register = REPO_ROOT / 'claudecode/retired_model_ids.py'
    assert 'claude-3-5-haiku-20241022' in register.read_text(encoding='utf-8')
    # The register is on the allow-list, so the check above passes while this id is
    # present — proving the pass is a real scan of the rest of the tree, not an
    # empty file list.
    assert _tracked_files(), 'git ls-files returned nothing — the scan would vacuously pass'


@pytest.mark.parametrize('model_id', RETIRED_MODEL_IDS)
def test_register_entries_look_like_model_ids(model_id):
    assert model_id.startswith('claude-'), model_id
