from tests.unit.conftest import fetch_data_side_effect
from webshooter_client.commands.competitions import CompetitionsCommand


def test_competition_list(mocker, testdata_resources_rootdir_w_path, capsys):
    mocker.patch(
        "webshooter_client.api.api_calls.fetch_data",
        side_effect=lambda url: fetch_data_side_effect(testdata_resources_rootdir_w_path, competition=None, page=None),
    )

    result = CompetitionsCommand.get_competitions(year=2024)

    # Method returns None but prints output
    assert result is None

    # Check that output was printed
    captured = capsys.readouterr()
    assert "Total:" in captured.out


def test_competitions(mocker, testdata_resources_rootdir_w_path):
    mocker.patch(
        "webshooter_client.api.api_calls.fetch_data",
        side_effect=lambda url: fetch_data_side_effect(testdata_resources_rootdir_w_path, competition=None, page=None),
    )

    result = CompetitionsCommand.get_competitions(year=2024)

    assert result is None
