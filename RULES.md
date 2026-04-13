# AI Working Rules — TQF System

## 1. When you identify tasks → save to a .md file immediately

**Filename** must describe the content, e.g.:
- `issue_db_schema.md`
- `todo_gui_improvements.md`
- `issue_import_bugs.md`

**Required file structure:**
```markdown
# [Title]
Date found: YYYY-MM-DD

## Tasks
- [ ] Task 1 — description
- [ ] Task 2 — description

## Reason / Context
Why this needs to be done

## Related Files
- `database.py` — line X
- `import_tqf3.py` — function Y
```

---

## 2. When done → update the .md file

Change `- [ ]` to `- [x]` and add:
```
- [x] Task 1 — ✅ Fixed (YYYY-MM-DD): describe what was changed
```

Add a `## Completed` section at the bottom:
```markdown
## Completed
- Fixed X by doing Y
- Added Z to function W
```

---

## 3. Language & Token Rule  `[low token used]`

**All .md files must be written in English.**
Reason: reduces LLM token usage in future sessions.
- Code comments: English preferred, Thai acceptable
- User communication: Thai is fine
- MD content (HANDOFF, RULES, PROJECT_REFERENCE, CODEX_CONTEXT, issue logs): **English only**

**Token optimization guidelines:**
- Prefer concise responses over verbose explanations
- Show code directly — skip line-by-line narration
- Use tables and bullet points instead of long paragraphs in docs
- Do not repeat context already established in HANDOFF.md / PROJECT_REFERENCE.md
- Skip restating what you just did — the user can read the diff

---

## 4. Project-specific Rules

### DB / Schema
- **Never** use `ALTER TABLE RENAME` in production code — create new DB from schema then copy data, or use `ALTER TABLE xxx ADD COLUMN yyy` migration inside `init_db()`
- Every schema change in `database.py` must be tested in `/tmp/` before applying to production
- Check FK integrity with `PRAGMA integrity_check` after every migration

### SQLite file operations (CRITICAL)
- **Never** use `cp` to replace the `.db` file on the Linux mount after any write operation
- If you used `cp` and a `.db-journal` file exists, the DB is in an inconsistent state — must be fixed on Windows
- Correct way to copy DB: use `conn.backup(dst_conn)` API
- Test all DB operations by copying to `/tmp/` first (sandbox mount doesn't support SQLite file locks)
- If `.db-journal` exists on the Windows mount and can't be deleted from Linux: create a fix script and run it on Windows

### Python .pyc cache (CRITICAL)
- The Linux bash sandbox caches `.pyc` files by source file mtime
- After editing a `.py` file via Write/Edit tool (which writes to Windows path), the Linux mount may show the old mtime
- **Always run `touch <filename>.py` in bash** after editing via Write/Edit tool, before testing
- Symptom of stale cache: code changes have no effect, or functions that exist in source are missing from module

### import_tqf3.py
- Don't pass `curriculum_id` to `upsert_course` → it finds existing records automatically
- CLO count unexpectedly low → check if docx uses the expected heading format for the parser

### import_grades.py
- Supports `.doc`/`.rtf` via `parse_rtf_tables()` (no LibreOffice needed)
- If course not found in DB → create empty record and log a warning (don't fail)
- Course name from grade file may not match curriculum — curriculum data is the master

### GUI (input_gui.py)
- All DB operations in GUI must run in background thread (`threading.Thread`)
- Always call `db.init_db()` before any other DB operation
- Errors must appear in the log box, not as popups (exception: successful export)

### generate_tqf3.py
- Opens the existing template `templates/แบบฟอร์ม มคอ. 3.docx` — never creates a document from scratch
- Use `_replace_block_between()` for all paragraph block replacements — do not write inline removal loops
- Use `addnext` to insert paragraphs after an anchor — never `addprevious` (causes XML ordering bugs)
- Filter `instructors_json` with `_is_valid_instructor_name()` before using as instructor names
- Prefer `tqf3_staff` table over `instructors_json` fallback

---

## 5. Standard Workflow

```
Found bug / new task
    ↓
Create issue_XXXX.md
    ↓
Fix code / rebuild DB (in /tmp/ first)
    ↓
Test at runtime (not just syntax check)
    ↓
Update .md → change [ ] to [x]
    ↓
Update PROJECT_REFERENCE.md if schema or behavior changed
    ↓
Update HANDOFF.md (latest status + next tasks)
    ↓
git commit + push (if git is set up)
```

---

## 6. Multi-Device / Multi-AI Workflow

This project runs across 3 environments:

| Environment | Tool | When to use |
|-------------|------|-------------|
| PC (primary) | Cowork | Main work, GUI, DB, complex analysis |
| PC (fallback) | Codex | Cowork tokens exhausted, direct coding tasks |
| MacBook | Cowork or Codex | Off-site work |

### Start of every session
1. **Read `HANDOFF.md` first** — know where work was left off
2. If using git: `git pull` before starting
3. If DB may have changed (worked on another machine): check DB file state

### End of every session
1. **Update `HANDOFF.md`** — write what was done and what comes next
2. If schema changed: update `PROJECT_REFERENCE.md`
3. If using git: `git add *.py *.md .gitignore` → `git commit` → `git push`
4. **Never commit**: `.db`, `__pycache__`, `.xlsx` files

### Handing off to Codex
```
Tell Codex:
"Read these files first: CODEX_CONTEXT.md, HANDOFF.md
Then continue according to the 'Next Up' section in HANDOFF.md"
```

### Git setup (one-time)
```bash
cd "path/to/tqf gen/tqf_system"
git init
git add *.py *.md *.bat *.txt .gitignore requirements.txt
git commit -m "initial: TQF system"
git remote add origin https://github.com/YOUR_USERNAME/tqf-system.git
git push -u origin main
```

### Standard git commands for routine sessions
```bash
# Check current state first
git status --short --branch

# Review what changed
git diff
git diff --cached

# Stage only the files you intend to publish
git add -- <file1> <file2> <file3>

# Or stage all intended tracked/untracked updates carefully
git add -A

# Commit with a clear message
git commit -m "feat: short summary"

# Push the current branch
git push origin main
```

Rules for using these commands:
- Always run `git status --short --branch` before `git add`
- Prefer `git add -- <files>` over `git add -A` when the repo is dirty
- Do not push until tests/verification for the touched files pass
- After pushing, run `git status --short --branch` again and record any leftover dirty files in `HANDOFF.md`

### DB sync between machines
- **DB is not in git** (binary, changes frequently)
- Use a **cloud folder** (OneDrive/Google Drive) to sync the whole folder instead
- For git-only workflows: Excel export is sufficient for viewing data on another machine
