import math
from typing import Annotated
from helpers.midi_processor import MidiRepresentation, process_and_save_midi
from helpers.utils import create_argparse_from_function
from functools import partial

def to_swing(beat_count: float, mult: float) -> float:
    """Return the swing variant of a beat's count.
    """
    beat_count = beat_count * mult
    beat_decimal = beat_count % 1
    beat_whole_num = math.floor(beat_count)
    # new_beat_decimal = 0.0
    if beat_decimal <= 0.500000001:  # prevents rounding error
        new_beat_decimal = beat_decimal * (4 / 3)
    else:
        new_beat_decimal = (1 / 3) * ((2 * beat_decimal) + 1)
        # (beat_decimal - 0.5) * (2/3) + (2/3)
    new_beat = beat_whole_num + new_beat_decimal
    return new_beat / mult


def swing_midi(midi_representation: MidiRepresentation, mult: float) -> None:
    for _, track in midi_representation.tracks.items():
        for i in range(len(track.notes)):
            track.notes[i].beat = to_swing(track.notes[i].beat, mult)
            track.notes[i].duration = track.notes[i].duration
        track.clamp_notes()


multiplicative_factor_str = """Adjusts what's considered a beat. 
When set to 1, one beat is considered one beat.
When set to 2, beats are half as long. Same effect as setting the time sig denominator to 8.
When set to n, beats are 1/n as long for the purposes of swinging.
Decimal values are acceptable.
Defaults to 1."""



def run(source: Annotated[str, "Path to MIDI file to modify"], 
        destination: Annotated[str, "Path to output MIDI file"],
        mult: Annotated[float, multiplicative_factor_str] = 1) -> None:
    """Swings a non-swing MIDI throughout. We assume that the midi's time sig
    denominator is 4."""
    process_and_save_midi(source, destination, lambda sw: swing_midi(sw, mult))


if __name__ == '__main__':
    create_argparse_from_function(run)

