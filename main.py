import argparse
import os
from typing import Callable

from midi_processor import MidiRepresentation, process_and_save_midi
from no_chords import no_chords


def no_filter(midi_representation: MidiRepresentation) -> None:
    """This does nothing."""
    _ = midi_representation


FILTERS: dict[str, Callable[[MidiRepresentation], None]] = {
    "no_filter": no_filter,
    "no_chords": no_chords
}


def fn(arg1: str, arg2: str, arg3: str) -> None:
    """
    Process arguments.

    :param arg1: Input file path
    :param arg2: Output file path
    :param arg3: Which filter to run
    """
    print(f"Processing with input: {arg1}, output: {arg2}, filter: {arg3}")
    cur_filter = FILTERS.get(arg3, None)
    if not os.path.isfile(arg1):
        raise argparse.ArgumentTypeError("The input file you specified does not exist")

    _, input_ext = os.path.splitext(arg1)
    _, opt_ext = os.path.splitext(arg2)

    if input_ext != ".mid":
        raise argparse.ArgumentTypeError("Input file does not end with a .mid")

    if opt_ext != ".mid":
        raise argparse.ArgumentTypeError("Output file does not end with a .mid")

    if cur_filter is None:
        raise argparse.ArgumentTypeError(
            f"The filter you selected does not exist. The current filters are {list(FILTERS.keys())}")
    process_and_save_midi(arg1, arg2, cur_filter)
    print("Processing complete")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=f'Processes a MIDI file with a given filter. The current filters are {list(FILTERS.keys())}')

    parser.add_argument('input', type=str, help='Input')
    parser.add_argument('output', type=str, help='Output')
    parser.add_argument('filter', type=str, help='Filter')

    args = parser.parse_args()
    fn(args.input, args.output, args.filter)


if __name__ == '__main__':
    main()
