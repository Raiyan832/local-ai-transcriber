# Troubleshooting

Run `Install.cmd` and launch via `Run.cmd`, not by double-clicking `LocalAITranscriber.pyw`: Windows might associate `.pyw` with another Python version.

| Problem | Solution |
| --- | --- |
| Python 3.12 missing | Install Python 3.12 and rerun `Install.cmd`. |
| `ModuleNotFoundError: faster_whisper` | Re-run `Install.cmd` and use `Run.cmd`. |
| `av.open() got an unexpected keyword argument 'metadata_errors'` | The project requires `av==18.1.0`. Reinstall dependencies from `requirements.txt`. |
| CUDA detected but GPU test fails | Install optional GPU packages with `Install-GPU.cmd`, verify driver, rerun Test Hardware. |
| FFmpeg or FFprobe not found | Install `Gyan.FFmpeg` and reopen the terminal. |
| First model load fails | Connect to the internet for the initial model download. |
| Transcription fails | Read the failed row's Details column and the error log. |

## Verify your environment

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "import av; print(av.__version__)"
```

The last command should print `18.1.0`.

## NVIDIA GPU

Install the optional CUDA packages with `Install-GPU.cmd`. A recent NVIDIA driver and compatible card are required. Choose explicit **NVIDIA GPU** and click **Test Hardware**. **Auto** may silently fall back to CPU. If testing fails, provide the exact error before changing CUDA installations.

## Error log

```powershell
Get-Content "$env:APPDATA\LocalAITranscriber\error.log" -Tail 80
```

The log may not exist before an error has been recorded. Remove private filenames and paths before reporting bugs.

## Packaged builds

The Windows ZIP from Actions or Releases is unsigned, CPU-oriented, and does not bundle Whisper models. Extract the entire folder; do not move the EXE away from `_internal`. GPU inference in the packaged build is not guaranteed. The standalone FFmpeg converter is not included in this build.
