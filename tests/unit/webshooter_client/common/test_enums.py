"""Tests for DisplayEnum base class."""

import pytest
from enum import Enum

from webshooter_client.common.enums import DisplayEnum


# Create a test enum for testing
class TestEnum(DisplayEnum):
    """Test enum using DisplayEnum."""

    OPTION_A = ("value_a", "Display Name A")
    OPTION_B = ("value_b", "Display Name B")
    OPTION_C = ("value_c", "Display Name C")


class TestDisplayEnum:
    """Tests for DisplayEnum base class."""

    def test_enum_has_value(self):
        """Enum members have correct values."""
        assert TestEnum.OPTION_A.value == "value_a"
        assert TestEnum.OPTION_B.value == "value_b"
        assert TestEnum.OPTION_C.value == "value_c"

    def test_enum_has_display_name(self):
        """Enum members have display_name attribute."""
        assert TestEnum.OPTION_A.display_name == "Display Name A"
        assert TestEnum.OPTION_B.display_name == "Display Name B"
        assert TestEnum.OPTION_C.display_name == "Display Name C"

    def test_enum_construction_from_value(self):
        """Enum can be constructed from value."""
        enum_a = TestEnum("value_a")
        assert enum_a == TestEnum.OPTION_A
        assert enum_a.display_name == "Display Name A"

    def test_enum_equality(self):
        """Enum members support equality checks."""
        assert TestEnum.OPTION_A == TestEnum.OPTION_A
        assert TestEnum.OPTION_A != TestEnum.OPTION_B

    def test_enum_is_enum_instance(self):
        """DisplayEnum members are Enum instances."""
        assert isinstance(TestEnum.OPTION_A, Enum)
        assert isinstance(TestEnum.OPTION_A, DisplayEnum)

    def test_enum_invalid_value_raises(self):
        """Creating enum from invalid value raises ValueError."""
        with pytest.raises(ValueError):
            TestEnum("invalid_value")

    def test_enum_iteration(self):
        """Enum supports iteration over members."""
        members = list(TestEnum)
        assert len(members) == 3
        assert TestEnum.OPTION_A in members
        assert TestEnum.OPTION_B in members
        assert TestEnum.OPTION_C in members

    def test_enum_name_attribute(self):
        """Enum members have name attribute."""
        assert TestEnum.OPTION_A.name == "OPTION_A"
        assert TestEnum.OPTION_B.name == "OPTION_B"

    def test_enum_repr(self):
        """Enum members have readable repr."""
        assert "TestEnum" in repr(TestEnum.OPTION_A)
        assert "OPTION_A" in repr(TestEnum.OPTION_A)
