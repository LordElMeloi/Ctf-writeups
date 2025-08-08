# 🧱 Brick by Brick — TryHackMe CTF Write-Up

**Category:** Web Exploitation, Post-Exploitation, Threat Intelligence  
**Difficulty:** Easy  
**Player:** David Umoh (LordElMeloi)  
**Platform:** TryHackMe  
**Completion Date:** August 2025  

---

## 🧩 Initial Enumeration

### 🔹 Add Target to Hosts File

To work comfortably with the domain, I echoed the target IP to `/etc/hosts`:

```bash
echo "10.10.X.X brick.thm" | sudo tee -a /etc/hosts
```

### 🔹 Nmap Scan

I started enumeration using Nmap:

```bash
nmap -sC -sV -oA brickscan 10.10.X.X
```

Discovered an open web server (HTTP) running WordPress.

### 🔹 WordPress Version Enumeration

Navigated to the following path:

```
http://brick.thm/wp-content/themes/bricks/style.css
```

This CSS file revealed the version of **Bricks Builder** in a comment:

```
Version: 1.9.5
```

---

## 🚨 Vulnerability Discovery

The Bricks Builder version `1.9.5` is vulnerable to **CVE-2024-25600**, a known authenticated Remote Code Execution flaw. I used the publicly available exploit from:

> https://github.com/K3ysTr0K3R/CVE-2024-25600-EXPLOIT

Running the script --> ```python3 CVE-2024-25600.py -u https://bricks.thm/```.

---

## 🖥️ Post-Exploitation: Privilege Persistence & Mining Activity

### 🔹 Checking Running Services

```bash
systemctl | grep running
```

Found a suspicious service:

```text
ubuntu.service
```

### 🔹 Inspecting the Service File

```bash
cat /etc/systemd/system/ubuntu.service
```

Contents:

