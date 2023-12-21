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

```
usage: main.py [-h] input output filter
```

- `input` is the input MIDI file path this program will read. It must end with `.mid`
- `output` is the path to the output file this program will write. It should not exist unless you want to have an existing file overwritten. It must end with `.mid`
- `filter`: The filter to select. Running `main.py -h` will show you the available filters.

Use `-h` to figure out what filters are needed. If you've made your own filters, add them to `FILTERS`, key being the command line argument and value being the filter function. 

Example:

```
python main.py input.mid output.mid no_filter
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

This program may not work well for overlapping notes in the same pitch (two notes with the same **pitch, channel, and track** are playing at the same time). Realistically, that would be impossible to do in real life.

**Slide notes and portamentos are not preserved.**

This program preserves track names, channels, instruments, and tempo changes. Any esoteric feature in MIDIs may not be preserved.

## Exporting MIDIs from FL Studio

FL Studio normally likes it when each track ties to a channel, as if there was a non-injective (not 1-1) mapping from each track to a channel.

- Each Track is an item you can see on the channel rack.
- Channels are tied to a track, based on the channel you set for MIDI out

You can also export a MIDI file directly from a channel. If you do so, the colors you assigned to the notes will be preserved, each distinct color getting its own track.