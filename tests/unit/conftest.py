import json
import logging
import os
from typing import Any, Dict, Optional

import pytest

# for info on # ignores for pyright and flake8 with fixtures see
# https://github.com/microsoft/pylance-release/discussions/4083

disable_loggers = ["charset_normalizer"]


def pytest_configure():
    for logger_name in disable_loggers:
        logger = logging.getLogger(logger_name)
        logger.disabled = True


def __get_tests_rootdir() -> str:
    return os.path.dirname(__file__).removesuffix("/unit")


@pytest.fixture(scope="function")
def testdata_resources_rootdir_w_path(request) -> str:
    def closure(path):
        return os.path.join(__get_tests_rootdir(), "resources", "test_data", path)

    return closure


@pytest.fixture(scope="function")
def _resource_testfile_rootdir(request) -> str:
    relative_test_file_location = (
        str(request.fspath).removeprefix(__get_tests_rootdir()).removesuffix(".py").removeprefix("/")
    )
    testfile_rootdir = os.path.join(__get_tests_rootdir(), "resources", relative_test_file_location)

    return testfile_rootdir


@pytest.fixture(scope="function")
def resource_testfile_rootdir_w_path(request, _resource_testfile_rootdir) -> str:
    # https://www.inspiredpython.com/article/five-advanced-pytest-fixture-patterns
    def closure(path):
        return os.path.join(_resource_testfile_rootdir, path)

    return closure


def fetch_data_X(competition, page) -> Dict[str, Any]:
    print("here")


def fetch_data_side_effect(
    testdata_resources_rootdir_w_path, competition: Optional[int] = None, page: Optional[str] = None
) -> Dict[str, Any]:
    if competition is None:
        filename = testdata_resources_rootdir_w_path("competitions/competitions.json")
    elif page is None:
        filename = testdata_resources_rootdir_w_path(f"competitions/{competition}/competition_{competition}.json")
    else:
        filename = testdata_resources_rootdir_w_path(
            f"competitions/{competition}/competition_{competition}_{page.split('?')[0]}.json"
        )

    with open(filename) as f:
        print(f"Reading file {filename}")
        output = f.read()

    return json.loads(output)