```ini
[Unit]
Description=TRYHACK3M

[Service]
Type=simple
ExecStart=/lib/NetworkManager/nm-inet-dialog
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

This service runs a binary masquerading as a NetworkManager component.

---

## 🔍 Malware Analysis & Log Hunting

### 🔹 Inspecting the Binary Path

```bash
ls -lah /lib/NetworkManager/
```

Found a suspicious file:
```
nm-inet-dialog
```

Also found a **log-like file**:
```
inet.conf
```

### 🔹 Reading the Log File

```bash
cat /lib/NetworkManager/inet.conf
```

Contents revealed:

```text
ID: 5757314e65474e5962484a4f656d787457544e424e574648555446684d3070735930684b616c70555a7a566b52335276546b686b65575248647a525a57466f77546b64334d6b347a526d685a6255313459316873636b35366247315a4d304531595564476130355864486c6157454a3557544a564e453959556e4a685246497a5932355363303948526a4a6b52464a7a546d706b65466c525054303d
Status: Mining!
Bitcoin Miner Thread Started
```

### 🔹 Decoding the ID

Used CyberChef’s “Magic” function to decode the `ID`:

Result:

```text
bc1qyk79fcp9hd5kreprce89tkh4wrtl8avt4l67qa
```

Also found a second similar string:
```
bc1qyk79fcp9had5kreprce89tkh4wrtl8avt4l67qa
```

These appeared to be **Bitcoin wallet addresses**.

---

## 🕵️‍♂️ Threat Intelligence & Attribution

I then explored blockchain explorers (e.g., Blockstream.info, btcscan.org) and used Google to search for known associations with these wallet addresses.

One address found in the miner logs led me to a different address:

```text
32pTjxTNi7snk8sodrgfmdKao3DEn1nVJM
```

Upon searching this address, I found a **press release** attributing it to the **LOCKBIT ransomware group**.

### ✅ Confirmed:
- The machine had been backdoored using a systemd service.
- A miner was deployed and logging activity locally.
- At least one associated wallet address linked back to a known cybercriminal group (LOCKBIT).

---

## 🧠 Lessons Learned

- Always check `/etc/systemd/system` for persistence mechanisms.
- Malicious binaries can be hidden in common Linux paths under deceptive names.
- Even if external communications (like mining pools) are blocked, logs can reveal mining status.
- Attribution is possible via reused wallet addresses tied to threat actors.

---

## 🧰 Tools Used

- `nmap`, `curl`, `cat`, `systemctl`, `ls`
- CyberChef (for decoding)
- Blockchain Explorer
- Google (OSINT)

---
## Answers
- What is the content of the hidden .txt file in the web folder?
  flag > THM{fl46_650c844110baced87e1606453b93f22a}
 
 
- What is the name of the suspicious process?
  ```nm-inet-dialog```


- What is the service name affiliated with the suspicious process?

  ```ubuntu.service```

- What is the log file name of the miner instance?
  ```ls -lah /lib/NetworkManager```

  answer → inet.conf

- What is the wallet address of the miner instance?

  bc1qyk79fcp9hd5kreprce89tkh4wrtl8avt4l67qa

- The wallet address used has been involved in transactions between wallets belonging to which threat group?
  answer --> LockBit

## 🎯 Goal Achieved

- Gained RCE using CVE-2024-25600  
- Identified persistence via a systemd service  
- Discovered and analyzed a Bitcoin miner  
- Linked mining wallet to the **LOCKBIT** ransomware group  

---

## 📎 References

- [Bricks Builder CVE-2024-25600](https://nvd.nist.gov/vuln/detail/CVE-2024-25600)  
- [Exploit Script](https://github.com/K3ysTr0K3R/CVE-2024-25600-EXPLOIT)  
- [CyberChef](https://gchq.github.io/CyberChef)  
- [Blockstream Explorer](https://blockstream.info/)  
- [Press Article – LOCKBIT Wallet Attribution](#) *(Include the exact article link if public)*

---

*Write-up by [David Umoh (LordElMeloi)](https://github.com/LordElMeloi)*  
*Red Team & Cybersecurity Enthusiast — Top 4% on TryHackMe*

# 🧱 Brick by Brick — TryHackMe CTF Write-Up

**Category:** Web Exploitation, Post-Exploitation, Threat Intelligence  
**Difficulty:** Medium  
**Player:** David Umoh (LordElMeloi)  
**Platform:** TryHackMe  
**Completion Date:** August 2025  

---

## 🧩 Initial Enumeration

### 🔹 Add Target to Hosts File

To work comfortably with the domain, I echoed the target IP to `/etc/hosts`:

```bash
echo "10.10.X.X brick.thm" | sudo tee -a /etc/hosts
```

### 🔹 Nmap Scan

I started enumeration using Nmap:

```bash
nmap -sC -sV -oA brickscan 10.10.X.X
```

Discovered an open web server (HTTP) running WordPress.

### 🔹 WordPress Version Enumeration

Navigated to the following path:

```
http://brick.thm/wp-content/themes/bricks/style.css
```

This CSS file revealed the version of **Bricks Builder** in a comment:

```
Version: 1.9.5
```

---

## 🚨 Vulnerability Discovery

The Bricks Builder version `1.9.5` is vulnerable to **CVE-2024-25600**, a known authenticated Remote Code Execution flaw. I used the publicly available exploit from:

> https://github.com/K3ysTr0K3R/CVE-2024-25600-EXPLOIT

Running the script --> ```python3 CVE-2024-25600.py -u https://bricks.thm/```.

---

## 🖥️ Post-Exploitation: Privilege Persistence & Mining Activity

### 🔹 Checking Running Services

```bash
systemctl | grep running
```

Found a suspicious service:

```text
ubuntu.service
```

### 🔹 Inspecting the Service File

```bash
cat /etc/systemd/system/ubuntu.service
```

Contents:

