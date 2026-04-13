# Issue: GUI Dialog Crashes — Missing `FG` Constant
Date found: 2026-04-12

## Tasks
- [x] `CourseResourcesDialog` / `_ResourceRowDialog`: cannot add rows — ✅ Fixed (2026-04-12): added `FG` constant
- [x] `TQF3StaffDialog`: opens blank page — ✅ Fixed (2026-04-12): added `FG` constant

## Root Cause
`FG` color constant was used in `_ResourceRowDialog`, `TQF3StaffDialog`, and `_PersonRowDialog`
but never defined in the module-level style block.

tkinter swallows the `NameError` silently — the window frame opens but widget construction
stops at the first `fg=FG` call. Result:
- `_ResourceRowDialog`: form never renders → `result` stays `None` → parent sees no data
- `TQF3StaffDialog`: header label crashes → combobox + tree never built → blank window

## Fix
Added to `input_gui.py` style constants (line ~22):
```python
FG = "#1a1a1a"
```

## Related Files
- `input_gui.py` — style constants block (top of file), classes: `_ResourceRowDialog` (line ~2819), `TQF3StaffDialog` (line ~2886), `_PersonRowDialog` (line ~3048)

## Completed
- Added `FG = "#1a1a1a"` to module constants — all three dialogs now have a valid color value
