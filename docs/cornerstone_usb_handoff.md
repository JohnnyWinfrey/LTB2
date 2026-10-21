# Cornerstone monochromator: direct USB driver (handoff)

**Status (2026-10-21):** code written and tested against a simulated device
only. **It has not run on a real CS130 or CS260 yet.** The old helper exe is
still in place and is used automatically on any PC that hasn't been switched
over, so nothing is broken in the meantime.

## Why

The Cornerstone (Oriel CS130 / CS260) used to be driven through
`helpers/cornerstone_helper.exe`. That's a bundled 32-bit Python that loads
Newport's `Cornerstone.dll`, which uses Cypress's `CyUSB.dll` and the
`CyUSB.sys` kernel driver. LTB2 talks to the exe over stdin/stdout. It's slow
(each query took about 2 s), hard to change, and needs Newport software
installed on every PC.

`Cornerstone.dll` turned out to be a thin 12 KB .NET wrapper around plain text
commands sent over USB. The new code sends those same bytes itself, using
`pyusb` and Microsoft's generic WinUSB driver: no Newport software, no exe,
normal 64-bit Python.

## How it works

Windows lets one kernel driver "own" each USB device. On a PC switched over
with Zadig, that's WinUSB instead of Cypress's driver. WinUSB is a dumb pipe,
and `pyusb` uses it to read and write the device's two bulk endpoints.

```
before:  LTB2 -> helper exe (32-bit Python) -> Cornerstone.dll -> CyUSB.dll -> CyUSB.sys -> USB
after:   LTB2 -> pyusb / libusb -> WinUSB.sys -> USB
```

The bytes on the cable are the same in both cases. The monochromator can't
tell the difference.

## Protocol (from disassembling Cornerstone.dll v1.0.1.1)

| Item | Value |
|---|---|
| USB ID | VID `0x1180`, PID `0x0012` (same for CS130 and CS260) |
| Endpoints | bulk OUT `0x01`, bulk IN `0x81`, interface 0 |
| Packet size | 64 bytes |
| Command format | ASCII text + `\r\n`, e.g. `GOWAVE 500.000\r\n` |
| Replies | one line, `<value>\r\n`; Newport parses the first line |
| Set commands | no reply (`GOWAVE`, `SHUTTER O/C`, `GRAT n`, `FILTER n`, ...) |

Full command set used by the DLL:

| Purpose | Query | Set |
|---|---|---|
| Wavelength | `WAVE?` | `GOWAVE <nm>` |
| Motor steps | | `STEP <n>` |
| Units | `UNITS?` | `UNITS NM\|UM\|WN` |
| Shutter | `SHUTTER?` (`O`/`C`) | `SHUTTER O`, `SHUTTER C` |
| Grating | `GRAT?` | `GRAT <n>` |
| Grating info | `GRAT<n>LINES?`, `GRAT<n>LABEL?` | `GRAT<n>LINES <l>`, `GRAT<n>LABEL <text>` |
| Grating calibration | `GRAT<n>ZERO?`, `GRAT<n>OFFSET?`, `GRAT<n>FACTOR?` | same without `?`, plus a value |
| Filter wheel | `FILTER?`, `FILTER<n>LABEL?` | `FILTER <n>`, `FILTER<n>LABEL <text>` |
| Slits (µm) | `SLIT<n>MICRONS?` | `SLIT<n>MICRONS <um>` |
| Bandpass | `BANDPASS?` | `BANDPASS <nm>` |
| Handshake | | `HANDSHAKE 0\|1` |

Slit numbers: 1 = input port A, 2 = off-axis output B, 3 = on-axis output C.

**How Newport waits for a move.** For `GOWAVE` and `GRAT`, the DLL sends
`HANDSHAKE 1`, then the move, polls the IN pipe until a reply starts with `"0"`
(up to 120 s), then sends `HANDSHAKE 0`. The new code doesn't do that. It
polls `WAVE?` / `GRAT?` / `FILTER?` until the unit reports the target, and
counts unanswered queries as "still moving".

## What's in the repo

| File | What |
|---|---|
| `hardware/cornerstone.py` | `CornerstoneUSB` (new driver), `CornerstoneClient` (old exe link), `Cornerstone` (GUI/automation class), fakes |
| `helpers/cornerstone_probe.py` | standalone diagnostic; logs raw USB traffic to a text file |
| `requirements.txt` | adds `pyusb` and `libusb-package` |
| `docs/cornerstone_usb_handoff.md` | this file |

`hardware/cornerstone.py` in more detail:

- **`CornerstoneUSB`** has every command in the table above as a method
  (`goto`, `position`, `set_grating`, `grating_info`, `set_filter`,
  `set_slit_width`, `units`, ...). `goto`, `set_grating` and `set_filter`
  block until the move finishes and raise `RuntimeError` on timeout. A
  re-entrant lock keeps the GUI and a running automation from interleaving
  commands. Stale input is drained before each command.
