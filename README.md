# Local AI Transcriber

A Windows desktop application for local speech-to-text transcription using `faster-whisper`, with CPU and NVIDIA GPU support, batch processing, multiple export formats, and a companion FFmpeg-based media converter.

## Status

**Active Development**

Current baseline: `v0.1.0`

The application is functional and has been migrated from its original local development folder into a structured Git repository workspace.

## Overview

Local AI Transcriber provides a desktop interface for transcribing local audio and video files without relying on a hosted transcription service.

The application uses:

- Python
- Tkinter
- faster-whisper
- CTranslate2
- FFmpeg / FFprobe
- optional NVIDIA CUDA acceleration

The main application handles:

- transcription
- Whisper model selection
- CPU/GPU hardware selection
- batch queue processing
- transcript export
- transcript editing
- settings persistence
- CUDA verification and CPU fallback

A separate companion utility, `converter.py`, converts supported video files to MP3 using FFmpeg.

## Features

Current functionality includes:

- Local audio and video transcription
- Batch queue processing
- Whisper model selection
- Automatic hardware selection
- Manual CPU selection
- Manual NVIDIA GPU selection
- CPU transcription using INT8
- NVIDIA GPU transcription using CUDA FP16
- Automatic CPU fallback when GPU inference fails in Auto mode
- Real CUDA inference validation before processing user media
- Plain TXT transcript export
- Timestamped TXT transcript export
- SRT subtitle export
- Editable transcript output
- Persistent application settings
- Separate FFmpeg-based video-to-MP3 conversion utility

## Supported Whisper Models

The application currently supports:

- `tiny`
- `base`
- `small`
- `medium`
- `large-v3`

The current default model is:

```text
small
```

Model files are downloaded through the underlying `faster-whisper` workflow and are not stored in this repository.

## Supported Input Formats

The main transcription application currently accepts:

```text
.mp4
.mp3
.wav
.m4a
.mov
.mkv
.webm
.aac
.flac
.ogg
.wma
.mpeg
.mpg
```

The companion converter currently accepts:

```text
.mp4
.mkv
.mov
.avi
.webm
```

and converts supported video files to MP3.

## Output Formats

The transcription application can export:

- TXT
- Timestamped TXT
- SRT

Edited transcripts can also be saved as separate TXT files.

## Hardware Modes

The application provides three hardware options:

```text
Auto
CPU
NVIDIA GPU
```

### CPU Mode

CPU transcription uses:

```text
device = cpu
compute_type = int8
```

CPU mode is available when CUDA acceleration is unavailable or when the user explicitly selects CPU processing.

### NVIDIA GPU Mode

GPU transcription uses:

```text
device = cuda
compute_type = float16
```

The application uses CTranslate2 to detect available NVIDIA CUDA devices.

It also performs a real inference test before relying on GPU acceleration. This is intended to catch cases where the GPU is detected but required CUDA or cuDNN runtime components are unavailable.

### Auto Mode

Auto mode checks for an available CUDA-capable NVIDIA GPU.

If compatible GPU operation is available, the application uses CUDA FP16.

If GPU initialization or transcription fails, the application can retry using CPU INT8 processing.

## CUDA Runtime Handling

The application includes Windows-specific runtime detection for CUDA and cuDNN.

It checks common locations including:

```text
C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA
C:\Program Files\NVIDIA\CUDNN
C:\Program Files\NVIDIA Corporation\cuDNN
```

It also checks relevant environment variables and NVIDIA runtime directories installed through Python packages.

The application does not bundle CUDA or cuDNN binaries in this repository.

## Requirements

### Operating System

The current application is primarily developed and tested on Windows.

### Python

Verified development environment:

```text
Python 3.12.10
```

### Python Dependencies

Install dependencies with:

```powershell
python -m pip install -r requirements.txt
```

Current verified dependency versions:

```text
faster-whisper==1.2.1
ctranslate2==4.8.2
numpy==2.5.3
```

`faster-whisper` installs additional dependencies including packages such as:

- av
- huggingface-hub
- onnxruntime
- tokenizers
- tqdm

CTranslate2 also depends on NumPy and PyYAML.

## FFmpeg

FFmpeg and FFprobe are required by the companion media converter.

They must be installed and available on the system `PATH`.

The current development environment was validated with:

```text
FFmpeg 9.0.2
FFprobe 9.0.2
```

Example Windows installation using WinGet:

```powershell
winget install Gyan.FFmpeg
```

Verify installation with:

```powershell
ffmpeg -version
ffprobe -version
```

## Optional NVIDIA GPU Support

GPU acceleration requires:

- a compatible NVIDIA GPU
- a working CUDA runtime supported by CTranslate2
- required CUDA runtime DLLs
- compatible cuDNN runtime components

CPU mode remains available when GPU acceleration is unavailable.

The application performs a real Whisper inference test before marking GPU operation as verified instead of relying only on CUDA device detection.

## Installation

Clone the repository:

