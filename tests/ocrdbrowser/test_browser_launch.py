import asyncio
import functools
from typing import AsyncIterator, Callable

import pytest
import pytest_asyncio

from ocrdbrowser import (
    DockerOcrdBrowserFactory,
    NoPortsAvailableError,
    OcrdBrowserFactory,
    SubProcessOcrdBrowserFactory,
)
from tests.ocrdmonitor.server.decorators import compose

# NOTE: We are using different ports in each test case, because I think that tests are executed
# faster than docker is able to free the ports again


def browse_ocrd_not_available() -> bool:
    import shutil

    browse_ocrd = shutil.which("browse-ocrd")
    broadway = shutil.which("broadwayd")
    return not all((browse_ocrd, broadway))


def docker_not_available() -> bool:
    import shutil

    return not bool(shutil.which("docker"))


create_docker_browser_factory = functools.partial(
    DockerOcrdBrowserFactory, "http://localhost"
)

browser_factory_test = compose(
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.parametrize(
        "create_browser_factory",
        (
            pytest.param(
                create_docker_browser_factory,
                marks=(
                    pytest.mark.needs_docker,
                    pytest.mark.skipif(
                        docker_not_available(),
                        reason="Skipping because Docker is not available",
                    ),
                ),
            ),
            pytest.param(
                SubProcessOcrdBrowserFactory,
                marks=pytest.mark.skipif(
                    browse_ocrd_not_available(),
                    reason="Skipping because browse-ocrd or broadwayd are not available",
                ),
            ),
        ),
    ),
)


@pytest_asyncio.fixture(autouse=True)
async def stop_browsers() -> AsyncIterator[None]:
    yield

    cmd = await asyncio.create_subprocess_shell(
        "docker stop $(docker ps | grep ocrd-browser | awk '{ print $1 }')"
    )
    await cmd.wait()


@browser_factory_test
async def test__launching_on_an_allocated_port__raises_unavailable_port_error(
    create_browser_factory: Callable[[set[int]], OcrdBrowserFactory]
) -> None:
    _factory = create_browser_factory({9000})
    first = await _factory("first-owner", "tests/workspaces/a_workspace")

    sut = create_browser_factory({9000})
    with pytest.raises(NoPortsAvailableError):
        second = await sut("second-owner", "tests/workspaces/a_workspace")


@browser_factory_test
async def test__one_port_allocated__launches_on_next_available(
    create_browser_factory: Callable[[set[int]], OcrdBrowserFactory]
) -> None:
    _factory = create_browser_factory({9000})
    await _factory("other-owner", "tests/workspaces/a_workspace")

    sut = create_browser_factory({9000, 9001})
    browser = await sut("second-other-owner", "tests/workspaces/a_workspace")

    assert browser.address() == "http://localhost:9001"
