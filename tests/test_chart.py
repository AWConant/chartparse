import datetime
import pathlib
import pytest
import unittest.mock

from chartparse.chart import Chart, _iterate_from_second_elem, _max_timedelta, _zero_timedelta
from chartparse.exceptions import RegexNotMatchError
from chartparse.globalevents import GlobalEventsTrack, LyricEvent
from chartparse.instrument import NoteEvent, InstrumentTrack, Difficulty, Instrument, Note
from chartparse.metadata import Metadata
from chartparse.sync import SyncTrack, BPMEvent


_directory_of_this_file = pathlib.Path(__file__).parent.resolve()
_chart_directory_filepath = _directory_of_this_file / "data"
_valid_chart_filepath = _chart_directory_filepath / "test.chart"
_missing_metadata_chart_filepath = _chart_directory_filepath / "missing_metadata.chart"
_missing_sync_track_chart_filepath = _chart_directory_filepath / "missing_sync_track.chart"


class TestChartInit(object):
    def test_basic(
        self,
        mocker,
        basic_metadata,
        basic_global_events_track,
        basic_sync_track,
        basic_instrument_track,
        basic_instrument_tracks,
    ):
        mock_populate_bpm_event_timestamps = mocker.patch.object(
            Chart, "_populate_bpm_event_timestamps"
        )
        mock_populate_event_timestamps = mocker.patch.object(Chart, "_populate_event_timestamps")
        mock_populate_event_hopo_states = mocker.patch.object(
            Chart, "_populate_note_event_hopo_states"
        )
        mock_populate_last_note_timestamp = mocker.patch.object(
            Chart, "_populate_last_note_timestamp"
        )
        c = Chart(
            basic_metadata, basic_global_events_track, basic_sync_track, basic_instrument_tracks
        )

        assert c.metadata == basic_metadata
        assert c.global_events_track == basic_global_events_track
        assert c.sync_track == basic_sync_track
        assert c.instrument_tracks == basic_instrument_tracks

        mock_populate_bpm_event_timestamps.assert_called_once()
        mock_populate_event_timestamps.assert_has_calls(
            [
                unittest.mock.call(basic_sync_track.time_signature_events),
                unittest.mock.call(basic_global_events_track.text_events),
                unittest.mock.call(basic_global_events_track.section_events),
                unittest.mock.call(basic_global_events_track.lyric_events),
                unittest.mock.call(basic_instrument_track.note_events),
                unittest.mock.call(basic_instrument_track.star_power_events),
            ],
            any_order=True,
        )
        mock_populate_event_hopo_states.assert_called_once_with(basic_instrument_track.note_events)
        mock_populate_last_note_timestamp.assert_called_once_with(basic_instrument_track)


class TestChartAlternateInitializers(object):
    def test_basic(
        self,
        mocker,
        placeholder_string_iterator_getter,
        basic_chart,
        basic_metadata,
        basic_global_events_track,
        basic_sync_track,
        basic_instrument_track,
    ):
        mocker.patch.object(
            Chart,
            "_find_sections",
            return_value={
                "Song": placeholder_string_iterator_getter,
                "Events": placeholder_string_iterator_getter,
                "SyncTrack": placeholder_string_iterator_getter,
                "ExpertSingle": placeholder_string_iterator_getter,
            },
        )
        mocker.patch.object(Metadata, "from_chart_lines", return_value=basic_metadata)
        mocker.patch.object(
            GlobalEventsTrack, "from_chart_lines", return_value=basic_global_events_track
        )
        mocker.patch.object(SyncTrack, "from_chart_lines", return_value=basic_sync_track)
        mocker.patch.object(
            InstrumentTrack, "from_chart_lines", return_value=basic_instrument_track
        )
        with open(_valid_chart_filepath, "r", encoding="utf-8-sig") as f:
            assert Chart.from_file(f) == basic_chart
        assert Chart.from_filepath(_valid_chart_filepath) == basic_chart

    @pytest.mark.parametrize(
        "path",
        [
            pytest.param(_missing_metadata_chart_filepath, id="missing_metadata"),
            pytest.param(_missing_sync_track_chart_filepath, id="missing_sync_track"),
        ],
    )
    def test_invalid_chart(self, path):
        with open(path, "r", encoding="utf-8-sig") as f, pytest.raises(ValueError):
            _ = Chart.from_file(f)


