"""For representing the data related to tempo and meter.

You will rarely need to create any of this module's objects manually; please instead create a
:class:`~chartparse.chart.Chart` and inspect its attributes via that object.

.. _Google Python Style Guide:
    http://google.github.io/styleguide/pyguide.html

"""

from __future__ import annotations

import datetime
import re
from collections.abc import Callable, Iterable, Sequence
from typing import Optional, Pattern, Type, TypeVar

from chartparse.event import Event
from chartparse.exceptions import RegexNotMatchError
from chartparse.track import EventTrack, HasSectionNameMixin
from chartparse.util import DictPropertiesEqMixin, DictReprTruncatedSequencesMixin

SyncTrackT = TypeVar("SyncTrackT", bound="SyncTrack")


class SyncTrack(
    EventTrack, HasSectionNameMixin, DictPropertiesEqMixin, DictReprTruncatedSequencesMixin
):
    """All of a :class:`~chartparse.chart.Chart` object's tempo-mapping related events."""

    time_signature_events: Sequence[TimeSignatureEvent]
    """A ``SyncTrack``'s ``TimeSignatureEvent``\\ s."""

    bpm_events: Sequence[BPMEvent]
    """A ``SyncTrack``'s ``BPMEvent``\\ s."""

    section_name = "SyncTrack"

    def __init__(
        self, time_signature_events: Sequence[TimeSignatureEvent], bpm_events: Sequence[BPMEvent]
    ):
        """Instantiates and validates all instance attributes.

        Raises:
            ValueError: If ``time_signature_events`` or ``bpm_events`` is empty, or if either of
                their first elements has a ``tick`` value of ``0``.
        """

        if not time_signature_events:
            raise ValueError("time_signature_events must not be empty")
        if time_signature_events[0].tick != 0:
            raise ValueError(
                f"first TimeSignatureEvent {time_signature_events[0]} must have tick 0"
            )
        if not bpm_events:
            raise ValueError("bpm_events must not be empty")
        if bpm_events[0].tick != 0:
            raise ValueError(f"first BPMEvent {bpm_events[0]} must have tick 0")

        self.time_signature_events = time_signature_events
        self.bpm_events = bpm_events

    @classmethod
    def from_chart_lines(
        cls: Type[SyncTrackT], iterator_getter: Callable[[], Iterable[str]]
    ) -> SyncTrackT:
        """Initializes instance attributes by parsing an iterable of strings.

        Args:
            iterator_getter: The iterable of strings returned by this is most likely from a
                Moonscraper ``.chart``. Must be a function so the strings can be iterated over
                multiple times, if necessary.

        Returns:
            A ``SyncTrack`` parsed from the strings returned by ``iterator_getter``.
        """

        time_signature_events = cls._parse_events_from_chart_lines(
            iterator_getter(), TimeSignatureEvent.from_chart_line
        )
        bpm_events = cls._parse_events_from_chart_lines(
            iterator_getter(), BPMEvent.from_chart_line
        )
        return cls(time_signature_events, bpm_events)

    def idx_of_proximal_bpm_event(self, tick: int, start_idx: int = 0) -> int:
        """Returns the index of the :class:`~chartparse.sync.BPMEvent` proximal to ``tick``.

        A BPMEvent is "proximal" relative to tick `T` if it is the BPMEvent with the highest tick
        value not greater than `T`.

        Args:
            tick: The tick value for which the proximal :class:`~chartparse.sync.BPMEvent` should
                be found.
            start_idx: The index from which :attr:`~chartparse.sync.SyncTrack.bpm_events` should be
                searched. This is only an optimization to avoid searching known irrelevant events.

        Returns:
            The index of the :class:`~chartparse.sync.BPMEvent` proximal to ``tick``.

        Raises:
            ValueError: If there are no :class:`~chartparse.sync.BPMEvent` objects at or after
                ``tick`` in :attr:`~chartparse.sync.SyncTrack.bpm_events`.

        """

        for idx in range(start_idx, len(self.bpm_events)):
            is_last_bpm_event = idx == len(self.bpm_events) - 1
            next_bpm_event = self.bpm_events[idx + 1] if not is_last_bpm_event else None
            if is_last_bpm_event or (next_bpm_event is not None and next_bpm_event.tick > tick):
                return idx
        raise ValueError(f"there are no BPMEvents at or after index {start_idx} in bpm_events")


