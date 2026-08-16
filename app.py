import os
import re
import signal
import subprocess
import sys


# ============================================================
# CONFIGURATION
# ============================================================

FREEYA_HOST = "freeya.in"
FREEYA_USER = "tunnel"

# Change this to the public name you want on FreeYa.
FREEYA_NAME = os.environ.get("FREEYA_NAME", "guna")

# Your local web application port.
LOCAL_PORT = int(os.environ.get("LOCAL_PORT", "80"))

LOCAL_HOST = "127.0.0.1"


# ============================================================
# GLOBALS
# ============================================================

ssh_process = None


# ============================================================
# DIAGNOSTICS
# ============================================================

def command_output(command):
    try:
        result = subprocess.run(
            command,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )

        output = result.stdout.strip()

        if output:
            print(output)

        return result.returncode, output

    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1, ""


def diagnostics():
    print("=" * 60)
    print("FEATHERPANEL CONTAINER CHECK")
    print("=" * 60)

    print("\n$ whoami")
    command_output("whoami")

    print("\n$ id")
    command_output("id")

    print("\n$ id 998")
    command_output("id 998")

    print("\n$ getent passwd 998")
    _, passwd_998 = command_output("getent passwd 998")

    print("\n$ getent group 998")
    _, group_998 = command_output("getent group 998")

    print("\n$ which ssh")
    command_output("which ssh")

    print("\n$ ssh -V")
    command_output("ssh -V")

    print("\n$ ls -ld /home/container")
    command_output("ls -ld /home/container")

    print("\n$ stat /home/container")
    command_output(
        "stat -c '%n owner=%u group=%g mode=%a' /home/container"
    )

    print("\n" + "=" * 60)

    if passwd_998:
        print("OK: UID 998 has a passwd entry.")
    else:
        print("ERROR: UID 998 still has no passwd entry.")

    if group_998:
        print("OK: GID 998 has a group entry.")
    else:
        print("ERROR: GID 998 still has no group entry.")

    print("=" * 60)


# ============================================================
# FREEYA SSH
# ============================================================

def start_freeya():
    global ssh_process

    ssh_path = "/usr/bin/ssh"

    if not os.path.exists(ssh_path):
        ssh_path = "ssh"

    command = [
        ssh_path,

        # Automatically accept a NEW host key.
        # Still protects against a changed known host key.
        "-o",
        "StrictHostKeyChecking=accept-new",

        # Don't request a pseudo-terminal.
        "-T",

        # Remote port allocation.
        "-R",
        f"0:{LOCAL_HOST}:{LOCAL_PORT}",

        f"{FREEYA_USER}@{FREEYA_HOST}",
        FREEYA_NAME,
    ]

    print("\n" + "=" * 60)
    print("STARTING FREEYA")
    print("=" * 60)

    print(
        "Command:",
        " ".join(command)
    )

    print("=" * 60)

    ssh_process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    url_pattern = re.compile(
        r"https?://[^\s]+",
        re.IGNORECASE,
    )

    port_patterns = [
        re.compile(
            r"(?:assigned\s+port|remote\s+port|public\s+port)"
            r"\s*[:=]?\s*(\d+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bport\s*[:=]\s*(\d+)",
            re.IGNORECASE,
        ),
    ]

    public_url = None
    assigned_port = None

    try:
        for raw_line in ssh_process.stdout:
            line = raw_line.rstrip()

            # Always show SSH/FreeYa output.
            print(line, flush=True)

            lower = line.lower()

            # ------------------------------------------------
            # SSH HOST KEY PROMPT
            # ------------------------------------------------

            if (
                "are you sure you want to continue connecting"
                in lower
                and "yes/no" in lower
            ):
                print(
                    "[SSH] Host-key confirmation detected."
                )
                print(
                    "[SSH] Automatically answering: yes"
                )

                try:
                    ssh_process.stdin.write("yes\n")
                    ssh_process.stdin.flush()
                except BrokenPipeError:
                    pass

                continue

            # ------------------------------------------------
            # PUBLIC URL
            # ------------------------------------------------

            match = url_pattern.search(line)

            if match:
                url = match.group(0).rstrip(".,)")

                if url != public_url:
                    public_url = url

                    print("\n" + "=" * 60)
                    print("PUBLIC URL")
                    print("=" * 60)
                    print(public_url)
                    print("=" * 60)
                    print(flush=True)

            # ------------------------------------------------
            # ASSIGNED PORT
            # ------------------------------------------------

            for pattern in port_patterns:
                match = pattern.search(line)

                if match:
                    port = match.group(1)

                    if port != assigned_port:
                        assigned_port = port

                        print("\n" + "=" * 60)
                        print("ASSIGNED PORT")
                        print("=" * 60)
                        print(port)
                        print("=" * 60)
                        print(flush=True)

                    break

    except KeyboardInterrupt:
        stop_freeya()

    return_code = ssh_process.wait()

    print("\n" + "=" * 60)
    print("FREEYA SSH EXITED")
    print("=" * 60)
    print(f"Exit code: {return_code}")

    if public_url:
        print(f"Public URL: {public_url}")

    if assigned_port:
        print(f"Assigned port: {assigned_port}")

    if return_code != 0:
        print("FreeYa tunnel failed.")

    return return_code


# ============================================================
# STOP
# ============================================================

def stop_freeya(signum=None, frame=None):
    global ssh_process

    print("\nStopping FreeYa tunnel...")

    if ssh_process is not None:
        try:
            ssh_process.terminate()
            ssh_process.wait(timeout=5)
        except Exception:
            try:
                ssh_process.kill()
            except Exception:
                pass

    sys.exit(0)


# ============================================================
# SIGNAL HANDLERS
# ============================================================

signal.signal(signal.SIGTERM, stop_freeya)
signal.signal(signal.SIGINT, stop_freeya)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    diagnostics()

    print("\nConfiguration:")
    print(f"FreeYa name : {FREEYA_NAME}")
    print(f"Local host  : {LOCAL_HOST}")
    print(f"Local port  : {LOCAL_PORT}")

    start_freeya()
