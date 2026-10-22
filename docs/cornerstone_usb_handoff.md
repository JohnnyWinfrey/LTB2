# Cornerstone monochromator: direct USB driver (handoff)

## Where things stand (2026-10-22)

LTB2 now drives Oriel Cornerstone monochromators directly over USB
(`pyusb` + Microsoft's WinUSB driver) instead of through Newport's software.

- **CS130: done.** SN1007, firmware V04.30, on the CS130 lab PC. Connecting,
  wavelength moves, shutter and grating changes were checked against the
  hardware. That PC is on WinUSB now.
- **CS260: not tested yet.** That's the next step, below. The protocol is
  expected to be the same (same USB ID, same DLL), but the CS260 has 3
  gratings, possibly a filter wheel and motorized slits, and its firmware
  may differ.
- **The old helper exe is gone** (removed from the repo along with
  Newport's DLLs and all code that used it). **Every PC must have the
  WinUSB driver swap before LTB2 can use its monochromator.** On a PC still
  on Newport's driver, `Cornerstone()` stops with "can't open the
  monochromator … still on Newport's CYUSB driver".
- **One code path for every unit.** The lab has one CS130 and two CS260s
  at three tables. On connect, the driver reads the model, serial and
  firmware and detects the installed gratings, filter wheel and motorized
  slits. Asking for something a unit lacks (grating 3 on the CS130) prints
  a warning in the GUI and sends nothing. Detection is verified on the
  CS130 only.

## Next session: test on the CS260

### 0. Before leaving the CS130 PC

The driver rewrite must be committed and pushed, or the CS260 PC won't have
it. Check with `git log`: the commits after `19edcd1 cornerstone refactor
start` should touch `hardware/cornerstone.py`, `helpers/cornerstone_probe.py`
and this file, and delete `helpers/cornerstone_helper.exe`.

### 1. Set up the CS260 PC

From the repo root, after pulling:

```
pip install -r requirements.txt
```

(`pyusb` and `libusb-package` are the new ones.)

Check whether anything else on this PC uses the monochromator through
Newport's software (LabVIEW, Newport's own app, another script). After the
driver swap, **none of them will see it**. That's reversible (see
"Undoing the driver swap"), but decide first.

### 2. Swap the driver with Zadig (once per PC, needs admin)

