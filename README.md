# Local AI Transcriber

**Private, local speech-to-text for Windows.** Turn lectures, interviews, meetings, and videos into searchable transcripts without uploading your media to a transcription service.

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D4) ![Python](https://img.shields.io/badge/Python-3.12-3776AB) ![License](https://img.shields.io/badge/License-MIT-green) ![Status](https://img.shields.io/badge/Status-Active%20development-orange)

Built with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), CTranslate2, and Tkinter.

## Features

- **Local processing:** recordings remain on your computer. Models are downloaded on first use.
- **Batch processing:** transcribe multiple audio or video files in one queue.
- **Multiple exports:** TXT, timestamped TXT, and SRT subtitles.
- **CPU or NVIDIA GPU:** CPU INT8, CUDA FP16, and automatic CPU fallback.
- **Transcript editor** and persistent settings.
- **GPU hardware test:** verifies real CUDA inference, not only device detection.
- **Separate video-to-MP3 converter** using FFmpeg.

## Install on Windows

**Easiest supported option: source installation.** No Git or IDE is necessary.

1. Install [Python 3.12](https://www.python.org/downloads/) (or run `winget install --id Python.Python.3.12 -e`).
2. **[Download the project ZIP](https://github.com/Raiyan832/local-ai-transcriber/archive/refs/heads/main.zip)** and extract it.
3. Double-click **`Install.cmd`** in the extracted folder. This creates a private `.venv` and installs pinned dependencies.
4. Double-click **`Run.cmd`** to open the transcriber.
5. Add a media file, choose a Whisper model (start with `small`), and click **Start**.

> Review scripts before running them. The installer puts dependencies only in this project's local Python environment. The model downloads on first use, so an internet connection is initially required.

### Optional NVIDIA acceleration

Run **`Install-GPU.cmd`** after installation. This installs large optional CUDA 12/cuDNN 9 runtime packages, not the NVIDIA display driver. In the app select **NVIDIA GPU** and click **Test Hardware**. GPU detection alone does not confirm inference works.

### Downloadable Windows EXE

Check [Releases](https://github.com/Raiyan832/local-ai-transcriber/releases). Tagged releases may provide an **unsigned, CPU-oriented ZIP**. If there are no assets, use the source installation above. Packaged NVIDIA acceleration is not yet verified on clean machines.

## Use it

1. Open `Run.cmd` and add MP3, MP4, WAV, M4A, MOV, MKV, WEBM, AAC, FLAC, OGG, WMA, MPEG, or MPG files.
2. Choose `tiny`, `base`, `small`, `medium`, or `large-v3`. Larger models take more resources.
3. Select CPU, Auto, or NVIDIA GPU. Auto may fall back to CPU.
4. Start transcription and save TXT, timestamped TXT, or SRT files.

## Video to MP3

For the separate converter, install FFmpeg and FFprobe (`winget install --id Gyan.FFmpeg -e`), reopen your terminal, and double-click **`Convert.cmd`**. FFmpeg is not required for the main app's PyAV decoding.

## Developers

```powershell
git clone https://github.com/Raiyan832/local-ai-transcriber.git
cd local-ai-transcriber
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\LocalAITranscriber.pyw
```

The project pins `av==18.1.0` because PyAV 19 caused a decoding error with the pinned faster-whisper version. See [Troubleshooting](docs/TROUBLESHOOTING.md), [Contributing](CONTRIBUTING.md), and the [Changelog](CHANGELOG.md).

## Limitations

Windows-focused and under active development. Models are not bundled, so first use requires internet. The packaged EXE is unsigned and GPU compatibility has not been established on fresh machines. Automated functional transcription tests are not yet implemented.

## Privacy and license

Transcription processing occurs locally after model download. Do not share personal recordings or exported transcripts in public GitHub issues. Licensed under [MIT](LICENSE).
