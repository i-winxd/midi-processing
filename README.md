# Python Midi Processing

A Python module meant for processing MIDI files in a programmer-friendly way.

## Installation and Setup

Make sure you have Python 3.8 or later installed. You have it installed if you can type `python` in the command prompt and have the console show up.

https://www.python.org/downloads/

Make sure to add Python to your path.

Then, run this command:

```
python -m pip install -r requirements.txt
```

Then, you may run `main.py` below, or use the API in `midi_processor.py` if you already have programming experience.



## Command line usage

All the python files are their own filters and can exist as standalone programs. Run `python <program.py> -h` to see what they do.

Sample usage - assumes `input.mid` exists.

```
python identity.py input.mid output.mid
```

## API

- ``midi_to_representation(midi_file: mido.MidiFile) -> MidiRepresentation:``
- ``representation_to_midi_file(midi_representation: MidiRepresentation) -> mido.MidiFile:``
- ``process_and_save_midi(md_path: str, md_opt: str, fn: Callable[[MidiRepresentation], None]) -> None:``

You are not meant to use any method that starts with an underscore.

## Sample Code Usage

```python
midi_file = mido.MidiFile("input.mid")
midi_representation = midi_to_representation(midi_file)
# do stuff to the midi_representation
midi_file_2 = representation_to_midi_file(midi_representation)
midi_file_2.save("output.mid")
```

Or more compactly:

```python
def midi_processor(midi_representation: MidiRepresentation) -> None:
    # your code here; this is a function that mutates midi_representation
    pass

process_and_save_midi("input.mid", "output.mid", midi_processor)
```

## Object Representation

Just read the class declarations in `midi_processor.py`

## Caution!

**Do NOT** try to interpret track numbers! They may be offset. Instead, use track names instead if they were defined when exporting the MIDI file.

**Channels in this program count from 0**. In FL Studio, channels count from 1. Don't let this convention mix you up!

*Preserved* means if you put a midi file into this program without filtering it and put the output back in FL Studio, all of its information should be retained. This program does not preserve MIDI files perfectly; read the warnings below.

### Preserved

- Tempo and tempo changes
- Track names
- Channel numbers
- Instrument mappings

### Readable

- Time signatures

### Not Preserved

- Slide notes, portamentos

## Exporting MIDIs from FL Studio

FL Studio normally likes it when each track ties to a channel, as if there was a non-injective (not 1-1) mapping from each track to a channel.

- Each Track is an item you can see on the channel rack.
- Channels are tied to a track, based on the channel you set for MIDI out

You can also export a MIDI file directly from a channel. If you do so, the colors you assigned to the notes will be preserved, each distinct color getting its own track.

## Current Filters

- `identity`: Does nothing. Just like multiplying a value by 1, or a vector by the identity matrix.
- `no_chords`: Remove all but one note from all chords.
    Only applies to the same channel and track.
    Keep the highest one.
- `tempo_integrator`: Remove all tempo changes. Forces the tempo to 60.
    Adjust note duration and beat durations to accommodate the removal of tempo so the output MIDI file still sounds the same.

## To Dos

- 6/8 to 4/4 (Hard)
- Chord identifier (Very hard)
