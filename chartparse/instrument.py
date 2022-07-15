"""For representing the data related to a single (instrument, difficulty) pair.

You will rarely need to create any of this module's objects manually; please instead create a
:class:`~chartparse.chart.Chart` and inspect its attributes via that object.

.. _Google Python Style Guide:
    http://google.github.io/styleguide/pyguide.html

"""

from __future__ import annotations

import collections
import datetime
import enum
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, List, Optional, Pattern, Type, TypeVar, Union

import chartparse.tick
from chartparse.datastructures import ImmutableSortedList
from chartparse.event import Event
from chartparse.exceptions import RegexNotMatchError
from chartparse.tick import NoteDuration
from chartparse.track import EventTrack
from chartparse.util import (
    AllValuesGettableEnum,
    DictPropertiesEqMixin,
    DictReprTruncatedSequencesMixin,
)

InstrumentTrackT = TypeVar("InstrumentTrackT", bound="InstrumentTrack")


@enum.unique
class Difficulty(AllValuesGettableEnum):
    """An :class:`~chartparse.instrument.InstrumentTrack`'s difficulty setting."""

    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    EXPERT = "Expert"


@enum.unique
class Instrument(AllValuesGettableEnum):
    """The instrument to which a :class:`~chartparse.instrument.InstrumentTrack` corresponds."""

    GUITAR = "Single"
    GUITAR_COOP = "DoubleGuitar"
    BASS = "DoubleBass"
    RHYTHM = "DoubleRhythm"
    KEYS = "Keyboard"
    DRUMS = "Drums"
    GHL_GUITAR = "GHLGuitar"  # Guitar (Guitar Hero: Live)
    GHL_BASS = "GHLBass"  # Bass (Guitar Hero: Live)


