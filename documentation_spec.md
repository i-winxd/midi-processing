# MIDI REPRESENTATION SPECIFICATION

A `MidiRepresentation` class has these fields:

- `tracks`: A dictionary, `dict[int, Track]`
  - Keys are `int`s being the track number
  - Values are `Track` instances, having these fields:
    - `notes`: a **list** of `Note` instances (`list[Note]`), each note being
      - `channel` (`int`, counts from 0, adjust conventions as FL counts from 1)
      - `note` (`int`, `60=C5`)
      - `velocity` (`int`, 0 to 100)
      - `beat` (`float`)
      - `duration` (`float`)
    - `track_name` (`str`), the name of the track, which in FL Studio is the name of what you set in the channel rack
- `channel_instrument_map`: `dict[int, int]`
  - Key: channel number (counting from 0)
  - Value: MIDI instrument number
- `bpm_changes`: a list of `TempoChange` (`list[TempoChange]`) instances, where each `TempoChange` has these fields:
  - `beat` (`float`), the beat where it occurs
  - `new_bpm` (`float`), the new BPM
- `time_signature_changes`, a list of `TimeSignature` instances. For songs without time signature changes, it usually
  has one at beat 0 representing 4/4. A `TimeSignatureChange` consists of:
  - `numerator` (`int`)
  - `denominator` (`int`)
  - `beat` (`float`)