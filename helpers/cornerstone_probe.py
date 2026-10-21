"""Probe a Cornerstone monochromator over raw USB (pyusb + WinUSB) and log
exactly what it sends back. Standalone: needs only pyusb and libusb-package.

    python helpers/cornerstone_probe.py            # read-only queries
    python helpers/cornerstone_probe.py --move     # also moves +10 nm and back,
                                                   # and opens/closes the shutter
    python helpers/cornerstone_probe.py --grating 2  # also switches to grating 2
                                                     # and back

Everything is printed and saved to cornerstone_probe_<time>.txt in the current
directory; send that file back.

Before running on Windows, swap the driver to WinUSB with Zadig (see the
docstring in hardware/cornerstone.py). Nothing here changes the monochromator's
settings except, with --move / --grating, its wavelength, shutter and grating
(all restored).
"""
import argparse
import platform
import sys
import time

VID, PID = 0x1180, 0x0012
EP_OUT, EP_IN = 0x01, 0x81

LOG = []


def log(msg=""):
    print(msg, flush=True)
    LOG.append(msg)


def backend():
    try:
        import libusb_package
    except ImportError:
        log("libusb-package not installed; pyusb will search for libusb itself")
        return None
    return libusb_package.get_libusb1_backend()


def read_all(dev, window_s, packet_timeout_ms=100):
    """Every IN packet that arrives within window_s, with arrival times."""
    import usb.core

    got, t0 = [], time.monotonic()
    while time.monotonic() - t0 < window_s:
        try:
            data = bytes(dev.read(EP_IN, 64, packet_timeout_ms))
        except usb.core.USBTimeoutError:
            continue
        got.append((time.monotonic() - t0, data))
    return got


def exchange(dev, cmd, terminator=b"\r\n", window_s=1.5):
    """Send cmd, log every packet that comes back within window_s."""
    read_all(dev, 0.2)    # drain
    payload = cmd.encode("ascii") + terminator
    t0 = time.monotonic()
    n = dev.write(EP_OUT, payload, 1000)
    got = read_all(dev, window_s)
    log(f">> {payload!r}  (wrote {n} bytes)")
    if not got:
        log("   <no reply>")
    for t, data in got:
        log(f"   +{t * 1000:7.1f} ms  {len(data):2d} B  {data!r}")
    return got, t0


