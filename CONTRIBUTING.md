# Contributing

Bug reports, documentation changes, and focused pull requests are welcome.

- Search existing issues before reporting a bug.
- Provide reproduction steps, expected and actual results, relevant versions, and a sanitized traceback.
- Never include private recordings, transcripts, credentials, or sensitive file paths.
- Work on a topic branch and keep changes focused.
- Test GUI launch, short transcription, text/SRT export, and affected converter functionality. Test GPU only when compatible hardware is available.
- Update documentation when installation or behavior changes.

## Developer setup

```powershell
git clone https://github.com/Raiyan832/local-ai-transcriber.git
cd local-ai-transcriber
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\LocalAITranscriber.pyw
```

See [AGENTS.md](AGENTS.md) for project development guidance and [LICENSE](LICENSE) for licensing.