1. Plug in and power on the monochromator.
2. Run Zadig (https://zadig.akeo.ie). Options → **List All Devices**.
3. In the dropdown, pick the monochromator. Before the swap it is listed as
   "Newport/Oriel Cornerstone Monochromator" (Device Manager's name for it).
4. Check the fields:
   - **USB ID** fills in by itself and must read `1180` `0012`. The third
     box is usually blank. If it shows anything else, you picked the wrong
     device.
   - **Driver**: left of the arrow is the current driver (`CYUSB`). Right
     of the arrow, choose **WinUSB**.
   - **WCID**: just an indicator; a red ✗ is normal. Ignore it.
5. Click **Replace Driver**.

Afterwards Device Manager lists it under "Universal Serial Bus devices"
with service `WinUSB` (on the CS130 the name changed to "VSE-SPECTRA").

### 3. Run the probe in stages

The probe talks to the unit directly and logs every reply to
`cornerstone_probe_<time>.txt` in the current folder. Run it from a scratch
folder so logs don't land in the repo.

```
python <repo>/helpers/cornerstone_probe.py                 # read-only
python <repo>/helpers/cornerstone_probe.py --move          # +10 nm and back, shutter open/close
python <repo>/helpers/cornerstone_probe.py --grating 1     # switch grating and back, restore wavelength
```

- Start read-only. If it fails at "Claim", the driver swap didn't take.
- `--grating N` must be a grating **other than the current one** (the
  read-only run shows it under `GRAT?`), or nothing moves. The probe
  switches to N, back to the original, and returns to the original
  wavelength.
- Everything it changes is restored. It never writes calibration values.

### 4. Compare the log with the CS130

Each reply is the text before the first `\r\n` in the packets logged after
the command. What the CS130 answered, for reference:

| Query | CS130 reply | What to look for on the CS260 |
|---|---|---|
| `INFO?` | `Oriel Instruments,Model Cornerstone 130,SN1007,V04.30` | **Must contain "Cornerstone"**: the driver checks this on connect |
| `WAVE?` | `655.976` | a number in nm |
| `UNITS?` | `nm` | `nm` (LTB2 assumes nm) |
| `SHUTTER?` | `C` / `O` | same |
| `GRAT?` | `2,600,1000` (number, lines/mm, label) | **same format**; the driver uses the first number |
| `GRAT<n>LINES?` / `LABEL?` | `600` / `400`, `600` / `1000` | grating 3 should answer now |
| `GRAT3…` | no reply (CS130 has 2 gratings) | a reply |
| `FILTER?` | `0` (no wheel) | `0`, or a position if there's a wheel |
| `SLIT1MICRONS?`, `BANDPASS?` | `0`, `0.000` (no motorized slits) | real values if it has them |
| `STB?` | `20` | anything |
| `STEP?` | `149135` (motor position) | a number |

How the firmware should behave (all true on the CS130, so check these):

- **Replies arrive 60–150 ms after the command.** The packets before that
  start with eight `\x00` bytes ("busy").
- **The query right after a move is answered only once the move is done.**
  In the `--move` section, the `WAVE?` after `GOWAVE` should come back with
  the new wavelength, not the old one. Same for `GRAT?` after `GRAT`
  (~11 s on the CS130).
- **The wavelength after a grating change.** On the CS130 it jumped
  (3163.99 nm on grating 1, -0.029 nm back on grating 2). Note what the
  CS260 does. If it keeps the wavelength, `Cornerstone.set_grating`'s
  move-back is harmless but could be skipped.

### 5. Test the real driver

From the repo root, with the unit idle:

```python
from hardware import Cornerstone
cs = Cornerstone()
# prints e.g. "Cornerstone: Cornerstone 130 SN1007 V04.30:
#   gratings 1 (600 l/mm), 2 (600 l/mm); no filter wheel; no motorized slits"
print(cs.client.info, cs.client.units(), cs.position(), cs.getGratingInfo())
for n in (1, 2, 3):
    print(cs.client.grating_info(n))
cs.open_shutter(); print(cs.shutter_open()); cs.close_shutter(); print(cs.shutter_open())
start = cs.position()
cs.goto(start + 10); print(cs.position())
cs.goto(start); print(cs.position())
cs.set_grating(1); print(cs.getGratingInfo(), cs.position())   # pick one that isn't current;
cs.set_grating(2); print(cs.getGratingInfo(), cs.position())   # end on the original grating
cs.client.close()
```

Each `set_grating` should come back near the starting wavelength (within
0.05 nm).

**Check the connect line against the real unit.** It should list 3
gratings on a CS260. The filter wheel and slits are detected by
`FILTER?` > 0 and `SLIT<n>MICRONS?` > 0. That's right for a unit without
them (the CS130 answers `0`), but untested on one that has them. If a
fitted wheel or slit shows up as missing (or the reverse), fix
`CornerstoneClient._detect`. Run this on both CS260s, since their gratings and
accessories may differ. If the CS260 has a filter wheel or slits, also try
`cs.filter()`, `cs.set_filter(n)` and `cs.slit_width(1)`. Only change slits
if nothing on the bench minds.

Then run a real automation (e.g. `python -m automations.tcspc.spectral`)
and check the console prints the `Cornerstone: Cornerstone 260 …` line.

### 6. If something goes wrong

- **"replies are out of step with queries; power-cycle the monochromator"**
  or answers that belong to a different query: switch the unit off for
  ~5 s and back on. USB resets don't clear it. It's caused by sending
  commands while one is still running (e.g. two programs at once, or a
  script polling during a move).
- **`Cornerstone warning: … has no grating 3 …; nothing sent`**: expected
  on a unit without that grating or accessory, from the GUI or an
  automation. The automation carries on, on the grating it was already
  using. (Calling `cs.client` directly raises `Unsupported` instead.)
- **`no reply to 'X?' in 2 s`**: the unit doesn't support that command
  (on the CS130 that's `GRAT3…` and `FILTER1LABEL?`). This does not put it
  out of step.
- **"can't open the monochromator: it's still on Newport's CYUSB
  driver"**: do (or redo) the Zadig step.
- **"can't open the monochromator (Access denied …); another program …
  has it open"**: close the other LTB2 window or script using it.
- **A move times out**: `goto` waits 120 s, `set_grating` 120 s,
  `set_filter` 30 s. If the CS260 is slower, raise those defaults in
  `CornerstoneClient`.

### Still open after the CS260

1. **`BANDPASS` and `STEP` set syntax.** Newport's DLL sends them with no
   space (`BANDPASS5`, `STEP10`); the driver sends a space. Untested, since
   the CS130 has no motorized slits and `STEP` moves the motor. If the
   CS260 has slits, try `cs.client.set_bandpass(...)`, then
   `cs.client.bandpass()` and see
   whether it took.
2. **Roll out** to the remaining PC (the second CS260):
   `pip install -r requirements.txt` + the Zadig swap. Required now that
   there's no fallback. `wdi-simple.exe` (from libwdi, the project behind
   Zadig) can do the swap from a `.bat` if clicking through Zadig is a
   problem.
3. **Optional: pick a unit by serial number** (`cs.client.serial`, e.g. `1007`), if a
   PC ever has two monochromators. There's no COM port over USB (VID, PID
   and endpoints are fixed for every CS130/CS260). An RS-232 transport via
   pyserial would be a separate addition if the serial port is ever used.

---

## Reference

### Why the change

The old route (removed; last present in commit `19edcd1`) was
`helpers/cornerstone_helper.exe`, a bundled 32-bit
Python that loads Newport's `Cornerstone.dll`, which uses Cypress's
`CyUSB.dll` and `CyUSB.sys`. It was slow (~2 s per query), hard to change,
and needed Newport software on every PC. `Cornerstone.dll` turned out to be
a thin .NET wrapper around plain text commands over USB, so LTB2 now sends
those bytes itself.

```
before:  LTB2 -> helper exe (32-bit Python) -> Cornerstone.dll -> CyUSB.dll -> CyUSB.sys -> USB
after:   LTB2 -> pyusb / libusb -> WinUSB.sys -> USB
```

Speed on the CS130: queries ~0.1 s; 10 nm move ~0.35 s; 0 → 655 nm
~1.3 s; grating change ~11 s (~19 s through `Cornerstone.set_grating`, which also moves
back to the wavelength).

### What's in the repo

| File | What |
|---|---|
| `hardware/cornerstone.py` | `Cornerstone` (simple; automations + GUI), `CornerstoneClient` (all the hardware code), `FakeCornerstone` (`--sim`), `Unsupported` |
| `helpers/cornerstone_probe.py` | standalone diagnostic; logs raw USB traffic |
| `requirements.txt` | `pyusb`, `libusb-package` |
| `auto_gui.py` | `position`, `grating`, `filter`, `shutter_open` added to the readout names, so the GUI shows their values |

Two layers, like `TH260` / `TH260DLLClient`:

- **`Cornerstone`** is the simple class automations use, e.g.
  `cs = Cornerstone()`, `cs.goto(550)`. It has `goto`, `position`,
  `open_shutter`, `close_shutter`, `shutter_open`, `set_grating`,
  `grating`, `set_filter`, `filter`, `set_slit_width` and `slit_width`. Each
  is a line or two calling the client, with a plain-English docstring.
  It's also the GUI window; its public methods are the GUI controls, plus
  the scan range (`startWavelength`, `endWavelength`, `numSteps`) and
  `getGratingInfo`. `set_grating` also moves back to the previous
  wavelength. `set_grating` / `set_filter` / `set_slit_width` print a
  warning and do nothing for anything the unit lacks.
- **`CornerstoneClient`** (`cs.client`) has all the hardware code and every
  command below (`step`, `units`, `grating_info`, `filter_label`,
  `set_bandpass`, calibration, ...); its docstring lists them all. `goto`,
  `set_grating` and `set_filter` return once the move is done and raise
  `RuntimeError` if the unit ends up elsewhere. A lock keeps the GUI and a
  running automation from interleaving commands. Also exported from
  `hardware` along with `Unsupported`.
- **Capability detection** (`CornerstoneClient._detect`, run by `open()`, ~2 s):
  `.model`, `.serial`, `.firmware` from `INFO?`; `.gratings`
  (`{number: lines/mm}`, from which `GRAT<n>LINES?` answer); `.has_filter_wheel`;
  `.slits`. `describe()` gives the one-line summary. Grating, filter and slit
  methods raise `Unsupported` for anything not detected, before sending.
  A missing feature never replies, so detection uses a 0.5 s timeout.
- **`Cornerstone()`** connects and prints the unit's one-line description.
  The GUI's `set_grating` buttons 1/2/3 come from the class's type hints,
  so button 3 is always shown (and warns on a CS130); hiding it per unit
  would need a change in `auto_gui.py`.
- **`FakeCornerstone`** (`--sim`) runs the real `CornerstoneClient` code on a
  simulated CS260 with everything fitted (3 gratings, filter wheel,
  slits). Only the USB layer is replaced, so every method behaves as on
  hardware, the `Unsupported` checks included.

### Protocol

| Item | Value |
|---|---|
| USB ID | VID `0x1180`, PID `0x0012` (CS130 and CS260) |
| Endpoints | bulk OUT `0x01`, bulk IN `0x81`, interface 0, 64-byte packets (the device also has unused `0x82` IN / `0x08` OUT) |
| Commands | ASCII + `\r\n`, e.g. `GOWAVE 500.000\r\n` |
| Queries | one-line reply |
| Set commands, bad commands | no reply |

| Purpose | Query | Set |
|---|---|---|
| Identity | `INFO?` | |
| Wavelength | `WAVE?` | `GOWAVE <nm>` |
| Motor steps | `STEP?` | `STEP <n>` |
| Units | `UNITS?` | `UNITS NM\|UM\|WN` |
| Shutter | `SHUTTER?` (`O`/`C`) | `SHUTTER O`, `SHUTTER C` |
| Grating | `GRAT?` | `GRAT <n>` |
| Grating info | `GRAT<n>LINES?`, `GRAT<n>LABEL?` | `GRAT<n>LINES <l>`, `GRAT<n>LABEL <text>` |
| Grating calibration | `GRAT<n>ZERO?`, `OFFSET?`, `FACTOR?` | same without `?`, plus a value |
| Filter wheel | `FILTER?`, `FILTER<n>LABEL?` | `FILTER <n>`, `FILTER<n>LABEL <text>` |
| Slits (µm) | `SLIT<n>MICRONS?` | `SLIT<n>MICRONS <um>` |
| Bandpass | `BANDPASS?` | `BANDPASS <nm>` |
| Status | `STB?` | |
| Handshake | | `HANDSHAKE 0\|1` |

Slits: 1 = input port A, 2 = off-axis output B, 3 = on-axis output C.

### How the firmware answers (measured on the CS130)

- **IN `0x81` is a buffer, not a stream.** Every read instantly returns the
  whole 64-byte reply buffer again. Its first line is the latest reply; the
  rest is leftovers from older replies, e.g.
  `b'C\r\n.976\r\n\numents,Model Cornerstone 130,...'`.
- **Taking a command blanks the buffer.** Its first 8 bytes become `\x00`.
  A query's reply replaces that 60–150 ms later, sometimes after a
  zero-length packet or a read timeout. A set command leaves it blank.
  `CornerstoneClient.query` waits for blank → reply, so it never returns the
  previous answer.
- **One command at a time.** A write made while the unit is busy blocks
  until it's free, so a query sent right after `GOWAVE`/`GRAT` is answered
  once the move has finished. That's how the driver waits for moves: one
  query, no polling.
- **Never two commands in flight.** Polling `GRAT?` every 0.5 s during a
  grating change left the CS130 answering every query with the reply to
  the one two before it, until power-cycled. `open()` checks `INFO?` to
  catch this.
- **`HANDSHAKE 1`** (what Newport's DLL uses around moves) adds a status
  line to every command, `0` ok or `32` error, which overwrites a query's
  value ~4 ms after it appears. The driver keeps handshake off.

## Caveats

- **Newport's software can't see a monochromator on WinUSB.** Undo: Device
  Manager → the device → Update driver → pick the Cypress/Newport driver,
  or Roll Back Driver.
- **Grating changes may lose the wavelength** (they do on the CS130).
  `cs.set_grating` moves back; scripts calling
  `cs.client.set_grating` directly must `goto` themselves.
- **Don't drive the monochromator from two programs at once.**
- **`set_grating_zero/offset/factor/lines` overwrite the unit's stored
  calibration.** Only for recalibrating; the probe log records the current
  values first.
- **`goto` / `position` use whatever `UNITS?` reports.** LTB2 assumes nm.

## Re-deriving the protocol

The DLLs are no longer in the working tree; get them from commit `19edcd1`
(`git show 19edcd1:helpers/Cornerstone.dll > Cornerstone.dll`).
`Cornerstone.dll` and `CyUSB.dll` are .NET assemblies and decompile almost
to source: use ILSpy on Windows, or in Python `pip install dnfile dncil`,
walk `pe.net.mdtables.TypeDef` → `MethodList` and disassemble each body
with `dncil.cil.body.CilMethodBody` (strings are in `pe.net.user_strings`;
VID/PID are the `ldc.i4` constants stored to `vendorId` / `productId`).
Both DLLs are AnyCPU, so the helper's 32-bit Python was never needed.

## Linux / macOS (future)

`CornerstoneClient` works without a driver swap. Install libusb
(`brew install libusb` / `apt install libusb-1.0-0`). On Linux add a udev
rule so non-root users can open the device:

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="1180", ATTRS{idProduct}=="0012", MODE="0666"
```

If the device appears as Cypress `04b4:8613` instead of `1180:0012`, it's
waiting for firmware from the Newport driver and needs `fxload`.