class Note(Enum):
    """The note lane(s) to which a :class:`~chartparse.instrument.NoteEvent` corresponds."""

    P = bytearray((0, 0, 0, 0, 0))
    G = bytearray((1, 0, 0, 0, 0))
    GR = bytearray((1, 1, 0, 0, 0))
    GY = bytearray((1, 0, 1, 0, 0))
    GB = bytearray((1, 0, 0, 1, 0))
    GO = bytearray((1, 0, 0, 0, 1))
    GRY = bytearray((1, 1, 1, 0, 0))
    GRB = bytearray((1, 1, 0, 1, 0))
    GRO = bytearray((1, 1, 0, 0, 1))
    GYB = bytearray((1, 0, 1, 1, 0))
    GYO = bytearray((1, 0, 1, 0, 1))
    GBO = bytearray((1, 0, 0, 1, 1))
    GRYB = bytearray((1, 1, 1, 1, 0))
    GRYO = bytearray((1, 1, 1, 0, 1))
    GRBO = bytearray((1, 1, 0, 1, 1))
    GYBO = bytearray((1, 0, 1, 1, 1))
    GRYBO = bytearray((1, 1, 1, 1, 1))
    R = bytearray((0, 1, 0, 0, 0))
    RY = bytearray((0, 1, 1, 0, 0))
    RB = bytearray((0, 1, 0, 1, 0))
    RO = bytearray((0, 1, 0, 0, 1))
    RYB = bytearray((0, 1, 1, 1, 0))
    RYO = bytearray((0, 1, 1, 0, 1))
    RBO = bytearray((0, 1, 0, 1, 1))
    RYBO = bytearray((0, 1, 1, 1, 1))
    Y = bytearray((0, 0, 1, 0, 0))
    YB = bytearray((0, 0, 1, 1, 0))
    YO = bytearray((0, 0, 1, 0, 1))
    YBO = bytearray((0, 0, 1, 1, 1))
    B = bytearray((0, 0, 0, 1, 0))
    BO = bytearray((0, 0, 0, 1, 1))
    O = bytearray((0, 0, 0, 0, 1))  # noqa: E741
    # Aliases
    OPEN = bytearray((0, 0, 0, 0, 0))
    GREEN = bytearray((1, 0, 0, 0, 0))
    GREEN_RED = bytearray((1, 1, 0, 0, 0))
    GREEN_YELLOW = bytearray((1, 0, 1, 0, 0))
    GREEN_BLUE = bytearray((1, 0, 0, 1, 0))
    GREEN_ORANGE = bytearray((1, 0, 0, 0, 1))
    GREEN_RED_YELLOW = bytearray((1, 1, 1, 0, 0))
    GREEN_RED_BLUE = bytearray((1, 1, 0, 1, 0))
    GREEN_RED_ORANGE = bytearray((1, 1, 0, 0, 1))
    GREEN_YELLOW_BLUE = bytearray((1, 0, 1, 1, 0))
    GREEN_YELLOW_ORANGE = bytearray((1, 0, 1, 0, 1))
    GREEN_BLUE_ORANGE = bytearray((1, 0, 0, 1, 1))
    GREEN_RED_YELLOW_BLUE = bytearray((1, 1, 1, 1, 0))
    GREEN_RED_YELLOW_ORANGE = bytearray((1, 1, 1, 0, 1))
    GREEN_RED_BLUE_ORANGE = bytearray((1, 1, 0, 1, 1))
    GREEN_YELLOW_BLUE_ORANGE = bytearray((1, 0, 1, 1, 1))
    GREEN_RED_YELLOW_BLUE_ORANGE = bytearray((1, 1, 1, 1, 1))
    RED = bytearray((0, 1, 0, 0, 0))
    RED_YELLOW = bytearray((0, 1, 1, 0, 0))
    RED_BLUE = bytearray((0, 1, 0, 1, 0))
    RED_ORANGE = bytearray((0, 1, 0, 0, 1))
    RED_YELLOW_BLUE = bytearray((0, 1, 1, 1, 0))
    RED_YELLOW_ORANGE = bytearray((0, 1, 1, 0, 1))
    RED_BLUE_ORANGE = bytearray((0, 1, 0, 1, 1))
    RED_YELLOW_BLUE_ORANGE = bytearray((0, 1, 1, 1, 1))
    YELLOW = bytearray((0, 0, 1, 0, 0))
    YELLOW_BLUE = bytearray((0, 0, 1, 1, 0))
    YELLOW_ORANGE = bytearray((0, 0, 1, 0, 1))
    YELLOW_BLUE_ORANGE = bytearray((0, 0, 1, 1, 1))
    BLUE = bytearray((0, 0, 0, 1, 0))
    BLUE_ORANGE = bytearray((0, 0, 0, 1, 1))
    ORANGE = bytearray((0, 0, 0, 0, 1))

    def is_chord(self):
        """Returns whether this ``Note`` has multiple active lanes."""

        return sum(self.value) > 1


class NoteTrackIndex(AllValuesGettableEnum):
    """The integer in a line in a Moonscraper ``.chart`` file's instrument track."""

    G = 0
    R = 1
    Y = 2
    B = 3
    O = 4  # noqa: E741
    P = 7
    FORCED = 5
    TAP = 6
    # Aliases
    GREEN = 0
    RED = 1
    YELLOW = 2
    BLUE = 3
    ORANGE = 4
    OPEN = 7


