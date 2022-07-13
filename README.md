---
# chartparse

[![codecov](https://codecov.io/gh/AWConant/chartparse/branch/main/graph/badge.svg?token=chartparse_token_here)](https://codecov.io/gh/AWConant/chartparse)
[![CI](https://github.com/AWConant/chartparse/actions/workflows/main.yml/badge.svg)](https://github.com/AWConant/chartparse/actions/workflows/main.yml)

## Install it from PyPI

```bash
pip install chartparse
```

## Usage

```py
from chartparse.chart import Chart
from chartparse.instrument import Instrument, Difficulty

c = Chart.from_filepath("/path/to/file.chart")

# the first 7 BPM changes
c.sync_track.bpm_events[:7]

# the first 8 time signature changes
c.sync_track.time_signature_events[:8]

expert_guitar = c.instrument_tracks[Instrument.GUITAR][Difficulty.EXPERT]

# the first 10 notes of the expert guitar chart
expert_guitar.note_events[:10]

# the first 3 star power phrases of the expert guitar chart
expert_guitar.star_power_events[:3]
```

See the [documentation](https://chartparse-gh.readthedocs.io/en/latest/) for more detailed
guidance.

Note: this software is tested only with .chart files that are written by
[Moonscraper](https://github.com/FireFox2000000/Moonscraper-Chart-Editor).
Files written by other editors or are handwritten may produce undefined
behavior.

## Development

Read the [CONTRIBUTING.md](CONTRIBUTING.md) file.
