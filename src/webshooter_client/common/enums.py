"""Base enum classes with display names for the webshooter client."""

from enum import Enum


class DisplayEnum(Enum):
    """Base enum class that supports display names.

    This eliminates the duplicate __new__ pattern across enum classes.
    Each enum member is defined as a tuple of (value, display_name).

    Example:
        class MyEnum(DisplayEnum):
            OPTION_A = ("value_a", "Display Name A")
            OPTION_B = ("value_b", "Display Name B")

        # Access display name
        MyEnum.OPTION_A.display_name  # "Display Name A"

        # Standard enum operations work as expected
        MyEnum("value_a")  # MyEnum.OPTION_A
    """

    def __new__(cls, value, display_name):
        """Create enum member with value and display_name attributes.

        Args:
            value: The enum value (used for equality and construction)
            display_name: Human-readable name for display purposes

        Returns:
            Enum member with display_name attribute
        """
        obj = object.__new__(cls)
        obj._value_ = value
        obj.display_name = display_name
        return obj
