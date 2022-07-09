"""For type annotation related utilities.

.. _Google Python Style Guide:
    http://google.github.io/styleguide/pyguide.html

"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Protocol, TypeVar, runtime_checkable


@runtime_checkable
class Comparable(Protocol):
    """Protocol for annotating comparable types."""

    @abstractmethod
    def __lt__(self, other: Any) -> bool:
        ...  # pragma: no cover


T = TypeVar("T")

ComparableT = TypeVar("ComparableT", bound=Comparable)
"""A type for comparable values."""