class InstrumentTrack(EventTrack, DictPropertiesEqMixin, DictReprTruncatedSequencesMixin):
    """All of the instrument-related events for one (instrument, difficulty) pair."""

    instrument: Instrument
    """The instrument to which this track corresponds."""

    difficulty: Difficulty
    """This track's difficulty setting."""

    section_name: str
    """The concatenation of this track's difficulty and instrument (in that order)."""

    note_events: Sequence[NoteEvent]
    """An (instrument, difficulty) pair's ``NoteEvent`` objects."""

    star_power_events: Sequence[StarPowerEvent]
    """An (instrument, difficulty) pair's ``StarPowerEvent`` objects."""

    _min_note_instrument_track_index = 0
    _max_note_instrument_track_index = 4
    _open_instrument_track_index = 7
    _forced_instrument_track_index = 5
    _tap_instrument_track_index = 6

    def __init__(
        self,
        instrument: Instrument,
        difficulty: Difficulty,
        note_events: Sequence[NoteEvent],
        star_power_events: Sequence[StarPowerEvent],
    ) -> None:
        """Instantiates all instance attributes."""

        self.instrument = instrument
        self.difficulty = difficulty
        self.note_events = note_events
        self.star_power_events = star_power_events
        self.section_name = difficulty.value + instrument.value
        self._populate_star_power_data()

    @classmethod
    def from_chart_lines(
        cls: Type[InstrumentTrackT],
        instrument: Instrument,
        difficulty: Difficulty,
        iterator_getter: Callable[[], Iterable[str]],
    ) -> InstrumentTrackT:
        """Initializes instance attributes by parsing an iterable of strings.

        Args:
            iterator_getter: The iterable of strings returned by this strings is most likely from a
                Moonscraper ``.chart``. Must be a function so the strings can be iterated over
                multiple times, if necessary.

        Returns:
            An ``InstrumentTrack`` parsed from the strings returned by ``iterator_getter``.
        """

        note_events = cls._parse_note_events_from_chart_lines(iterator_getter())
        star_power_events = cls._parse_events_from_chart_lines(
            iterator_getter(), StarPowerEvent.from_chart_line
        )
        return cls(instrument, difficulty, note_events, star_power_events)

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"{type(self).__name__}"
            f"(instrument: {self.instrument}, "
            f"difficulty: {self.difficulty}, "
            f"len(note_events): {len(self.note_events)}, "
            f"len(star_power_events): {len(self.star_power_events)})"
        )

    @staticmethod
    def _parse_note_events_from_chart_lines(
        chart_lines: Iterable[str],
    ) -> ImmutableSortedList[NoteEvent]:
        tick_to_note_array: collections.defaultdict[int, bytearray] = collections.defaultdict(
            lambda: bytearray(5)
        )
        tick_to_sustain_list: collections.defaultdict[
            int, list[Optional[int]]
        ] = collections.defaultdict(lambda: [None] * 5)
        tick_to_is_tap = collections.defaultdict(bool)
        tick_to_is_forced = collections.defaultdict(bool)
        for line in chart_lines:
            m = NoteEvent._regex_prog.match(line)
            if not m:
                continue
            tick, note_index, sustain = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if (
                InstrumentTrack._min_note_instrument_track_index
                <= note_index
                <= InstrumentTrack._max_note_instrument_track_index
            ):
                tick_to_note_array[tick][note_index] = 1
                tick_to_sustain_list[tick][note_index] = sustain
            elif note_index == InstrumentTrack._open_instrument_track_index:
                # Because `tick_to_note_array` is a defaultdict, simply accessing it at `tick` is
                # sufficient to conjure a bytearray representing an open note.
                tick_to_note_array[tick]
                tick_to_sustain_list[tick]
            elif note_index == InstrumentTrack._tap_instrument_track_index:
                tick_to_is_tap[tick] = True
            elif note_index == InstrumentTrack._forced_instrument_track_index:
                tick_to_is_forced[tick] = True
            else:  # pragma: no cover
                # TODO: [Logging] Log unhandled instrument track note index.
                pass

        events = []
        for tick in tick_to_note_array.keys():
            note = Note(tick_to_note_array[tick])
            event = NoteEvent(
                tick,
                note,
                sustain=tick_to_sustain_list[tick],
                is_forced=tick_to_is_forced[tick],
                is_tap=tick_to_is_tap[tick],
            )
            events.append(event)
        return ImmutableSortedList(events, key=lambda e: e.tick)

    def _populate_star_power_data(self) -> None:
        num_notes = len(self.note_events)

        note_idx_to_star_power_idx = dict()
        note_idx = 0
        for star_power_idx, star_power_event in enumerate(self.star_power_events):
            start_tick = star_power_event.tick
            end_tick = start_tick + star_power_event.sustain

            # Seek until the first note after this star power phrase.
            while note_idx < num_notes and self.note_events[note_idx].tick < end_tick:
                note = self.note_events[note_idx]
                if start_tick <= note.tick:
                    note_idx_to_star_power_idx[note_idx] = star_power_idx
                note_idx += 1

        for note_idx, note_event in enumerate(self.note_events):
            current_star_power_idx = note_idx_to_star_power_idx.get(note_idx, None)
            if current_star_power_idx is None:
                continue
            next_star_power_idx = note_idx_to_star_power_idx.get(note_idx + 1, None)
            current_note_is_end_of_phrase = current_star_power_idx != next_star_power_idx
            note_event.star_power_data = StarPowerData(
                current_star_power_idx, current_note_is_end_of_phrase
            )


