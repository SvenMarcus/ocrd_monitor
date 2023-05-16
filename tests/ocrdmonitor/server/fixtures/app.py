from pathlib import Path
from typing import Iterator

import pytest
import pytest_asyncio
import uvicorn
from fastapi.testclient import TestClient

from ocrdmonitor.server.app import create_app
from ocrdmonitor.server.settings import (
    OcrdBrowserSettings,
    OcrdControllerSettings,
    OcrdLogViewSettings,
    Settings,
)
from tests.testdoubles import BackgroundProcess

JOB_DIR = Path(__file__).parent / "ocrd.jobs"
WORKSPACE_DIR = Path("tests") / "workspaces"


def create_settings() -> Settings:
    return Settings(
        ocrd_browser=OcrdBrowserSettings(
            workspace_dir=WORKSPACE_DIR,
            port_range=(9000, 9100),
            db_connection_string="",
        ),
        ocrd_controller=OcrdControllerSettings(
            job_dir=JOB_DIR,
            host="",
            user="",
        ),
        ocrd_logview=OcrdLogViewSettings(port=8022),
    )


@pytest_asyncio.fixture
async def app() -> TestClient:
    return TestClient(await create_app(create_settings()))


def _launch_app() -> None:
    app = create_app(create_settings())
    uvicorn.run(app, port=3000)


@pytest.fixture
def launch_monitor() -> Iterator[None]:
    with BackgroundProcess(_launch_app):
        yield