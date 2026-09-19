#!/usr/bin/env python3
"""Sonda pty + select su macOS (debug CI).

Verifica il comportamento di select(timeout) su un pty slave in cbreak
DOPO che un primo byte e' stato letto: su macOS si sospetta un 'phantom
ready' che poi blocca os.read(). Ogni riga osservata viene emessa come
annotazione GitHub (::error) perche' i log dei job possono essere illeggibili.

Esce sempre 0: e' una sonda, non un test.
"""

import os
import sys
import time

CHILD = r"""
import os, select, sys, termios, tty
fd = sys.stdin.fileno()
old = termios.tcgetattr(fd)
tty.setcbreak(fd)
try:
    r, _, _ = select.select([fd], [], [], 0.8)
    print("SELECT1:", "READY" if r else "TIMEOUT", flush=True)
    if r:
        print("READ1:", os.read(fd, 16), flush=True)
    # Seconda attesa: NON arriva piu' input. Su Linux -> TIMEOUT. Su macOS?
    r, _, _ = select.select([fd], [], [], 0.8)
    print("SELECT2:", "READY" if r else "TIMEOUT", flush=True)
    if r:
        import fcntl
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        try:
            print("READ2(nonblock):", os.read(fd, 16), flush=True)
        except BlockingIOError:
            print("READ2(nonblock): WOULD-BLOCK (phantom ready!)", flush=True)
        finally:
            fcntl.fcntl(fd, fcntl.F_SETFL, flags)
    # Terza attesa identica alla prima, per escludere one-shot effects.
    r, _, _ = select.select([fd], [], [], 0.8)
    print("SELECT3:", "READY" if r else "TIMEOUT", flush=True)
finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old)
print("CHILD-DONE", flush=True)
"""


def main() -> int:
    import select as sel
    import pty

    pid, fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = "xterm-256color"
        os.execv(sys.executable, [sys.executable, "-c", CHILD])

    buf = b""
    output_lines = []

    def drain(wait):
        nonlocal buf
        deadline = time.time() + wait
        while time.time() < deadline:
            if not sel.select([fd], [], [], 0.05)[0]:
                return
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                return
            if not chunk:
                return
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                output_lines.append(line.decode(errors="replace").strip())

    try:
        # il figlio manda prima SELECT1 (attende input); diamogli il byte
        drain(1.5)
        os.write(fd, b"1")
        drain(4.0)
        # sicurezza: se SELECT2 fosse ready con read bloccante originale,
        # il figlio non arriverebbe a CHILD-DONE: annotiamo comunque.
        drain(1.0)
    finally:
        try:
            os.kill(pid, 9)
            os.waitpid(pid, 0)
        except Exception:
            pass
        os.close(fd)

    status = "COMPLETATO" if any("CHILD-DONE" in l for l in output_lines) else "APPESO"
    line = f"PROBE child={status} :: " + " | ".join(output_lines)
    print("::error ::" + line)
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