def first_text(got):
    text = b"".join(d for _, d in got).replace(b"\x00", b"").decode("ascii", "replace")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--move", action="store_true",
                    help="also test GOWAVE and the shutter")
    ap.add_argument("--grating", type=int,
                    help="also switch to this grating and back")
    args = ap.parse_args()

    log(f"cornerstone_probe  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"python {sys.version.split()[0]} {platform.architecture()[0]}  {platform.platform()}")
    try:
        import usb.core
        import usb.util
    except ImportError:
        log("pyusb not installed: pip install pyusb libusb-package")
        return 1
    log(f"pyusb {usb.__version__}")

    be = backend()

    # --- 1. Find the device ------------------------------------------------
    log("\n== USB devices ==")
    devs = list(usb.core.find(find_all=True, backend=be))
    for d in devs:
        mark = "  <-- Cornerstone" if (d.idVendor, d.idProduct) == (VID, PID) else ""
        log(f"  {d.idVendor:04x}:{d.idProduct:04x}  bus {d.bus} addr {d.address}{mark}")
    dev = usb.core.find(idVendor=VID, idProduct=PID, backend=be)
    if dev is None:
        log(f"\nNo device {VID:04x}:{PID:04x} found. Is it plugged in and powered?")
        if any(d.idVendor == 0x04B4 for d in devs):
            log("A Cypress (04b4) device is present: the unit may be waiting for "
                "firmware from the Newport driver. Report this.")
        return 1

    # --- 2. Descriptors ------------------------------------------------------
    log("\n== Descriptors ==")
    try:
        log(str(dev))
    except Exception as e:     # string descriptors need the device open
        log(f"(full descriptor dump failed: {e})")
        for cfg in dev:
            for intf in cfg:
                for ep in intf:
                    log(f"  intf {intf.bInterfaceNumber} ep {ep.bEndpointAddress:#04x} "
                        f"attr {ep.bmAttributes:#04x} max {ep.wMaxPacketSize}")

    # --- 3. Claim ------------------------------------------------------------
    log("\n== Claim ==")
    try:
        try:
            dev.set_configuration()
        except usb.core.USBError as e:
            log(f"set_configuration: {e} (usually harmless)")
        usb.util.claim_interface(dev, 0)
        log("claimed interface 0")
    except Exception as e:
        log(f"FAILED: {e!r}")
        log("On Windows this almost always means the device is still on "
            "Cypress's CyUSB driver. Run Zadig and replace it with WinUSB.")
        return 1

    try:
        # --- 4. Read-only queries -----------------------------------------
        log("\n== Queries (\\r\\n) ==")
        for cmd in ["WAVE?", "SHUTTER?", "GRAT?", "FILTER?", "UNITS?", "INFO?",
                    "STB?", "STEP?", "BANDPASS?", "SLIT1MICRONS?", "FILTER1LABEL?"]:
            exchange(dev, cmd)
        for g in (1, 2, 3):
            for q in ("LINES?", "LABEL?", "ZERO?", "OFFSET?", "FACTOR?"):
                exchange(dev, f"GRAT{g}{q}", window_s=0.8)

        log("\n== Terminator check: WAVE? with \\n only ==")
        exchange(dev, "WAVE?", terminator=b"\n")

        log("\n== Back-to-back query timing (5x WAVE?) ==")
        for _ in range(5):
            exchange(dev, "WAVE?", window_s=0.5)

        # --- 5. Motion and shutter -----------------------------------------
        if args.move:
            lines = first_text(exchange(dev, "WAVE?")[0])
            start = float(lines[-1]) if lines else None
            if start is None:
                log("\nCould not read a start wavelength; skipping move test.")
            else:
                target = start + 10.0
                log(f"\n== GOWAVE {target:.3f} (from {start:.3f}): raw reply ==")
                exchange(dev, f"GOWAVE {target:.3f}", window_s=1.0)

                log("\n== Polling WAVE? during the move ==")
                t0, last = time.monotonic(), None
                while time.monotonic() - t0 < 30:
                    got, _ = exchange(dev, "WAVE?", window_s=0.3)
                    lines = first_text(got)
                    if lines and lines[-1] == last and abs(float(last) - target) < 0.05:
                        break
                    last = lines[-1] if lines else last
                log(f"move settled after ~{time.monotonic() - t0:.1f} s")

                log(f"\n== GOWAVE with HANDSHAKE 1 (Newport's way), back to {start:.3f} ==")
                exchange(dev, "HANDSHAKE 1")
                exchange(dev, f"GOWAVE {start:.3f}", window_s=15.0)
                exchange(dev, "HANDSHAKE 0")
                exchange(dev, "WAVE?")

            log("\n== Shutter ==")
            exchange(dev, "SHUTTER?")
            exchange(dev, "SHUTTER O")
            exchange(dev, "SHUTTER?")
            exchange(dev, "SHUTTER C")
            exchange(dev, "SHUTTER?")

        if args.grating:
            lines = first_text(exchange(dev, "GRAT?")[0])
            start = lines[-1].split(",")[0] if lines else None
            if start is None:
                log("\nCould not read the current grating; skipping grating test.")
            else:
                for g in (args.grating, start):
                    log(f"\n== GRAT {g}: raw reply, then polling GRAT? / WAVE? ==")
                    exchange(dev, f"GRAT {g}", window_s=1.0)
                    t0 = time.monotonic()
                    while time.monotonic() - t0 < 60:
                        lines = first_text(exchange(dev, "GRAT?", window_s=0.5)[0])
                        if lines and lines[-1].split(",")[0].strip() == str(g):
                            break
                    log(f"grating {g} reported after ~{time.monotonic() - t0:.1f} s")
                    exchange(dev, "WAVE?")
    finally:
        usb.util.release_interface(dev, 0)
        usb.util.dispose_resources(dev)
    log("\ndone")
    return 0


if __name__ == "__main__":
    rc = 1
    try:
        rc = main()
    finally:
        name = f"cornerstone_probe_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(name, "w") as f:
            f.write("\n".join(LOG) + "\n")
        print(f"\nlog saved to {name}")
    sys.exit(rc)
