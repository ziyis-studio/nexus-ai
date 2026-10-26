"""Run the executable lease-fencing integration scenario in a configured QA DB."""

import os
import subprocess

os.environ["NEXUS_INTEGRATION"] = "1"
raise SystemExit(
    subprocess.call(
        [
            "uv",
            "run",
            "pytest",
            "tests/integration/test_persistence.py::test_lease_recovery_fences_old_worker_and_persists_one_result",
            "-v",
        ],
        env=os.environ.copy(),
    )
)
