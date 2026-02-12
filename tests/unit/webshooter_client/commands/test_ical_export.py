"""Tests for iCal export functionality."""

from datetime import datetime
from icalendar import Calendar
from webshooter_client.commands.ical_export import export_starttimes
from webshooter_client.models.competition import Competition, CompetitionType
from webshooter_client.models.patrol import Patrol
from webshooter_client.models.signup import Signup


def test_export_starttimes_generates_valid_ical(tmp_path, mocker, monkeypatch):
    """Test that export_starttimes generates a valid iCal file that can be parsed."""
    # Change to temp directory so file is created there
    monkeypatch.chdir(tmp_path)

    # Mock data
    competition = Competition(
        id=123,
        name="Test Competition",
        competition_date="2026-03-15",
        signups_close="2026-03-10",
        city="Stockholm",
        venue="Test Venue",
        type=CompetitionType.FIELD,
    )

    signup1 = Signup(
        id=1,
        shooting_card_number="12345",
        fullname="Test Shooter",
        spsf_club_number="12-239",
        weapon_class="C3",
        weapon_class_general="C",
        lane=1,
        share_patrol_with=None,
    )

    patrol = Patrol(
        id=1,
        number=1,
        start_time=datetime(2026, 3, 15, 10, 0, 0),
        end_time=datetime(2026, 3, 15, 12, 0, 0),
        signups=[signup1],
    )

    # Mock API calls
    mocker.patch("webshooter_client.commands.ical_export.get_patrols", return_value=[patrol])
    mocker.patch("webshooter_client.commands.ical_export.get_competition", return_value=competition)

    # Execute
    export_starttimes(competition_id=123, club="12-239")

    # Verify file was created
    ical_file = tmp_path / "webshooter_123.ical"
    assert ical_file.exists()

    # Verify file is valid iCal format
    with open(ical_file, "rb") as f:
        cal = Calendar.from_ical(f.read())

    # Verify calendar properties
    assert cal.get("prodid") == "-//Webshooter//Pistol//SV"
    assert cal.get("version") == "2.0"

    # Verify events
    events = [component for component in cal.walk() if component.name == "VEVENT"]
    assert len(events) == 1

    event = events[0]
    assert event.get("uid") == "webshooter_123-1"
    assert event.get("summary") == "Test Competition"
    assert event.get("location") == "Stockholm"
    assert "Test Competition" in event.get("description")
    assert "Vapengrupp: C3" in event.get("description")
    assert "Patrull: 1" in event.get("description")


def test_export_starttimes_filters_by_card(tmp_path, mocker, monkeypatch):
    """Test that export_starttimes filters by card number."""
    monkeypatch.chdir(tmp_path)

    competition = Competition(
        id=456,
        name="Test Competition 2",
        competition_date="2026-04-20",
        signups_close="2026-04-15",
        city="Gothenburg",
        venue="Test Venue 2",
        type=CompetitionType.PRECISION,
    )

    signup1 = Signup(
        id=1,
        shooting_card_number="11111",
        fullname="Shooter 1",
        spsf_club_number="12-239",
        weapon_class="C3",
        weapon_class_general="C",
        lane=1,
        share_patrol_with=None,
    )
    signup2 = Signup(
        id=2,
        shooting_card_number="22222",
        fullname="Shooter 2",
        spsf_club_number="12-239",
        weapon_class="CD2",
        weapon_class_general="CD",
        lane=2,
        share_patrol_with=None,
    )

    patrol = Patrol(
        id=1,
        number=1,
        start_time=datetime(2026, 4, 20, 14, 0, 0),
        end_time=datetime(2026, 4, 20, 16, 0, 0),
        signups=[signup1, signup2],
    )

    mocker.patch("webshooter_client.commands.ical_export.get_patrols", return_value=[patrol])
    mocker.patch("webshooter_client.commands.ical_export.get_competition", return_value=competition)

    # Export with card filter
    export_starttimes(competition_id=456, club="12-239", card="11111")

    ical_file = tmp_path / "webshooter_456.ical"
    with open(ical_file, "rb") as f:
        cal = Calendar.from_ical(f.read())

    events = [component for component in cal.walk() if component.name == "VEVENT"]
    assert len(events) == 1  # Only one event for card 11111
    assert events[0].get("uid") == "webshooter_456-1"