class TestFindSections(object):
    def test_basic(self):
        # TODO: Reconstruct file contents from want_lines rather than having an actual file.
        with open(_valid_chart_filepath, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()

        sections = Chart._find_sections(lines)

        def validate_lines(section_name, want_lines):
            assert section_name in sections
            lines_getter = sections[section_name]
            assert list(lines_getter()) == want_lines

        validate_lines(
            "Events",
            [
                '  800 = E "section Section 1"',
                '  1000 = E "phrase_start"',
                '  1200 = E "lyric Lo-"',
                '  1230 = E "lyric rem"',
                '  1800 = E "lyric ip-"',
                '  1840 = E "lyric sum"',
            ],
        )

        validate_lines(
            "Song",
            [
                '  Name = "Song Name"',
                '  Artist = "Artist Name"',
                '  Charter = "Charter Name"',
                '  Album = "Album Name"',
                '  Year = "1999"',
                "  Offset = 0",
                "  Resolution = 100",
                "  Player2 = bass",
                "  Difficulty = 6",
                "  PreviewStart = 0",
                "  PreviewEnd = 0",
                '  Genre = "rock"',
                '  MediaType = "cd"',
                '  MusicStream = "song.ogg"',
            ],
        )

        validate_lines(
            "SyncTrack",
            [
                "  0 = TS 4",
                "  0 = B 117000",
                "  800 = B 120000",
                "  1200 = B 90000",
                "  1200 = TS 6 3",
                "  1800 = B 100000",
            ],
        )

        validate_lines(
            "ExpertSingle",
            [
                "  800 = N 0 0",
                "  800 = N 2 0",
                "  825 = N 0 0",
                "  825 = N 5 0 ",
                "  900 = N 0 0",
                "  1000 = N 0 0",
                "  1000 = N 2 0",
                "  1000 = S 2 100",
                "  1100 = N 0 0",
                "  1100 = N 5 0 ",
                "  1150 = N 0 0",
                "  1200 = N 0 0",
                "  1200 = S 2 200",
                "  1225 = N 0 0",
                "  1300 = N 0 0",
                "  1300 = N 3 0",
                "  2000 = N 0 0",
            ],
        )

    @pytest.mark.parametrize(
        "lines",
        [
            ["Song]", "{", '  Name = "Song Name"', "}"],
            ["[Song]", "{", '  Name = "Song Name"', "}", "[ExpertSingle"],
        ],
    )
    def test_find_sections_raises(self, lines):
        with pytest.raises(RegexNotMatchError):
            _ = Chart._find_sections(lines)


def assert_event_timestamps(got_events, want_timestamps):
    assert len(got_events) == len(want_timestamps)
    for got_event, want_timestamp in zip(got_events, want_timestamps):
        assert got_event.timestamp == want_timestamp


class TestPopulateEventTimestamps(object):
    test_bpm_events = [
        BPMEvent(0, 117.000),
        BPMEvent(800, 120.000),
        BPMEvent(1200, 90.000),
        BPMEvent(1800, 100.000),
    ]

    @pytest.mark.parametrize(
        "bpm_events,want_timestamps",
        [
            pytest.param(
                test_bpm_events,
                [
                    datetime.timedelta(0),
                    datetime.timedelta(seconds=4.102564),
                    datetime.timedelta(seconds=6.102564),
                    datetime.timedelta(seconds=10.102564),
                ],
            ),
        ],
    )
    def test_populate_bpm_event_timestamps(
        self, mocker, bpm_events, want_timestamps, bare_chart, bare_metadata
    ):
        bare_metadata.resolution = 100
        bare_chart.metadata = bare_metadata
        bare_chart.sync_track = SyncTrack(pytest.default_time_signature_event_list, bpm_events)
        bare_chart._populate_bpm_event_timestamps()
        assert_event_timestamps(bare_chart.sync_track.bpm_events, want_timestamps)

    def test_populate_event_timestamps(self, bare_chart, bare_metadata):
        bare_metadata.resolution = 100
        bare_chart.metadata = bare_metadata
        bare_chart.sync_track = SyncTrack(
            pytest.default_time_signature_event_list, self.test_bpm_events
        )
        bare_chart.global_events_track = GlobalEventsTrack(
            [],
            [],
            [
                LyricEvent(1200, "Lo-"),
                LyricEvent(1230, "rem"),
                LyricEvent(1800, "ip-"),
                LyricEvent(1840, "sum"),
            ],
        )
        bare_chart._populate_event_timestamps(bare_chart.global_events_track.lyric_events)

        assert_event_timestamps(
            bare_chart.global_events_track.lyric_events,
            [
                datetime.timedelta(seconds=6.102564),
                datetime.timedelta(seconds=6.302564),
                datetime.timedelta(seconds=10.102564),
                datetime.timedelta(seconds=10.342564),
            ],
        )


class TestPopulateNoteEventHOPOStates(object):
    def test_basic(self, mocker, bare_chart, bare_metadata):
        note_event1 = NoteEvent(0, Note.G)
        note_event2 = NoteEvent(pytest.default_resolution, Note.R)
        note_event3 = NoteEvent(pytest.default_resolution + pytest.default_resolution * 2, Note.Y)
        note_events = [note_event1, note_event2, note_event3]
        # TODO: Make it simpler to create a bare chart with a resolution.
        bare_metadata.resolution = pytest.default_resolution
        bare_chart.metadata = bare_metadata

        mock_populate_hopo_state1 = mocker.patch.object(note_event1, "_populate_hopo_state")
        mock_populate_hopo_state2 = mocker.patch.object(note_event2, "_populate_hopo_state")
        mock_populate_hopo_state3 = mocker.patch.object(note_event3, "_populate_hopo_state")

        bare_chart._populate_note_event_hopo_states(note_events)

        mock_populate_hopo_state1.assert_called_once_with(pytest.default_resolution, None)
        mock_populate_hopo_state2.assert_called_once_with(pytest.default_resolution, note_event1)
        mock_populate_hopo_state3.assert_called_once_with(pytest.default_resolution, note_event2)

    def test_empty(self, bare_chart, bare_metadata):
        bare_metadata.resolution = pytest.default_resolution
        bare_chart.metadata = bare_metadata
        note_events = []
        bare_chart._populate_note_event_hopo_states(note_events)
        assert not note_events


class TestPopulateLastNoteTimestamp(object):
    @pytest.mark.parametrize(
        "note_events,want",
        [
            pytest.param([NoteEvent(1, pytest.default_note)], 1),
            pytest.param(
                [NoteEvent(1, pytest.default_note), NoteEvent(2, pytest.default_note)], 2
            ),
            pytest.param([NoteEvent(1, pytest.default_note, sustain=100)], 101),
        ],
    )
    def test_basic(self, mocker, bare_chart, bare_instrument_track, note_events, want):
        mock_timestamp_at_tick = mocker.patch.object(
            Chart, "_timestamp_at_tick", return_value=(None, None)
        )
        bare_instrument_track.note_events = note_events
        bare_chart._populate_last_note_timestamp(bare_instrument_track)
        mock_timestamp_at_tick.assert_called_once_with(want)

    def test_empty(self, mocker, bare_chart, bare_instrument_track):
        mock_timestamp_at_tick = mocker.patch.object(
            Chart, "_timestamp_at_tick", return_value=(None, None)
        )
        bare_instrument_track.note_events = []
        bare_chart._populate_last_note_timestamp(bare_instrument_track)
        mock_timestamp_at_tick.assert_not_called()


class TestTimestampAtTick(object):
    test_bpm_events = [
        BPMEvent(0, 60.000),
        BPMEvent(100, 120.000),
        BPMEvent(400, 180.000),
        BPMEvent(800, 90.000),
    ]

    @pytest.mark.parametrize(
        # TODO: Move test_bpm_events to be a parameter. This might mutate the list, screwing up
        # the case where there are multiple test cases.
        "resolution,tick,want_timestamp,want_proximal_bpm_event_idx",
        [
            pytest.param(100, 100, datetime.timedelta(seconds=1), 1),
            pytest.param(100, 120, datetime.timedelta(seconds=1.1), 1),
            pytest.param(100, 400, datetime.timedelta(seconds=2.5), 2),
            pytest.param(100, 1000, datetime.timedelta(seconds=5.166666), 3),
        ],
    )
    def test_basic(
        self,
        bare_chart,
        bare_metadata,
        resolution,
        tick,
        want_timestamp,
        want_proximal_bpm_event_idx,
    ):
        bare_metadata.resolution = resolution
        bare_chart.metadata = bare_metadata
        bare_chart.sync_track = SyncTrack(
            pytest.default_time_signature_event_list, self.test_bpm_events
        )
        bare_chart._populate_bpm_event_timestamps()
        timestamp, proximal_bpm_event_idx = bare_chart._timestamp_at_tick(tick)
        assert timestamp == want_timestamp
        assert proximal_bpm_event_idx == want_proximal_bpm_event_idx


class TestSecondsFromTicksAtBPM(object):
    @pytest.mark.parametrize(
        "resolution,ticks,bpm,want",
        [
            pytest.param(100, 100, 60, 1),
            pytest.param(100, 100, 120, 0.5),
            pytest.param(100, 200, 120, 1),
            pytest.param(100, 400, 200, 1.2),
            pytest.param(200, 100, 60, 0.5),
        ],
    )
    def test_basic(self, bare_chart, bare_metadata, ticks, bpm, resolution, want):
        bare_metadata.resolution = resolution
        bare_chart.metadata = bare_metadata
        assert bare_chart._seconds_from_ticks_at_bpm(ticks, bpm) == want

    @pytest.mark.parametrize(
        "ticks,bpm,resolution",
        [
            pytest.param(100, -1, 192, id="negative_bpm"),
            pytest.param(100, 0, 192, id="zero_bpm"),
        ],
    )
    def test_error(self, bare_chart, ticks, bpm, resolution):
        with pytest.raises(ValueError):
            _ = bare_chart._seconds_from_ticks_at_bpm(ticks, bpm)


class TestNotesPerSecond(object):
    note_event1 = NoteEvent(
        pytest.default_resolution, Note.GRY, timestamp=datetime.timedelta(seconds=1)
    )
    note_event2 = NoteEvent(
        pytest.default_resolution * 2, Note.RYB, timestamp=datetime.timedelta(seconds=2)
    )
    note_event3 = NoteEvent(
        pytest.default_resolution * 3, Note.YBO, timestamp=datetime.timedelta(seconds=3)
    )
    test_notes_per_second_note_events = [note_event1, note_event2, note_event3]

    @pytest.mark.parametrize(
        "lower_bound,upper_bound,want",
        [
            pytest.param(
                datetime.timedelta(seconds=1),
                datetime.timedelta(seconds=3),
                3 / 2,
            ),
            pytest.param(
                datetime.timedelta(seconds=2),
                datetime.timedelta(seconds=3),
                2,
            ),
            pytest.param(
                datetime.timedelta(seconds=2),
                datetime.timedelta(seconds=4),
                1,
            ),
        ],
    )
    def test_from_note_events(self, bare_chart, lower_bound, upper_bound, want):
        assert (
            bare_chart._notes_per_second(
                self.test_notes_per_second_note_events, lower_bound, upper_bound
            )
            == want
        )

    @pytest.mark.parametrize(
        "start_tick,end_tick,want_lower_bound,want_upper_bound",
        [
            pytest.param(
                None, 2, _zero_timedelta, datetime.timedelta(seconds=2), id="all_start_args_none"
            ),
            pytest.param(1, None, datetime.timedelta(seconds=1), _max_timedelta, id="last_none"),
            pytest.param(
                1, 2, datetime.timedelta(seconds=1), datetime.timedelta(seconds=2), id="no_none"
            ),
        ],
    )
    def test_with_ticks(
        self, mocker, bare_chart, start_tick, end_tick, want_lower_bound, want_upper_bound
    ):
        instrument_track = InstrumentTrack(
            pytest.default_instrument,
            pytest.default_difficulty,
            [],
            [],
        )
        instrument_track._last_note_timestamp = _max_timedelta
        bare_chart.instrument_tracks = {
            pytest.default_instrument: {
                pytest.default_difficulty: instrument_track,
            }
        }

        def tick_to_bound(tick):
            return datetime.timedelta(seconds=tick)

        def timestamp_at_tick_side_effect(tick):
            return (tick_to_bound(tick),)

        mock_timestamp_at_tick = mocker.patch.object(
            Chart,
            "_timestamp_at_tick",
            side_effect=timestamp_at_tick_side_effect,
        )
        spy = mocker.spy(bare_chart, "_notes_per_second")
        _ = bare_chart.notes_per_second(
            pytest.default_instrument,
            pytest.default_difficulty,
            start_tick=start_tick,
            end_tick=end_tick,
        )
        spy.assert_called_once_with([], want_lower_bound, want_upper_bound)

    @pytest.mark.parametrize(
        "start_time,end_time,want_lower_bound,want_upper_bound",
        [
            pytest.param(
                datetime.timedelta(seconds=1),
                None,
                datetime.timedelta(seconds=1),
                _max_timedelta,
                id="last_none",
            ),
            pytest.param(
                datetime.timedelta(seconds=1),
                datetime.timedelta(seconds=2),
                datetime.timedelta(seconds=1),
                datetime.timedelta(seconds=2),
                id="no_none",
            ),
        ],
    )
    def test_with_time(
        self, mocker, bare_chart, start_time, end_time, want_lower_bound, want_upper_bound
    ):
        instrument_track = InstrumentTrack(
            pytest.default_instrument,
            pytest.default_difficulty,
            [],
            [],
        )
        instrument_track._last_note_timestamp = _max_timedelta
        bare_chart.instrument_tracks = {
            pytest.default_instrument: {
                pytest.default_difficulty: instrument_track,
            }
        }
        spy = mocker.spy(bare_chart, "_notes_per_second")
        _ = bare_chart.notes_per_second(
            pytest.default_instrument,
            pytest.default_difficulty,
            start_time=start_time,
            end_time=end_time,
        )
        spy.assert_called_once_with([], want_lower_bound, want_upper_bound)

    @pytest.mark.parametrize(
        "start_seconds,end_seconds,want_lower_bound,want_upper_bound",
        [
            pytest.param(
                1,
                None,
                datetime.timedelta(seconds=1),
                _max_timedelta,
                id="last_none",
            ),
            pytest.param(
                1,
                2,
                datetime.timedelta(seconds=1),
                datetime.timedelta(seconds=2),
                id="no_none",
            ),
        ],
    )
    def test_with_seconds(
        self, mocker, bare_chart, start_seconds, end_seconds, want_lower_bound, want_upper_bound
    ):
        instrument_track = InstrumentTrack(
            pytest.default_instrument,
            pytest.default_difficulty,
            [],
            [],
        )
        instrument_track._last_note_timestamp = _max_timedelta
        bare_chart.instrument_tracks = {
            pytest.default_instrument: {
                pytest.default_difficulty: instrument_track,
            }
        }
        spy = mocker.spy(bare_chart, "_notes_per_second")
        _ = bare_chart.notes_per_second(
            pytest.default_instrument,
            pytest.default_difficulty,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )
        spy.assert_called_once_with([], want_lower_bound, want_upper_bound)

    @pytest.mark.parametrize(
        "start_time,start_tick,start_seconds",
        [
            pytest.param(datetime.timedelta(0), 0, None),
            pytest.param(datetime.timedelta(0), None, 0),
            pytest.param(None, 0, 0),
            pytest.param(datetime.timedelta(0), 0, 0),
        ],
    )
    def test_too_many_start_args(self, bare_chart, start_time, start_tick, start_seconds):
        with pytest.raises(ValueError):
            _ = bare_chart.notes_per_second(
                pytest.default_instrument,
                pytest.default_difficulty,
                start_time=start_time,
                start_tick=start_tick,
                start_seconds=start_seconds,
            )

    @pytest.mark.parametrize(
        "instrument,difficulty",
        [
            pytest.param(Instrument.BASS, Difficulty.EXPERT),
            pytest.param(Instrument.GUITAR, Difficulty.MEDIUM),
            pytest.param(Instrument.BASS, Difficulty.MEDIUM),
        ],
    )
    def test_missing_instrument_difficulty(self, basic_chart, instrument, difficulty):
        with pytest.raises(ValueError):
            _ = basic_chart.notes_per_second(
                instrument,
                difficulty,
                start_tick=0,
            )


class TestIterateFromSecondElem(object):
    def test_basic(self):
        xs = [3, 4, 2, 5]
        for x1, x2 in zip(_iterate_from_second_elem(xs), xs[1:]):
            assert x1 == x2
