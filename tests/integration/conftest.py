import asyncio
import os
import sys

import pytest


@pytest.fixture(scope="session")
def event_loop_policy():
    if sys.platform == "win32":
        return asyncio.WindowsSelectorEventLoopPolicy()
    return asyncio.DefaultEventLoopPolicy()


def pytest_collection_modifyitems(config, items):
    if os.getenv("NEXUS_INTEGRATION") != "1":
        for item in items:
            item.add_marker(
                pytest.mark.skip(
                    reason="Set NEXUS_INTEGRATION=1 for configured PostgreSQL/API integration environment."
                )
            )
