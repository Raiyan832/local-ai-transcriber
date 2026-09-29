# Project Instructions



## Objective



This repository contains a local AI transcription application for Windows.



The application processes local media files, performs speech-to-text transcription, and exports transcript files.



Preserve working behavior unless a task explicitly requires a change.



## Current Architecture



The current working application consists primarily of:



- `LocalAITranscriber.pyw` as the main GUI application

- `converter.py` as a supporting media conversion utility



The application currently uses a Tkinter GUI and invokes external/runtime dependencies as needed.



Do not move or rename these files until their path assumptions and runtime behavior have been reviewed and tested.



## Development Rules



- Make small, reviewable changes.

- Do not modify unrelated functionality.

- Preserve existing working behavior unless the task explicitly changes it.

- Prefer simple, maintainable implementations.

- Avoid unnecessary architectural rewrites.

- Do not silently replace the current application with a new framework.

- Do not introduce new dependencies unless they provide clear value.

- Preserve CPU-only operation.

- Preserve GPU acceleration when available.

- Preserve graceful CPU fallback when GPU/CUDA support is unavailable.

- Preserve existing transcription/export behavior unless explicitly changing it.

- Preserve existing GUI functionality unless explicitly changing it.



## Media and User Data



Do not commit:



- source media files

- converted media files

- generated transcripts

- personal recordings

- lecture recordings

- private datasets

- temporary processing files



The following directories are local/generated data and must remain untracked:



- `Converted/`

- `to_convert/`

- `output/`

- `outputs/`

- `temp/`

- `tmp/`



Use synthetic, public, or deliberately created sample media if testing assets are ever added to the public repository.



## Model and Runtime Files



Do not commit:



- downloaded Whisper models

- model caches

- CUDA runtime files

- cuDNN files

- Python virtual environments

- packaged build output

- installer artifacts unless published through an appropriate release process



Document how these dependencies are obtained instead.



## Repository Safety



Never commit or expose:



- passwords

- API keys

- authentication tokens

- SSH/private keys

- private file paths when unnecessary

- personal recordings

- university course recordings

- protected or restricted data

- machine-specific credentials



Use example configuration files when configuration needs to be documented.



## Git Rules



- Treat `main` as the accepted working state.

- Perform development on an appropriate branch.

- Use branch prefixes:

  - `feature/`

  - `fix/`

  - `refactor/`

  - `docs/`

  - `experiment/`

- Do not force-push unless explicitly requested.

- Do not rewrite shared Git history without explicit instruction.

- Review `git status` and `git diff` before committing.

- Keep commits focused on one coherent change when practical.

- Use concise, descriptive commit messages.



## Testing



Before considering a change complete:



1. Confirm the application launches.

2. Confirm the GUI opens normally.

3. Confirm input media can be selected or discovered.

4. Confirm the relevant transcription path works.

5. Confirm transcript export still works.

6. Confirm CPU mode still works when relevant.

7. Confirm GPU mode still works when relevant and hardware is available.

8. Run automated tests if they exist.

9. Report any tests that could not be run.



Do not claim successful GPU validation if the current machine lacks compatible GPU/CUDA support.



## Refactoring Rules



Before restructuring files or splitting modules:



1. Inspect file-path assumptions.

2. Inspect subprocess calls.

3. Inspect imports.

4. Inspect references between `LocalAITranscriber.pyw` and `converter.py`.

5. Confirm how FFmpeg or other external tools are located.

6. Preserve current behavior with a before/after smoke test.



Do not move source files into `src/` merely for cosmetic organization until this review is complete.



## Documentation



Update documentation when a change affects:



- installation

- dependencies

- supported media formats

- model behavior

- CPU/GPU requirements

- configuration

- usage

- architecture

- packaging

- outputs



Keep the README aligned with the actual application.



Do not describe planned features as completed features.



## Packaging



Build artifacts should not be committed directly to the repository.



Use:



- `build/`

- `dist/`



as generated directories.



When stable packaged applications are created, publish them through GitHub Releases rather than storing binaries in normal source history.



## Definition of Done



A task is complete only when:



- the requested requirement is satisfied

- the application still launches

- relevant transcription functionality still works

- relevant tests or validation pass

- existing behavior has not been unintentionally broken

- documentation is updated when necessary

- no private media, generated transcripts, secrets, or large runtime files were introduced

- `git diff` has been reviewed

- remaining limitations are clearly identified

