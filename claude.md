# CLAUDE.md: automate_stock

Small Python bot: NSE delivery swing trading via Groww, paper mode by default.
Full mission, hard rules and memory workflow: read `OBJECTIVE.md` once per session, only if the task touches strategy, risk, memory or themes. Do not re-read it.

## Files (know these, don't scan for them)
- `trader.py`: daily run: data, signal, risk gate, orders, state
- `themes.py` + `config.yaml`: news -> LLM themes -> candidate stocks
- `review.py`: stats from the journal
- `memory/params.json`: tunable settings. Other `memory/*` and `state.json` are runtime data.

## Never read or open
`.env*`, `.venv/`, `data/`, `__pycache__/`, `memory/journal.jsonl`, `state.json`, `*.csv`, lock files.
Need trade history? Ask me to run `python review.py` and paste the output.

## Token rules (save tokens by reading less, never by checking less)
- Read only the files named in the task, plus what they directly import. No "explore the repo".
- For big files, read the function you will change, not the whole file. Do not re-read a file already read this session.
- No sub-agents unless I ask. Do the work in the main session.
- Plans: 30 lines or fewer, bullets, no design essays, no restating the task.
- Replies: what changed, why, test result. No recap of the code, no long explanations unless asked.
- Command output: pipe long output through `tail`/`head`/`grep`. Never dump full logs or full test output; show failures only.
- One task per session. When a task is done, say so and stop. I will `/clear`.
- One question at a time, only when a wrong guess would be costly. Otherwise state your assumption and proceed.

## Quality rules (never trade these away to save tokens)
- Smallest change that meets the task's "done when" line. Do not refactor unrelated code.
- Do not change strategy logic (`signal`, indicators) or `memory/params.json` values unless the task says so.
- Every change ships with a test, or an explicit note why none applies. Run the relevant tests before saying done.
- Money-critical code (orders, state, risk gate, live/paper switch, costs): read the surrounding code fully, think it through, and cover failure cases (rejection, partial fill, timeout, crash mid-run). Being brief does not apply here; being correct does.
- Never weaken a safety rule: paper mode default, `LIVE_CONFIRM`, `STOP` file, loss limits, capital cap, ticker validation.
- Never print, log or commit secrets. Do not create or edit `.env`.
- If a requirement conflicts with `OBJECTIVE.md` hard rules, stop and ask.
- Prefer the standard library and existing dependencies. Ask before adding a new one.
- Use IST for all trading dates and times.

## Done means
1. Behavior matches the task's acceptance line.
2. Tests pass (state which ones you ran).
3. `git diff --stat` shows only intended files.
4. One-paragraph summary I can paste to my reviewer: what changed, files touched, tests, open risks.

## Compact instructions
When compacting, keep: current task and its "done when" line, files changed, failing tests with exact errors, decisions made, next steps. Drop: old exploration, repeated logs, discarded approaches.