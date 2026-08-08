# AURA

Artificial Universal Responsive Assistant is a terminal-based personal assistant built with Python and SQLite.

## Version

0.2.0 — Real Gemini AI Brain

## Features

- Persistent key/value memory and profile details
- Safe calculator with arithmetic, parentheses, and `sqrt()`
- Persistent SQLite notes
- Time, date, and day responses
- Built-in clean jokes and motivational messages
- Command help and a v0.1.0 changelog
- Model-independent, permission-controlled tool architecture for future AI integration
- Normalized, categorized, timestamped memory search and safe legacy-memory migration
- Simulated model-to-tool orchestration with bounded tool-call loops
- Gemini-powered natural-language fallback using the official `google-genai` SDK and `gemini-3.6-flash`
- Gemini function requests routed through AURA's validation, permission, and allowlisted tool registry

## Basic usage

```text
remember my favourite game is Minecraft
show my memories
calculate (12 + 8) * 3
take a note Finish Aura v0.1.0
show my notes
tell me a joke
help
```

## Gemini setup and offline behavior

Install dependencies, then set `GEMINI_API_KEY` in your environment before starting AURA. The key is read only from the environment and is never stored by AURA.

```text
pip install -r requirements.txt
$env:GEMINI_API_KEY = "your-key"   # PowerShell
python main.py
```

Deterministic commands always run first (calculator, notes, memories, profile, time/date/day, help, fun, and more). Only unrecognized input uses Gemini. Without an API key, AURA starts normally and all deterministic features remain available; it reports that the AI brain is unavailable for fallback requests.

Gemini can request registered tools such as `calculator.evaluate`, note and memory operations, and current time/date/day. AURA validates the request, checks permissions, executes only its controlled handler, and returns a structured result to Gemini. The model never receives direct Python, shell, SQL, filesystem, or database access. Tool loops are capped at three calls.

## Project structure

```text
AURA/
├── main.py
├── config.py
├── data/memory.db
├── brain/
│   ├── commands.py
│   ├── database.py
│   ├── profile.py
│   ├── time_utils.py
│   ├── calculator.py
│   ├── notes.py
│   └── fun.py
└── tests/
```

## Tests

Run the complete test suite with:

```text
python -m unittest discover -v
```

## Changelog

### v0.1.0

First core release: adds memory management, built-in jokes and motivation, command help, a concise changelog, and improved terminal startup presentation.

### v0.1.1

Adds a tested tool registry, validated tool-request schemas, permission levels, controlled wrappers for existing features, and focused memory retrieval. No AI model or external dependency has been added.

### v0.1.2

Adds normalized memory keys, categories, created/updated timestamps, ranked retrieval, and safe migration/conflict inspection for existing memory records.

### v0.1.3

Adds a test-only simulated AI brain that passes structured requests through validation, permissions, registered tools, structured results, and a final natural-language response. No real AI model is connected.

### v0.2.0

Adds the real Gemini AI brain via `google-genai` and `gemini-3.6-flash`, with bounded in-memory context, Gemini function declarations for AURA's registered tools, structured tool-result translation, and graceful offline fallback. The normal test suite is fully mocked and offline; an optional live test runs only with `AURA_LIVE_GEMINI_TEST=1`.