- **`Cornerstone(transport="auto")`** tries USB first and falls back to the
  helper exe, printing which one it used. `transport="usb"` or `"exe"` forces
  one.
- **New GUI controls** on `Cornerstone`: `setGrating` (buttons 1/2/3),
  `getGrating`, `setFilter`, `getFilter`, `setSlitWidth`. They only work over
  USB; on the old exe they raise a clear error.
- **Unchanged interface.** Automations that call `cs.mono.goto()`,
  `cs.mono.open_shutter()` and so on work the same on either transport.
  `FakeCornerstone` supports the new controls, so `--sim` runs still work.

## Not yet verified on hardware

The probe log will settle these:

1. **`BANDPASS` and `STEP` syntax.** The DLL sends them with no space
   (`BANDPASS5`, `STEP10`). The new code sends a space, like every other
   command. Check which one the firmware accepts.
2. **`GRAT?` reply format.** It might be `2` or `2,1200,750`. The code takes
   the leading number, so either works, but confirm.
3. **Move completion.** If `WAVE?` reports the target before the grating has
   physically stopped, `goto` returns early. In that case, switch to Newport's
   handshake approach.
4. **Echo, and replies to set commands.** The code tolerates both, but if
   neither happens the drain step can be simplified.
5. **CS130 has at most 2 gratings.** The "3" button just raises an error
   there. Fine, but worth knowing.

## Next steps

### 1. Test at a monochromator (ideally one CS130 and one CS260)

```
pip install -r requirements.txt
```

Switch the driver (one time per PC; needs admin rights):

1. Plug in and power the monochromator.
2. Run Zadig (https://zadig.akeo.ie).
3. Options → List All Devices.
4. Pick the Cornerstone (USB ID `1180 0012`).
5. Pick **WinUSB** as the target driver, then click **Replace Driver**.

Then run the probe from the repo root:

```
python helpers/cornerstone_probe.py --move --grating 2
```

It writes `cornerstone_probe_<time>.txt` to the current folder. `--move` steps
the wavelength +10 nm and back and opens/closes the shutter; `--grating 2`
switches to grating 2 and back. Without those flags it only reads.

Read the log against the "Not yet verified" list above and fix
`hardware/cornerstone.py` where needed. Then run a real automation
(e.g. `automations/tcspc/spectral.py`) and check that the console prints
`Cornerstone: direct USB (WinUSB)`.

### 2. Roll out to users

Each PC needs the `pip install` and the Zadig swap once. Nothing else changes
for them. If clicking through Zadig is a problem, `wdi-simple.exe` from the
same project (libwdi) can do the swap from a one-line `.bat`.

### 3. Clean up, once every PC is on WinUSB

Delete:

- `helpers/cornerstone_helper.exe`
- `helpers/Cornerstone.dll`
- `helpers/CyUSB.dll`
- `helpers/cornerstoneHelperFiles/`

Then remove `CornerstoneClient` and the fallback branch in
`Cornerstone._connect`.

## Caveats

- **On a PC switched to WinUSB, Newport's own software can't see the
  monochromator.** To undo: Device Manager → the device → Update driver →
  pick the Cypress/Newport driver, or roll back.
- **The `set_grating_zero/offset/factor/lines` methods overwrite the unit's
  stored calibration.** Only use them when recalibrating, and write down the
  old values first; the probe log has them.
- **`goto` / `position` use whatever `UNITS?` reports.** All of LTB2 assumes
  nm, same as before.

## Re-deriving the protocol

`Cornerstone.dll` and `CyUSB.dll` are .NET assemblies, not native code, so
they can be read back almost to source. There are two ways:

- **ILSpy** (free) on Windows.
- **Python, on any OS** (what was used here): `pip install dnfile dncil`, then
  walk `pe.net.mdtables.TypeDef` → `MethodList` and disassemble each method
  body with `dncil.cil.body.CilMethodBody`. String literals come from
  `pe.net.user_strings`. The VID/PID are the `ldc.i4` constants stored to
  `vendorId` / `productId` in the constructor.

Side note: both DLLs are flagged AnyCPU (not 32-bit-only). The 32-bit Python
inside the helper exe was never strictly required.

## Linux / macOS (future)

The same `CornerstoneUSB` code works with no driver swap. Install libusb
(`brew install libusb` / `apt install libusb-1.0-0`). On Linux, also add a udev
rule so non-root users can open the device:

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="1180", ATTRS{idProduct}=="0012", MODE="0666"
```

If the device shows up as Cypress `04b4:8613` instead of `1180:0012`, it is
waiting for firmware from the Newport driver, and `fxload` would be needed.
That's unlikely, but check it first.