```powershell
git clone https://github.com/Raiyan832/local-ai-transcriber.git
cd local-ai-transcriber
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install project dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install FFmpeg separately if you plan to use the converter utility.

## Running the Application

Start the transcription application:

```powershell
python .\LocalAITranscriber.pyw
```

Start the media converter:

```powershell
python .\converter.py
```

## Main Application Workflow

A typical transcription workflow is:

```text
Select media
    |
    v
Add files to queue
    |
    v
Choose Whisper model
    |
    v
Choose hardware mode
    |
    v
Configure transcription options
    |
    v
Load model
    |
    v
Verify GPU if applicable
    |
    v
Transcribe media
    |
    v
Generate outputs
    |
    +--> TXT
    |
    +--> Timestamped TXT
    |
    `--> SRT
```

## Converter Workflow

The companion converter follows this general process:

```text
Select video
    |
    v
Inspect media with FFprobe
    |
    v
Run FFmpeg conversion
    |
    v
Create MP3 output
```

## Repository Structure

```text
local-ai-transcriber/
|
|-- LocalAITranscriber.pyw
|-- converter.py
|-- requirements.txt
|-- README.md
|-- CHANGELOG.md
|-- LICENSE
|-- AGENTS.md
|-- .gitignore
|
|-- .github/
|   |-- ISSUE_TEMPLATE/
|   |   |-- bug_report.md
|   |   `-- feature_request.md
|   |
|   `-- workflows/
|
|-- assets/
|-- docs/
|-- scripts/
|-- src/
`-- tests/
```

The current working Python files remain at the repository root intentionally.

They should not be moved into `src/` until path behavior, subprocess behavior, packaging requirements, and regression testing justify restructuring.

## Data and Privacy

This repository is intended to contain source code and documentation only.

Do not commit:

- personal recordings
- lecture recordings
- private media
- generated transcripts
- restricted datasets
- downloaded model files
- CUDA runtime binaries
- cuDNN runtime binaries
- credentials
- authentication tokens
- passwords
- machine-specific secrets

The following generated or local-data directories are ignored by Git:

```text
Converted/
to_convert/
output/
outputs/
temp/
tmp/
models/
downloads/
```

Use synthetic, public, or deliberately created sample media for public testing assets.

## Testing and Validation

The migrated baseline has been manually verified to:

- launch the main Tkinter transcription application
- launch the companion converter
- load the current Python dependency environment
- detect FFmpeg
- detect FFprobe
- operate from the clean migration workspace

Changes affecting transcription behavior should validate:

- application launch
- GUI startup
- input media selection
- Whisper model loading
- CPU transcription
- GPU transcription when compatible hardware is available
- Auto-mode CPU fallback
- transcript export
- edited transcript saving
- converter behavior when modified

## Current Development Environment

The current verified development environment includes:

```text
Windows
Python 3.12.10
faster-whisper 1.2.1
CTranslate2 4.8.2
NumPy 2.5.3
FFmpeg 9.0.2
FFprobe 9.0.2
```

## Known Limitations

- Automated tests are not yet implemented.
- Development is currently Windows-focused.
- GPU acceleration depends on compatible NVIDIA CUDA configuration.
- FFmpeg must currently be installed separately.
- Source files have not yet been modularized.
- The current application can install some dependencies dynamically, but reproducible setup should use `requirements.txt`.
- Packaged executable distribution is not yet part of the stable release workflow.
- Fresh-clone validation is still part of the migration process.
- CI workflows have not yet been added.

## Roadmap

Planned work may include:

- CPU/GPU-aware default model selection
- improved dependency setup
- packaged Windows executable
- installer or portable distribution
- automated tests
- source modularization
- continuous integration
- improved error reporting
- reproducible fresh-machine setup
- application screenshots
- release packaging
- improved documentation
- cleaner separation between the transcriber and converter utilities

Roadmap items are planned work and should not be interpreted as completed features.

## Development Workflow

Development should generally follow:

```text
Issue
  |
  v
Branch
  |
  v
Development / Codex
  |
  v
Testing
  |
  v
git diff review
  |
  v
Commit
  |
  v
Push
  |
  v
Pull Request
  |
  v
Merge
  |
  v
Release
```

Suggested branch prefixes:

```text
feature/
fix/
refactor/
docs/
experiment/
```

Examples:

```text
feature/cuda-detection
fix/cpu-fallback
refactor/transcription-engine
docs/install-guide
experiment/model-benchmark
```

## Versioning

The project uses semantic-style versioning:

```text
vMAJOR.MINOR.PATCH
```

During active development, versions may remain below `v1.0.0`.

Examples:

```text
v0.1.0
v0.2.0
v0.2.1
v1.0.0
```

## Contributing

For development changes:

1. Create or identify the relevant issue.
2. Create a development branch.
3. Make a focused change.
4. Test the affected functionality.
5. Review `git diff`.
6. Commit with a descriptive message.
7. Push the branch.
8. Open a pull request.
9. Review and merge into `main`.

See `AGENTS.md` for repository development rules.

## Security and Privacy

Do not report private recordings, credentials, tokens, or restricted media in public GitHub issues.

When reporting bugs:

- remove private file paths where possible
- remove personal media names
- remove credentials and tokens
- include only the technical information required to reproduce the problem

## License

This project is licensed under the MIT License.

See `LICENSE` for details.