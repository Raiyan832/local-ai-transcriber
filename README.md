# Local AI Transcriber

A Windows desktop application for local speech-to-text transcription using `faster-whisper`, with CPU and NVIDIA GPU support, batch processing, multiple export formats, and a companion FFmpeg-based media converter.

## Status

**Active Development**

Current baseline: `v0.1.0`

## Overview

Local AI Transcriber provides a desktop interface for transcribing local audio and video files locally.

The application uses:

- Python
- Tkinter
- faster-whisper
- CTranslate2
- FFmpeg / FFprobe
- optional NVIDIA CUDA acceleration

The main application handles transcription, model selection, hardware selection, batch processing, transcript export, and transcript editing.

A separate companion utility, `converter.py`, converts supported video files to MP3 using FFmpeg.

## Features

- Local audio and video transcription
- Batch processing
- Whisper model selection
- Automatic hardware selection
- CPU transcription using INT8
- NVIDIA GPU transcription using CUDA FP16
- Automatic CPU fallback in Auto mode
- Real CUDA inference verification
- TXT export
- Timestamped TXT export
- SRT subtitle export
- Editable transcript output
- Persistent settings
- FFmpeg-based video-to-MP3 conversion

## Supported Whisper Models

- `tiny`
- `base`
- `small`
- `medium`
- `large-v3`

Current default model:

```text
small