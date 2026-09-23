# Windows Runtime Design

## 1. Goal

The Windows frontend should make OCR feel like an operating-system action rather than launching an application.

Target interaction:

```text
Ctrl+Shift+X
-> dim/overlay screen
-> drag
-> release
-> clipboard updated
```

---

## 2. Process model

Recommended:

```text
TextJ resident process
├─ hotkey listener
├─ capture UI
├─ OCR runtime
├─ model sessions
├─ clipboard output
└─ tray lifecycle
```

Do not launch a new OCR process for every shortcut press.

---

## 3. Global hotkey

Preferred baseline:

Win32 `RegisterHotKey`.

Reasons:

- simple
- low overhead
- does not require a global keyboard hook for ordinary shortcut combinations

Fallback:

- configurable alternative when another application owns the shortcut

A low-level keyboard hook should only be used if later features truly require it.

---

## 4. Region selector

The selector should be lightweight.

Suggested behavior:

1. hotkey fires,
2. current desktop frame is captured,
3. transparent/borderless selection overlay appears,
4. pointer drag defines rectangle,
5. release closes overlay immediately,
6. crop is sent to OCR,
7. clipboard is updated.

Important details:

- per-monitor DPI awareness
- negative monitor coordinates
- multi-monitor layouts
- scaling at 125%, 150%, etc.
- keyboard Escape cancellation
- minimum crop size
- cursor inclusion policy

---

## 5. Screen capture candidates

### DXGI Desktop Duplication

Strong low-level candidate for fast desktop frame acquisition.

Useful characteristics:

- GPU-backed desktop frames
- monitor-oriented capture
- change metadata
- dirty/moved region information

Potential value to TextJ:

- low-latency region capture
- future watch/continuous OCR
- dirty-region optimization

Costs:

- more native/D3D complexity
- device-reset handling
- monitor-specific management

### Windows.Graphics.Capture

Modern Windows capture API for displays and application windows.

Potential advantages:

- supported Windows capture stack
- frame-pool model
- application/window capture use cases

For TextJ's custom drag-to-select UX, benchmark the actual snapshot acquisition path against DXGI.

---

## 6. Capture benchmark

Do not benchmark APIs only by FPS.

TextJ cares about:

```text
T_request_to_pixels
```

Record:

- capture request -> usable pixel buffer
- crop extraction time
- pixel conversion time
- first-frame latency
- repeated capture latency
- 1080p and 4K
- single and multiple monitors

---

## 7. Clipboard output

Primary output format:

`CF_UNICODETEXT`

Rules:

- preserve Korean characters
- preserve normal line breaks
- avoid modifying clipboard when OCR returns no trustworthy text
- clipboard operation must not block the OCR worker indefinitely
- retry briefly if clipboard is temporarily locked

Future optional formats:

- plain text
- structured JSON through CLI
- HTML text preserving lines/layout

---

## 8. DPI correctness

OCR must use actual captured pixels, not coordinates accidentally transformed twice by display scaling.

Tests should include:

```text
100%
125%
150%
175%
200%
```

and mixed-DPI multi-monitor setups.

Coordinate systems must be explicitly documented in capture code.

---

## 9. Resident memory

Keeping OCR models loaded is intentional.

Track:

- idle RSS
- model memory
- first OCR after idle
- repeated OCR
- accelerated provider memory

Possible future behavior:

- keep lightweight model always warm
- unload heavy accurate model after inactivity
- reload accurate model only when requested

Fast mode should remain instantly available.

---

## 10. Provider selection

Possible runtime policy:

```text
startup
-> enumerate supported providers
-> read saved benchmark preference
-> select provider
-> warm model
```

Do not blindly select a GPU because one exists.

For tiny OCR workloads, CPU can outperform a GPU path after upload/synchronization overhead.

Provider selection should eventually be benchmark-informed.

---

## 11. Crash isolation

The tray process is the user-facing shell.

Long-term option:

```text
TextJ shell
   |
   +-- OCR worker process
```

Benefits:

- model/runtime crash does not kill hotkey/tray state
- worker can be restarted
- backend upgrades become safer

Costs:

- IPC latency
- complexity
- image transfer overhead

Start single-process. Introduce worker isolation only if stability requires it.

---

## 12. Security/privacy

Default behavior:

- local OCR
- no screenshot upload
- no persistent screenshot storage
- no OCR history unless explicitly enabled
- temporary image buffers released after use

Debug modes that save screenshots must be opt-in and clearly marked.
