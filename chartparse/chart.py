"""For representing the data of a ``.chart`` file as a object.

This module is the main entrypoint to this package. Typically, a
developer needs only to create a ``Chart`` object and then inspect
its attributes:

Example:
    Creating a ``Chart`` object::

        from chartparse.chart import Chart

        chart = Chart.from_file("path/to/file.chart")

.. _Google Python Style Guide:
    http://google.github.io/styleguide/pyguide.html

"""

from __future__ import annotations

import collections
import datetime
import itertools
import re
import typing
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import Optional, TextIO

from chartparse.event import Event
from chartparse.exceptions import RegexNotMatchError
from chartparse.globalevents import GlobalEventsTrack
from chartparse.hints import T
from chartparse.instrument import Difficulty, Instrument, InstrumentTrack, NoteEvent
from chartparse.metadata import Metadata
from chartparse.sync import SyncTrack
from chartparse.util import DictPropertiesEqMixin, DictReprTruncatedSequencesMixin

_max_timedelta = datetime.datetime.max - datetime.datetime.min


class Chart(DictPropertiesEqMixin, DictReprTruncatedSequencesMixin):
    """A Clone Hero / Moonscraper chart and its relevant gameplay data.

    While it is possible to create this with its initializer, as a user, you will most likely have
    a ``.chart`` file and not the constituent objects necessary to use ``__init__``. To initialize
    a ``Chart`` from a file, you should instead use :meth:`~chartparse.chart.Chart.from_file`.
    """

    metadata: Metadata
    """The chart's metadata, such as song title or charter name."""

    global_events_track: GlobalEventsTrack
    """Contains the chart's :class:`~chartparse.globalevents.GlobalEvent` objects"""

    sync_track: SyncTrack
    """Contains the chart's sync-related events."""

    instrument_tracks: dict[Instrument, dict[Difficulty, InstrumentTrack]]
    """Contains all of the chart's :class:`~chartparse.instrument.InstrumentTrack` objects."""

    def __init__(
        self,
        metadata: Metadata,
        global_events_track: GlobalEventsTrack,
        sync_track: SyncTrack,
        instrument_tracks: dict[Instrument, dict[Difficulty, InstrumentTrack]],
    ) -> None:
        """Instantiates all instance attributes and populates timestamps & note HOPO states."""

        self.metadata = metadata
        self.global_events_track = global_events_track
        self.sync_track = sync_track
        self.instrument_tracks = instrument_tracks

        self._populate_bpm_event_timestamps()
        self._populate_event_timestamps(self.sync_track.time_signature_events)
        self._populate_event_timestamps(self.global_events_track.text_events)
        self._populate_event_timestamps(self.global_events_track.section_events)
        self._populate_event_timestamps(self.global_events_track.lyric_events)
        for instrument, difficulties in self.instrument_tracks.items():
            for difficulty, track in difficulties.items():
                self._populate_event_timestamps(track.note_events)
                self._populate_event_timestamps(track.star_power_events)
                self._populate_note_event_hopo_states(track.note_events)

    _required_sections = ("Song", "SyncTrack")
    _instrument_track_name_to_instrument_difficulty_pair = {
        d + i: (Instrument(i), Difficulty(d))
        for i, d in typing.cast(
            Iterable[tuple[str, str]],
            itertools.product(Instrument.all_values(), Difficulty.all_values()),
        )
    }

    @classmethod
    def from_filepath(cls, path: Path) -> Chart:
        """Given a path, parses the contents of its file and returns a new Chart.

        Args:
            path: A ``Path`` object that points to a ``.chart`` file written by Moonscraper. Must
                have a ``[Song]`` section and a ``[SyncTrack]`` section.

        Returns:
            A ``Chart`` object, initialized with data parsed from ``path``.
        """
        with open(path, "r", encoding="utf-8-sig") as f:
            return Chart.from_file(f)

    @classmethod
    def from_file(cls, fp: TextIO) -> Chart:
        """Given a file object, parses its contents and returns a new Chart.

        Args:
            fp: A file object that allows reading from a .chart file written by Moonscraper.  Must
                have a ``[Song]`` section and a ``[SyncTrack]`` section.

        Returns:
            A ``Chart`` object, initialized with data parsed from ``fp``.
        """
        lines = fp.read().splitlines()
        sections = cls._find_sections(lines)
        if not all(section in sections for section in cls._required_sections):
            raise ValueError(
                f"parsed section list {list(sections.keys())} does not contain all "
                f"required sections {cls._required_sections}"
            )

        instrument_tracks: collections.defaultdict[
            Instrument, dict[Difficulty, InstrumentTrack]
        ] = collections.defaultdict(dict)
        for section_name, iterator_getter in sections.items():
            if section_name == Metadata.section_name:
                metadata = Metadata.from_chart_lines(iterator_getter)
            elif section_name == GlobalEventsTrack.section_name:
                global_events_track = GlobalEventsTrack.from_chart_lines(iterator_getter)
            elif section_name == SyncTrack.section_name:
                sync_track = SyncTrack.from_chart_lines(iterator_getter)
            elif section_name in cls._instrument_track_name_to_instrument_difficulty_pair:
                instrument, difficulty = cls._instrument_track_name_to_instrument_difficulty_pair[
                    section_name
                ]
                track = InstrumentTrack.from_chart_lines(instrument, difficulty, iterator_getter)
                instrument_tracks[instrument][difficulty] = track
            # TODO: [Logging] Log unhandled sections.

        return cls(metadata, global_events_track, sync_track, instrument_tracks)

    _section_name_regex = r"^\[(.+?)\]$"
    _section_name_regex_prog = re.compile(_section_name_regex)

    @classmethod
    def _find_sections(cls, lines: Iterable[str]) -> dict[str, Callable[[], Iterable[str]]]:
        sections: dict[str, Callable[[], Iterable[str]]] = dict()
        curr_section_name = None
        curr_first_line_idx = None
        curr_last_line_idx = None
        for i, line in enumerate(lines):
            if curr_section_name is None:
                m = cls._section_name_regex_prog.match(line)
                if not m:
                    raise RegexNotMatchError(cls._section_name_regex, line)
                curr_section_name = m.group(1)
            elif line == "{":
                curr_first_line_idx = i + 1
            elif line == "}":
                curr_last_line_idx = i - 1
                # Set default values for x and y so their current values are
                # captured, rather than references to these local variables.
                iterator_getter = (
                    lambda x=curr_first_line_idx, y=curr_last_line_idx: itertools.islice(
                        lines, x, y + 1
                    )
                )
                sections[curr_section_name] = iterator_getter
                curr_section_name = None
                curr_first_line_idx = None
                curr_last_line_idx = None
        return sections

    def _populate_bpm_event_timestamps(self) -> None:
        self.sync_track.bpm_events[0].timestamp = datetime.timedelta(0)
        for i, cur_event in enumerate(
            _iterate_from_second_elem(self.sync_track.bpm_events), start=1
        ):
            prev_event = self.sync_track.bpm_events[i - 1]
            assert prev_event.timestamp is not None
            ticks_since_prev = cur_event.tick - prev_event.tick
            seconds_since_prev = self._seconds_from_ticks_at_bpm(ticks_since_prev, prev_event.bpm)
            cur_event.timestamp = prev_event.timestamp + datetime.timedelta(
                seconds=seconds_since_prev
            )

    def _populate_event_timestamps(self, events: Iterable[Event]) -> None:
        proximal_bpm_event_idx = 0
        for i, event in enumerate(events):
            timestamp, proximal_bpm_event_idx = self._timestamp_at_tick(
                event.tick,
                start_bpm_event_index=proximal_bpm_event_idx,
            )
            event.timestamp = timestamp

    def _populate_note_event_hopo_states(self, events: Sequence[NoteEvent]) -> None:
        if not events:
            return

        for i, cur_event in enumerate(events):
            previous_event = events[i - 1] if i > 0 else None
            cur_event._populate_hopo_state(self.metadata.resolution, previous_event)

    def _timestamp_at_tick(
        self, tick: int, start_bpm_event_index: int = 0
    ) -> tuple[datetime.timedelta, int]:
        proximal_bpm_event_idx = self.sync_track.idx_of_proximal_bpm_event(
            tick, start_idx=start_bpm_event_index
        )
        proximal_bpm_event = self.sync_track.bpm_events[proximal_bpm_event_idx]
        assert proximal_bpm_event.timestamp is not None
        ticks_since_proximal_bpm_event = tick - proximal_bpm_event.tick
        seconds_since_proximal_bpm_event = self._seconds_from_ticks_at_bpm(
            ticks_since_proximal_bpm_event, proximal_bpm_event.bpm
        )
        timedelta_since_proximal_bpm_event = datetime.timedelta(
            seconds=seconds_since_proximal_bpm_event
        )
        timestamp = proximal_bpm_event.timestamp + timedelta_since_proximal_bpm_event
        return timestamp, proximal_bpm_event_idx

    def _seconds_from_ticks_at_bpm(self, ticks: int, bpm: float) -> float:
        if bpm <= 0:
            raise ValueError(f"bpm {bpm} must be positive")
        ticks_per_minute = bpm * self.metadata.resolution
        ticks_per_second = ticks_per_minute / 60
        seconds_per_tick = 1 / ticks_per_second
        return ticks * seconds_per_tick

    # TODO: Calculate this over the actual interval, not the interval formed by the first and last
    # notes.
    def notes_per_second(
        self,
        instrument: Instrument,
        difficulty: Difficulty,
        start_time: Optional[datetime.timedelta] = None,
        end_time: Optional[datetime.timedelta] = None,
        start_tick: Optional[int] = None,
        end_tick: Optional[int] = None,
        start_seconds: Optional[float] = None,
        end_seconds: Optional[float] = None,
    ) -> float:
        """Returns the average notes per second from the first and last note in the interval.

        More specifically, this calculates the number of :class:`~chartparse.instrument.NoteEvent`
        objects per second. Chords do not count as multiple "notes" in one instant.

        The interval is always a closed interval.

        You may pass one or zero of ``start_time``, ``start_tick``, and ``start_seconds``, or else
        ``ValueError`` will be raised.  If none of ``start_time``, ``start_tick``, and
        ``start_seconds`` are passed, the beginning of the track will be treated as the start of
        the interval.  If none of ``end_time``, ``end_tick``, and ``end_seconds`` are passed, the
        end of the track will be treated as the end of the interval.

        Args:
            instrument: The instrument for which the
                :class:`~chartparse.instrument.InstrumentTrack` should be looked up.
            difficulty: The instrument for which the
                :class:`~chartparse.instrument.InstrumentTrack` should be looked up.
            start_time: The beginning of the interval.
            end_time: The end of the interval.
            start_tick: The beginning of the interval.
            end_tick: The end of the interval.
            start_seconds: The beginning of the interval.
            end_seconds: The end of the interval.

        Returns:
            The average notes per second value over the interval formed by the first and last note.

        Raises:
            ValueError: If more than one of ``start_time``, ``start_tick``, and ``start_seconds``
                is ``None``.
            ValueError: If there is no :class:`~chartparse.instrument.InstrumentTrack`
                corresponding to ``instrument`` and ``difficulty``.
            ValueError: If there are fewer than two :class:`~chartparse.instrument.NoteEvent`
                objects within the indicated interval.
        """

        start_args = (start_time, start_seconds, start_tick)
        num_of_start_args_none = start_args.count(None)
        if num_of_start_args_none < 2:
            raise ValueError(
                f"no more than one of start_time {start_time}, start_seconds {start_seconds}, "
                f"and start_tick {start_tick} can be non-None"
            )
        all_start_args_none = num_of_start_args_none == len(start_args)

        def event_is_eligible_by_tick(note: NoteEvent) -> bool:
            lower_bound: int = start_tick if start_tick is not None else 0
            upper_bound: float = end_tick if end_tick is not None else float("inf")
            return lower_bound <= note.tick <= upper_bound

        def event_is_eligible_by_time(note: NoteEvent) -> bool:
            assert note.timestamp is not None
            lower_bound: datetime.timedelta = (
                start_time if start_time is not None else datetime.timedelta(0)
            )
            upper_bound: datetime.timedelta = end_time if end_time is not None else _max_timedelta
            return lower_bound <= note.timestamp <= upper_bound

        def event_is_eligible_by_seconds(note: NoteEvent) -> bool:
            assert note.timestamp is not None
            lower_bound: datetime.timedelta = (
                datetime.timedelta(seconds=start_seconds)
                if start_seconds is not None
                else datetime.timedelta(0)
            )
            upper_bound: datetime.timedelta = (
                datetime.timedelta(seconds=end_seconds)
                if end_seconds is not None
                else _max_timedelta
            )
            return lower_bound <= note.timestamp <= upper_bound

        if (start_tick is not None) or all_start_args_none:
            event_is_eligible_fn = event_is_eligible_by_tick
        elif start_time is not None:
            event_is_eligible_fn = event_is_eligible_by_time
        elif start_seconds is not None:
            event_is_eligible_fn = event_is_eligible_by_seconds
        else:
            raise RuntimeError(
                "unhandled input combination; should be impossible"
            )  # pragma: no cover

        try:
            track = self.instrument_tracks[instrument][difficulty]
        except KeyError:
            raise ValueError(
                f"no instrument track for difficulty {difficulty} instrument {instrument}"
            )
        events_to_consider = list(filter(event_is_eligible_fn, track.note_events))
        if len(events_to_consider) < 2:
            raise ValueError(
                "cannot determine average notes per second value of phrase with fewer than 2 "
                f"Events: {events_to_consider}"
            )

        return self._notes_per_second_from_events(events_to_consider)

    @staticmethod
    def _notes_per_second_from_events(events: Sequence[NoteEvent]) -> float:
        first_event = events[0]
        last_event = events[-1]
        assert first_event.timestamp is not None
        assert last_event.timestamp is not None
        phrase_duration_seconds = (last_event.timestamp - first_event.timestamp).total_seconds()
        return len(events) / phrase_duration_seconds

    def __str__(self) -> str:  # pragma: no cover
        items = []
        if hasattr(self, "metadata"):
            items.append(f"{self.metadata}")
        if hasattr(self, "global_events_track"):
            items.append(f"{self.global_events_track}")
        if hasattr(self, "sync_track"):
            items.append(f"{self.sync_track}")
        if hasattr(self, "instrument_tracks"):
            for _, difficulty_dict in self.instrument_tracks.items():
                for _, track in difficulty_dict.items():
                    items.append(f"{track}")

        item_string = ",\n  ".join(items)
        return f"{type(self).__name__}(\n  {item_string})"


def _iterate_from_second_elem(xs: Sequence[T]) -> Iterator[T]:
    """Given an iterable ``xs``, return an iterator that skips ``xs[0]``.

    Args:
        xs: Any non-exhausted iterable.

    Returns:
        A iterator that iterates over ``xs``, ignoring the first element.
    """
    it = iter(xs)
    next(it)
    yield from it