```ini
[Unit]
Description=TRYHACK3M

[Service]
Type=simple
ExecStart=/lib/NetworkManager/nm-inet-dialog
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

This service runs a binary masquerading as a NetworkManager component.

---

## 🔍 Malware Analysis & Log Hunting

### 🔹 Inspecting the Binary Path

```bash
ls -lah /lib/NetworkManager/
```

Found a suspicious file:
```
nm-inet-dialog
```

Also found a **log-like file**:
```
inet.conf
```

### 🔹 Reading the Log File

```bash
cat /lib/NetworkManager/inet.conf
```

Contents revealed:

```text
ID: 5757314e65474e5962484a4f656d787457544e424e574648555446684d3070735930684b616c70555a7a566b52335276546b686b65575248647a525a57466f77546b64334d6b347a526d685a6255313459316873636b35366247315a4d304531595564476130355864486c6157454a3557544a564e453959556e4a685246497a5932355363303948526a4a6b52464a7a546d706b65466c525054303d
Status: Mining!
Bitcoin Miner Thread Started
```

### 🔹 Decoding the ID

Used CyberChef’s “Magic” function to decode the `ID`:

Result:

```text
bc1qyk79fcp9hd5kreprce89tkh4wrtl8avt4l67qa
```

Also found a second similar string:
```
bc1qyk79fcp9had5kreprce89tkh4wrtl8avt4l67qa
```

These appeared to be **Bitcoin wallet addresses**.

---

## 🕵️‍♂️ Threat Intelligence & Attribution

I then explored blockchain explorers (e.g., Blockstream.info, btcscan.org) and used Google to search for known associations with these wallet addresses.

One address found in the miner logs led me to a different address:

```text
32pTjxTNi7snk8sodrgfmdKao3DEn1nVJM
```

Upon searching this address, I found a **press release** attributing it to the **LOCKBIT ransomware group**.

### ✅ Confirmed:
- The machine had been backdoored using a systemd service.
- A miner was deployed and logging activity locally.
- At least one associated wallet address linked back to a known cybercriminal group (LOCKBIT).

---

## 🧠 Lessons Learned

- Always check `/etc/systemd/system` for persistence mechanisms.
- Malicious binaries can be hidden in common Linux paths under deceptive names.
- Even if external communications (like mining pools) are blocked, logs can reveal mining status.
- Attribution is possible via reused wallet addresses tied to threat actors.

---

## 🧰 Tools Used

- `nmap`, `curl`, `cat`, `systemctl`, `ls`
- CyberChef (for decoding)
- Blockchain Explorer
- Google (OSINT)

---
## Answers
- What is the content of the hidden .txt file in the web folder?
  flag > THM{fl46_650c844110baced87e1606453b93f22a}
 
 
- What is the name of the suspicious process?
  ```nm-inet-dialog```


- What is the service name affiliated with the suspicious process?

  ```ubuntu.service```

- What is the log file name of the miner instance?
  ```ls -lah /lib/NetworkManager```

  answer → inet.conf

- What is the wallet address of the miner instance?

  bc1qyk79fcp9hd5kreprce89tkh4wrtl8avt4l67qa

- The wallet address used has been involved in transactions between wallets belonging to which threat group?
  answer --> LockBit

## 🎯 Goal Achieved

- Gained RCE using CVE-2024-25600  
- Identified persistence via a systemd service  
- Discovered and analyzed a Bitcoin miner  
- Linked mining wallet to the **LOCKBIT** ransomware group  

---

## 📎 References

- [Bricks Builder CVE-2024-25600](https://nvd.nist.gov/vuln/detail/CVE-2024-25600)  
- [Exploit Script](https://github.com/K3ysTr0K3R/CVE-2024-25600-EXPLOIT)  
- [CyberChef](https://gchq.github.io/CyberChef)  
- [Blockstream Explorer](https://blockstream.info/)  
- [Press Article – LOCKBIT Wallet Attribution](#) *(Include the exact article link if public)*

---

*Write-up by [David Umoh (LordElMeloi)](https://github.com/LordElMeloi)*  
*Red Team & Cybersecurity Enthusiast — Top 4% on TryHackMe*
