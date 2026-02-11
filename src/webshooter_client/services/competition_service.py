"""Service layer abstraction for API calls.

This provides an interface that can be injected into commands for better testability.
Default implementation delegates to the existing api_calls module.
"""

from typing import Optional, List, Dict
from abc import ABC, abstractmethod

from webshooter_client.models.competition import Competition
from webshooter_client.models.signup import Signup
from webshooter_client.models.patrol import Patrol
from webshooter_client.models.result import ResultBase


class CompetitionService(ABC):
    """Abstract service for competition-related operations."""

    @abstractmethod
    def get_competition(self, competition_id: int) -> Competition:
        """Fetch a single competition by ID."""
        pass

    @abstractmethod
    def get_competitions(self, year: Optional[int] = None) -> Dict[int, Competition]:
        """Fetch all competitions, optionally filtered by year."""
        pass

    @abstractmethod
    def get_signups(self, competition_id: int) -> List[Signup]:
        """Fetch signups for a competition."""
        pass

    @abstractmethod
    def get_patrols(self, competition_id: int) -> List[Patrol]:
        """Fetch patrols/start times for a competition."""
        pass

    @abstractmethod
    def get_results(self, competition_id: int) -> List[ResultBase]:
        """Fetch results for a competition."""
        pass


class DefaultCompetitionService(CompetitionService):
    """Default implementation delegating to api_calls module."""

    def get_competition(self, competition_id: int) -> Competition:
        from webshooter_client.api.api_calls import get_competition
        return get_competition(competition_id=competition_id)

    def get_competitions(self, year: Optional[int] = None) -> Dict[int, Competition]:
        from webshooter_client.api.api_calls import get_competitions
        return get_competitions(year=year)

    def get_signups(self, competition_id: int) -> List[Signup]:
        from webshooter_client.api.api_calls import get_signups
        return get_signups(competition_id=competition_id)

    def get_patrols(self, competition_id: int) -> List[Patrol]:
        from webshooter_client.api.api_calls import get_patrols
        return get_patrols(competition_id=competition_id)

    def get_results(self, competition_id: int) -> List[ResultBase]:
        from webshooter_client.api.api_calls import get_results
        return get_results(competition_id=competition_id)


# Global service instance - can be replaced for testing
_service_instance: CompetitionService = DefaultCompetitionService()


def get_service() -> CompetitionService:
    """Get the current service instance."""
    return _service_instance


def set_service(service: CompetitionService) -> None:
    """Set a custom service instance (for testing)."""
    global _service_instance
    _service_instance = service