@dataclass
class StarPowerData(DictPropertiesEqMixin):
    """Star power related info for a :class:`~chartparse.instrument.NoteEvent`."""

    star_power_event_idx: int
    is_end_of_phrase: bool


SustainListT = List[Optional[int]]
"""A 5-element list representing the sustain value of each note lane."""

ComplexNoteSustainT = Union[int, SustainListT]
"""A sustain value that can capture multiple coinciding notes with different sustain values.

If this value is an ``int``, it means that all note lanes at this tick value are sustained for the
same length of time.
"""


@enum.unique
class HOPOState(Enum):
    """The manner in which a :class:`~chartparse.instrument.NoteEvent` can/must be hit."""

    STRUM = 0
    HOPO = 1
    TAP = 2


class NoteEvent(Event):
    """An event representing all of the notes at a particular tick.

    A note event's ``str`` representation looks like this::

        NoteEvent(t@0000816 0:00:02.093750): sustain=0: Note.Y [flags=H]

    This event occurs at tick 816 and timestamp 0:00:02.093750. It is not sustained. It is yellow.
    It is a HOPO. Other valid flags are include ``F`` (for "forced"), ``T`` (for "tap"), and ``S``
    (for "strum").

    """

    note: Note
    """The note lane(s) that are active."""

    sustain: ComplexNoteSustainT
    """Information about this note event's sustain value."""

    # TODO: Figure out a way for ``hopo_state`` to not be Optional.
    hopo_state: Optional[HOPOState]
    """Whether the note is a strum, a HOPO, or a tap note.

    Optional, as it may need to be calculated later.
    """

    star_power_data: Optional[StarPowerData]
    """Information associated with star power for this note.

    If this is ``None``, then the note is not a star power note.
    """

    _is_forced: bool

    _is_tap: bool

    # This regex matches a single "N" line within a instrument track section,
    # but this class should be used to represent all of the notes at a
    # particular tick. This means that you might need to consolidate multiple
    # "N" lines into a single NoteEvent, e.g. for chords.
    # Match 1: Tick
    # Match 2: Note index
    # Match 3: Sustain (ticks)
    _regex: str = r"^\s*?(\d+?) = N ([0-7]) (\d+?)\s*?$"
    _regex_prog: Pattern[str] = re.compile(_regex)

    def __init__(
        self,
        tick: int,
        note: Note,
        timestamp: Optional[datetime.timedelta] = None,
        sustain: ComplexNoteSustainT = 0,
        is_forced: bool = False,
        is_tap: bool = False,
        star_power_data: Optional[StarPowerData] = None,
    ) -> None:
        self._validate_sustain(sustain, note)
        super().__init__(tick, timestamp=timestamp)
        self.note = note
        self.sustain = self._refine_sustain(sustain)
        self._is_forced = is_forced
        self._is_tap = is_tap
        self.star_power_data = star_power_data

    @staticmethod
    def _validate_sustain(sustain: ComplexNoteSustainT, note: Note) -> None:
        if isinstance(sustain, int):
            NoteEvent._validate_int_sustain(sustain)
        elif isinstance(sustain, list):
            NoteEvent._validate_list_sustain(sustain, note)
        else:
            raise TypeError(f"sustain {sustain} must be type list, or int.")

    @staticmethod
    def _validate_int_sustain(sustain: int) -> None:
        if sustain < 0:
            raise ValueError(f"int sustain {sustain} must be positive.")

    @staticmethod
    def _validate_list_sustain(sustain: SustainListT, note: Note) -> None:
        if len(sustain) != len(note.value):
            raise ValueError(f"list sustain {sustain} must have length {len(note.value)}")
        for note_lane_value, sustain_lane_value in zip(note.value, sustain):
            lane_is_active = note_lane_value == 1
            sustain_is_set = sustain_lane_value is not None
            if lane_is_active != sustain_is_set:
                raise ValueError(
                    f"list sustain {sustain} must have "
                    "values for exactly the active note lanes."
                )

    @staticmethod
    def _refine_sustain(sustain: ComplexNoteSustainT) -> ComplexNoteSustainT:
        if isinstance(sustain, list):
            if all(d is None for d in sustain):
                return 0
            first_non_none_sustain = next(d for d in sustain if d is not None)
            if all(d is None or d == first_non_none_sustain for d in sustain):
                return first_non_none_sustain
        return sustain

    def _populate_hopo_state(self, resolution: int, previous: Union[NoteEvent, None]) -> None:
        self.hopo_state = self._compute_hopo_state(resolution, self, previous)

    @staticmethod
    def _compute_hopo_state(
        resolution: int, current: NoteEvent, previous: Union[NoteEvent, None]
    ) -> HOPOState:
        if current._is_tap:
            return HOPOState.TAP

        # The Moonscraper UI does not allow the first note to be forced, so it must be a strum if
        # it is not a tap.
        if previous is None:
            return HOPOState.STRUM

        eighth_triplet_tick_boundary = chartparse.tick.calculate_ticks_between_notes(
            resolution, NoteDuration.EIGHTH_TRIPLET
        )
        ticks_since_previous = current.tick - previous.tick
        previous_is_within_eighth_triplet = ticks_since_previous <= eighth_triplet_tick_boundary
        previous_note_is_different = current.note != previous.note
        should_be_hopo = (
            previous_is_within_eighth_triplet
            and previous_note_is_different
            and not current.note.is_chord()
        )

        if should_be_hopo != current._is_forced:
            return HOPOState.HOPO
        else:
            return HOPOState.STRUM

    def __str__(self) -> str:  # pragma: no cover
        to_join = [super().__str__()]
        to_join.append(f": sustain={self.sustain}")
        to_join.append(f": {self.note}")

        if self.star_power_data:
            to_join.append("*")

        flags = []
        if hasattr(self, "hopo_state") and self.hopo_state is not None:
            if self.hopo_state == HOPOState.TAP:
                flags.append("T")
            elif self.hopo_state == HOPOState.HOPO:
                flags.append("H")
            elif self.hopo_state == HOPOState.STRUM:
                flags.append("S")
        else:
            if self._is_forced:
                flags.append("F")
            if self._is_tap:
                flags.append("T")
        if flags:
            to_join.extend([" [hopo_state=", "".join(flags), "]"])

        return "".join(to_join)


