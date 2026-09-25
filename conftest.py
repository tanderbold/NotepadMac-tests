"""Fixtures: one isolated NotepadMac per test session (per xdist worker)."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from harness.app import App  # noqa: E402


# git, the tests' own and the one the application runs, reads none of the machine's or the
# user's configuration: a user's commit.gpgsign would sign test commits with their key (or hang
# on a passphrase prompt), their identity would end up in test repositories.
_GITCONFIG = Path(__file__).parent / ".work" / "gitconfig"
_GITCONFIG.parent.mkdir(exist_ok=True)
_GITCONFIG.write_text("[commit]\n\tgpgsign = false\n[tag]\n\tgpgsign = false\n[init]\n\tdefaultBranch = main\n")
os.environ["GIT_CONFIG_GLOBAL"] = str(_GITCONFIG)
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"


def _worker_id(config) -> str:
    # NPPMAC_E2E_WORKER lets several suites run side by side, each with its
    # own copy, preference domain, home and socket.
    return os.environ.get("NPPMAC_E2E_WORKER") or os.environ.get("PYTEST_XDIST_WORKER", "main")


@pytest.fixture(scope="session")
def app_session(request):
    app = App(worker=_worker_id(request.config))
    app.start()
    yield app
    app.stop()


@pytest.fixture
def app(app_session):
    """The running application, brought back to a clean slate before the test."""
    if not app_session.running:
        app_session.start()
    app_session.reset()
    yield app_session


@pytest.fixture
def fresh_app(app_session):
    """A newly started application with empty preferences and home."""
    app_session.stop()
    app_session.start()
    yield app_session


@pytest.fixture
def tmp(tmp_path):
    """A scratch folder with the /private prefix resolved, as the app reports paths."""
    return Path(os.path.realpath(tmp_path))
