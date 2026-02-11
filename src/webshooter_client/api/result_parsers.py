"""Strategy pattern for parsing different competition result types from API."""

from abc import ABC, abstractmethod
from typing import Dict, Any

from webshooter_client.models.result import (
    ResultBase,
    PrecisionResult,
    MilitaryResult,
    FieldResult,
    SeriesResult,
    StationResult,
    StdMedal,
)
from webshooter_client.models.signup import Signup
from webshooter_client.models.competition import CompetitionType
import logging


class ResultParser(ABC):
    """Abstract base class for result parsing strategies."""

    @abstractmethod
    def parse(self, result_data: Dict[str, Any], signup: Signup) -> ResultBase:
        """Parse API result data into a Result object.

        Args:
            result_data: Raw result data from API
            signup: Signup object for this result

        Returns:
            Parsed Result object of appropriate type
        """
        pass

    def _parse_base_fields(self, result_data: Dict[str, Any], signup: Signup) -> Dict[str, Any]:
        """Extract common fields shared across all result types.

        Args:
            result_data: Raw result data from API
            signup: Signup object

        Returns:
            Dictionary of base fields for Result construction

        Raises:
            DataValidationError: If required fields are missing or invalid
        """
        from webshooter_client.api.exceptions import DataValidationError

        # Validate required fields
        if not result_data:
            raise DataValidationError("Result data is empty or None")

        if "placement" not in result_data:
            raise DataValidationError(f"Missing required field 'placement' in result for {signup.fullname}")

        # Handle points with default for missing values
        points = int(result_data.get("points", -1))
        if points == -1:
            logging.warning(f"Result for {signup.fullname} has invalid points value: -1")

        return {
            "signup": signup,
            "placement": int(result_data["placement"]),
            "std_medal": StdMedal(result_data["std_medal"]) if result_data.get("std_medal") else None,
            "points": points,
        }


class SeriesResultParser(ResultParser):
    """Parser for PRECISION and MILITARY results with series data."""

    def __init__(self, result_class):
        self.result_class = result_class

    def parse(self, result_data: Dict[str, Any], signup: Signup) -> ResultBase:
        """Parse result with series data."""
        base_kwargs = self._parse_base_fields(result_data, signup)
        series = [
            SeriesResult(points=s["points"], inner_tens=s.get("hits"))
            for s in result_data.get("results", [])
        ]
        return self.result_class(**base_kwargs, series=series)


class StationResultParser(ResultParser):
    """Parser for FIELD results with station data."""

    def parse(self, result_data: Dict[str, Any], signup: Signup) -> ResultBase:
        """Parse result with station data."""
        base_kwargs = self._parse_base_fields(result_data, signup)
        stations = [
            StationResult(hits=st.get("hits", 0), figure_hits=st.get("figure_hits"), points=st.get("points"))
            for st in result_data.get("results", [])
        ]
        return FieldResult(**base_kwargs, stations=stations)


class GenericResultParser(ResultParser):
    """Fallback parser for unknown result types."""

    def parse(self, result_data: Dict[str, Any], signup: Signup) -> ResultBase:
        """Parse result using base fields only."""
        base_kwargs = self._parse_base_fields(result_data, signup)
        return ResultBase(**base_kwargs)


class ResultParserFactory:
    """Factory for creating appropriate result parsers."""

    _parsers = {
        CompetitionType.PRECISION: SeriesResultParser(PrecisionResult),
        CompetitionType.MILITARY: SeriesResultParser(MilitaryResult),
        CompetitionType.FIELD: StationResultParser(),
        CompetitionType.POINTFIELD: StationResultParser(),
    }

    @classmethod
    def get_parser(cls, competition_type: CompetitionType) -> ResultParser:
        """Get the appropriate parser for a competition type.

        Args:
            competition_type: Type of competition

        Returns:
            ResultParser instance for the competition type
        """
        return cls._parsers.get(competition_type, GenericResultParser())