SpecialEventT = TypeVar("SpecialEventT", bound="SpecialEvent")


class SpecialEvent(Event):
    """Provides a regex template for parsing 'S' style chart lines.

    This is typically used only as a base class for more specialized subclasses.

    Attributes:
        sustain: The number of ticks for which this event is sustained. This event does _not_
            overlap events at ``tick + sustain``; it ends immediately before that tick.
    """

    # Match 1: Tick
    # Match 2: Sustain (ticks)
    _regex_template: ClassVar[str] = r"^\s*?(\d+?) = S {} (\d+?)\s*?$"

    _regex: str
    _regex_prog: Pattern[str]

    def __init__(
        self, tick: int, sustain: int, timestamp: Optional[datetime.timedelta] = None
    ) -> None:
        super().__init__(tick, timestamp=timestamp)
        self.sustain = sustain

    @classmethod
    def from_chart_line(cls: Type[SpecialEventT], line: str) -> SpecialEventT:
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
        tick, sustain = int(m.group(1)), int(m.group(2))
        return cls(tick, sustain)

    def __str__(self) -> str:  # pragma: no cover
        to_join = [super().__str__()]
        to_join.append(f": sustain={self.sustain}")
        return "".join(to_join)


class StarPowerEvent(SpecialEvent):
    """An event representing star power starting at some tick and lasting for some duration."""

    _regex = SpecialEvent._regex_template.format(r"2")
    _regex_prog = re.compile(_regex)


# TODO: Support S 0 ## and S 1 ## (GH1/2 Co-op)


# TODO: Support S 64 ## (Rock Band drum fills)
