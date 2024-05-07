from typing import Annotated
from helpers.midi_processor import MidiRepresentation, process_and_save_midi
from helpers.utils import create_argparse_from_function


def no_filter(midi_representation: MidiRepresentation) -> None:
    """This does nothing."""
    _ = midi_representation


def run(source: Annotated[str, "Path to MIDI file to modify"], 
        destination: Annotated[str, "Path to output MIDI file"]) -> None:
    """Does nothing to the input MIDI file, except for the inherent changes
    that must occur when converting a MIDI file with this module."""
    process_and_save_midi(source, destination, no_filter)


if __name__ == '__main__':
    create_argparse_from_function(run)