TimeSignatureEventT = TypeVar("TimeSignatureEventT", bound="TimeSignatureEvent")


class TimeSignatureEvent(Event):
    """An event representing a time signature change at a particular tick."""

    upper_numeral: int
    """The number indicating how many beats constitute a bar."""

    lower_numeral: int
    """The number indicating the note value that represents one beat."""

    # Match 1: Tick
    # Match 2: Upper numeral
    # Match 3: Lower numeral (optional; assumed to be 4 if absent)
    _regex: str = r"^\s*?(\d+?) = TS (\d+?)(?: (\d+?))?\s*?$"
    _regex_prog: Pattern[str] = re.compile(_regex)

    def __init__(
        self,
        tick: int,
        upper_numeral: int,
        lower_numeral: int,
        timestamp: Optional[datetime.timedelta] = None,
    ):
        """Initializes all instance attributes."""

        super().__init__(tick, timestamp=timestamp)
        self.upper_numeral = upper_numeral
        self.lower_numeral = lower_numeral

    @classmethod
    def from_chart_line(cls: Type[TimeSignatureEventT], line: str) -> TimeSignatureEventT:
        """Attempt to obtain an instance of this object from a string.

        Args:
            line: Most likely a line from a Moonscraper ``.chart``.

        Returns:
            An an instance of this object parsed from ``line``.

        Raises:
            RegexNotMatchError: If the mixed-into class' ``_regex`` does not match ``line``.
        """

        m = cls._regex_prog.match(line)
        if not m:
            raise RegexNotMatchError(cls._regex, line)
        tick, upper_numeral = int(m.group(1)), int(m.group(2))
        # The lower number is written by Moonscraper as the log2 of the true value.
        lower_numeral = 2 ** int(m.group(3)) if m.group(3) else 4
        return cls(tick, upper_numeral, lower_numeral)

    def __str__(self) -> str:  # pragma: no cover
        to_join = [super().__str__()]
        to_join.append(f": {self.upper_numeral}/{self.lower_numeral}")
        return "".join(to_join)


BPMEventT = TypeVar("BPMEventT", bound="BPMEvent")


class BPMEvent(Event):
    """An event representing a BPM (beats per minute) change at a particular tick."""

    bpm: float
    """The beats per minute value. Must not have more than 3 decimal places."""

    # Match 1: Tick
    # Match 2: BPM (the last 3 digits are the decimal places)
    _regex: str = r"^\s*?(\d+?) = B (\d+?)\s*?$"
    _regex_prog: Pattern[str] = re.compile(_regex)

    def __init__(self, tick: int, bpm: float, timestamp: Optional[datetime.timedelta] = None):
        """Initialize all instance attributes.

        Raises:
            ValueError: If ``bpm`` has more than 3 decimal places.
        """
        if round(bpm, 3) != bpm:
            raise ValueError(f"bpm {bpm} must not have more than 3 decimal places.")
        super().__init__(tick, timestamp=timestamp)
        self.bpm = bpm

    @classmethod
    def from_chart_line(cls: Type[BPMEventT], line: str) -> BPMEventT:
        """Attempt to obtain an instance of this object from a string.

        Args:
            line: Most likely a line from a Moonscraper ``.chart``.

        Returns:
            An an instance of this object parsed from ``line``.

        Raises:
            RegexNotMatchError: If the mixed-into class' ``_regex`` does not match ``line``.
        """

        m = cls._regex_prog.match(line)
        if not m:
            raise RegexNotMatchError(cls._regex, line)
        tick, raw_bpm = int(m.group(1)), m.group(2)
        bpm_whole_part_str, bpm_decimal_part_str = raw_bpm[:-3], raw_bpm[-3:]
        bpm_whole_part = int(bpm_whole_part_str) if bpm_whole_part_str != "" else 0
        bpm_decimal_part = int(bpm_decimal_part_str) / 1000
        bpm = bpm_whole_part + bpm_decimal_part
        return cls(tick, bpm)

    def __str__(self) -> str:  # pragma: no cover
        to_join = [super().__str__()]
        to_join.append(f": {self.bpm} BPM")
        return "".join(to_join)
