#!/usr/bin/env python3
"""Echo test USB veze RPi <-> Nucleo.

Salje nasumicne binarne blokove, ceka da se vrate i proverava svaki bajt.
Meri vreme povratka (RTT) i broji greske. Nucleo mora da ima echo firmware
(nucleo/echo_test).

Primeri:
    ./tools/echo_test.py                          # /dev/nucleo, 460800, 60 s
    ./tools/echo_test.py --duration 3600          # 1 sat (test sa motorima)
    ./tools/echo_test.py --port /dev/ttyACM0 --block 128 --csv rezultat.csv
"""
import argparse
import csv
import os
import statistics
import sys
import time

try:
    import serial
except ImportError:
    sys.exit("Nedostaje pyserial: sudo apt install python3-serial")


def read_exact(ser, n, timeout_s):
    """Cita tacno n bajtova ili vraca ono sto je stiglo do isteka vremena."""
    buf = bytearray()
    deadline = time.perf_counter() + timeout_s
    while len(buf) < n:
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            break
        ser.timeout = min(remaining, 0.05)
        chunk = ser.read(n - len(buf))
        if chunk:
            buf.extend(chunk)
    return bytes(buf)


def percentile(sorted_vals, p):
    if not sorted_vals:
        return float("nan")
    k = min(len(sorted_vals) - 1, int(round(p / 100.0 * (len(sorted_vals) - 1))))
    return sorted_vals[k]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", default="/dev/nucleo")
    ap.add_argument("--baud", type=int, default=460800)
    ap.add_argument("--block", type=int, default=64, help="velicina bloka u bajtovima (1-256)")
    ap.add_argument("--duration", type=float, default=60.0, help="trajanje testa u sekundama")
    ap.add_argument("--timeout", type=float, default=0.2, help="cekanje na povratak bloka [s]")
    ap.add_argument("--report", type=float, default=10.0, help="interval izvestaja [s]")
    ap.add_argument("--csv", help="upisi RTT svakog bloka u CSV fajl")
    args = ap.parse_args()

    if not 1 <= args.block <= 256:
        sys.exit("--block mora biti izmedju 1 i 256 (velicina prijemnog bafera na Nucleo-u)")

    ser = serial.Serial(args.port, args.baud, timeout=0.05)
    time.sleep(0.2)
    ser.reset_input_buffer()

    ok = mismatch = timeouts = 0
    bytes_ok = 0
    rtts_ms = []
    csv_writer = None
    csv_file = None
    if args.csv:
        csv_file = open(args.csv, "w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["t_s", "rtt_ms", "status"])

    print(f"Echo test: {args.port} @ {args.baud}, blok {args.block} B, {args.duration:.0f} s")
    t_start = time.perf_counter()
    t_report = t_start + args.report

    try:
        while time.perf_counter() - t_start < args.duration:
            block = os.urandom(args.block)
            t0 = time.perf_counter()
            ser.write(block)
            back = read_exact(ser, len(block), args.timeout)
            rtt = (time.perf_counter() - t0) * 1000.0

            if back == block:
                ok += 1
                bytes_ok += len(block)
                rtts_ms.append(rtt)
                status = "ok"
            elif len(back) < len(block):
                timeouts += 1
                status = f"timeout({len(back)}/{len(block)})"
            else:
                mismatch += 1
                status = "mismatch"

            if status != "ok":
                # ocisti ostatke da se sledeci blok ne poravna pogresno
                time.sleep(0.05)
                ser.reset_input_buffer()
                print(f"  [{time.perf_counter() - t_start:7.1f} s] GRESKA: {status}")

            if csv_writer:
                csv_writer.writerow([f"{t0 - t_start:.4f}", f"{rtt:.3f}", status])

            now = time.perf_counter()
            if now >= t_report:
                last = sorted(rtts_ms[-2000:])
                print(f"  [{now - t_start:7.1f} s] ok={ok} greske={mismatch + timeouts} "
                      f"RTT p50={percentile(last, 50):.2f} ms p99={percentile(last, 99):.2f} ms")
                t_report = now + args.report
    except KeyboardInterrupt:
        print("\nPrekinuto.")
    finally:
        ser.close()
        if csv_file:
            csv_file.close()

    elapsed = time.perf_counter() - t_start
    total = ok + mismatch + timeouts
    s = sorted(rtts_ms)
    print("\n===== Rezultat =====")
    print(f"Trajanje:        {elapsed:.1f} s")
    print(f"Blokova:         {total}  (ok {ok}, pogresnih {mismatch}, timeout {timeouts})")
    print(f"Propusnost:      {bytes_ok * 2 / elapsed / 1024:.1f} KiB/s (oba smera)")
    if s:
        print(f"RTT min/avg:     {s[0]:.2f} / {statistics.fmean(s):.2f} ms")
        print(f"RTT p50/p99/max: {percentile(s, 50):.2f} / {percentile(s, 99):.2f} / {s[-1]:.2f} ms")
    verdict = "PROSAO" if total and mismatch == 0 and timeouts == 0 else "PAO"
    print(f"Test:            {verdict}")
    return 0 if verdict == "PROSAO" else 1


if __name__ == "__main__":
    sys.exit(main())
