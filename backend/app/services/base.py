"""
Abstract base service contract.

Applying SOLID principles:
  - Single Responsibility: each concrete service handles one domain entity.
  - Open/Closed: new services extend BaseService without modifying it.
  - Liskov Substitution: any BaseService[T] implementation can replace another
    with the same T without breaking callers (e.g., swap a mock service in tests).
  - Interface Segregation: services that do not need all operations (e.g., a
    read-only ML inference service) simply raise NotImplementedError for
    write methods and document this explicitly.
  - Dependency Inversion: route handlers depend on the abstract BaseService[T],
    not on concrete implementations. Concrete services are injected as
    FastAPI dependencies.

Future concrete service examples:
  - SensorService(BaseService[Sensor])
  - AirQualityReadingService(BaseService[AirQualityReading])
  - AQIForecastService(BaseService[AQIForecast])  — read-only ML inference
  - AlertService(BaseService[Alert])
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class BaseService(ABC, Generic[T]):
    """
    Abstract CRUD service contract for a single domain entity type T.

    All business-logic services must implement this interface.
    Enforces a consistent API contract across all domain services,
    making them interchangeable in dependency injection and tests.
    """

    @abstractmethod
    async def get_by_id(self, id: int) -> T | None:
        """
        Retrieve a single entity by its primary key.

        Returns:
            The entity instance, or None if no record with that ID exists.
        """
        ...

    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100) -> list[T]:
        """
        Return a paginated list of entities.

        Args:
            skip:  Number of records to skip (for cursor/offset pagination).
            limit: Maximum number of records to return. Default 100.
        """
        ...

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> T:
        """
        Persist a new entity and return the created instance.

        Args:
            data: A dictionary of field values validated by the caller's Pydantic schema.

        Raises:
            ConflictError: If a unique constraint violation is detected.
            DatabaseError: If the insert fails for any other reason.
        """
        ...

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """
        Delete the entity with the given primary key.

        Returns:
            True if the entity was found and deleted.
            False if no entity with that ID exists.

        Raises:
            DatabaseError: If the delete fails for any reason other than NOT FOUND.
        """
        ...
