# Createc to Nanonis File Conversion

## What It Does

This repository converts **Createc** raw scan data files (`.dat`) into formats compatible with Nanonis analysis software. Currently supported conversions:

* Createc `.dat` → Nanonis `.sxm`
* Createc `.dat` → `.png` preview images

We have three tools that implement the above:

- `dat-gui` — graphical interface (recommended for most users)
- `dat-png` — CLI: convert to PNG
- `dat-sxm` — CLI: convert to SXM

Both CLI commands accept either a single `.dat` file or a directory of `.dat` files.

## Installation

Clone the repository, enter it, and install it in editable mode:

```bash
git clone https://github.com/SPMQT-Lab/Createc-to-Nanonis-file-conversion.git
cd Createc-to-Nanonis-file-conversion
python -m pip install -e .
```

That installs these commands into your active Python environment:

- `dat-png` — CLI: convert to PNG
- `dat-sxm` — CLI: convert to SXM
- `dat-gui` — graphical interface (recommended for most users)

## Usage

### Graphical interface (recommended)

```bash
dat-gui
```

Opens a window where you can:
- Browse to your input folder of `.dat` files
- Browse to your output folder
- Choose to convert to PNG, SXM, or both
- Adjust contrast clipping under Advanced options
- Toggle dark/light mode
- Watch live progress in the log panel

Your folder selections and preferences are saved automatically between sessions.

---

### Command line

#### Use the built-in default paths

The repository ships with two sample `.dat` files in [data/sample_input](data/sample_input). With the defaults unchanged, you can run:

```bash
dat-png
dat-sxm
```

### Supply your own paths

Convert to PNG previews:

```bash
dat-png --input-dir path/to/input --output-dir path/to/output
```

Convert to `.sxm`:

```bash
dat-sxm --input-dir path/to/input --output-dir path/to/output
```

### Optional flags

Both `dat-png` and `dat-sxm` support these additional flags:

| Flag | Default | Description |
|------|---------|-------------|
| `--clip-low` | `1.0` | Lower percentile for contrast clipping |
| `--clip-high` | `99.0` | Upper percentile for contrast clipping |
| `--verbose` | off | Enable debug logging (shows scaling factors, saved files, etc.) |

Example with custom contrast and verbose output:

```bash
dat-png --input-dir path/to/input --output-dir path/to/output --clip-low 2 --clip-high 98 --verbose
```

## Repository Contents

- [nanonis_tools](nanonis_tools): installable converter source code
  - `common.py`: shared utilities (DAC scaling, header parsing, image processing)
  - `dats_to_pngs.py`: PNG conversion tool
  - `dat_sxm_cli.py`: SXM conversion tool
  - `gui.py`: graphical interface
- [src/file_cushions](src/file_cushions): required layout assets for `.sxm` generation
- [data/sample_input](data/sample_input): two small example `.dat` files
- [tests](tests): pytest test suite (63 tests)

## Notes

- `dat-sxm` writes output files using the input filename stem.
- The `.sxm` timestamp parsing expects filenames of the form `AyyMMdd.HHmmss.dat` (e.g. `A250320.191933.dat`).
- The cushion files in `src/file_cushions` encode the binary structure of the `.sxm` format and are required for SXM generation. The path defaults to the repo root so no changes are needed unless you move them.
- If a batch run encounters errors, a summary `errors.json` is written to the output directory.
