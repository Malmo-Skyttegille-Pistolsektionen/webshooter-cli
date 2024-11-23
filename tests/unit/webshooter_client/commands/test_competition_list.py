from tests.unit.conftest import fetch_data_side_effect
from webshooter_client.commands.competition_list import CompetitionsListCommand


def test_competition_list(mocker, testdata_resources_rootdir_w_path):
    mocker.patch(
        "webshooter_client.commands.competition_list.fetch_data",
        side_effect=lambda competition=None, page=None: fetch_data_side_effect(
            testdata_resources_rootdir_w_path, competition, page
        ),
    )

    result = CompetitionsListCommand.get_competitions_list(year=2024)

    assert len(result) > 0


def test_competitions(mocker, testdata_resources_rootdir_w_path):
    mocker.patch(
        "webshooter_client.commands.competition_list.fetch_data",
        side_effect=lambda competition=None, page=None: fetch_data_side_effect(
            testdata_resources_rootdir_w_path, competition, page
        ),
    )

    result = CompetitionsListCommand.get_competitions(year=2024)

    assert result is None
