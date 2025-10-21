**DC-Assignment2**
This project implements a Distributed Mutual Exclusion (DME) system using the Ricart–Agrawala algorithm, along with a simple collaborative chat-style application.

**Overview**

The system consists of **three distributed nodes** communicating over TCP:
1. **File Server (Node A)** - stores the shared `chat.log` file.
2. **User Node B**
3. **User Node C**

User nodes communicate directly using HTTP to coordinate critical section access (via DME) and to perform read/write operations to the shared file server.

Each user node runs:
- `dme.py` --> Implements Ricart-Agrawala DME algorithm (distributed middleware).  
- `dme_app_node.py` --> Implements CLI and file-server communication (application layer).  
- `file_server.py` --> Simple HTTP server to handle `/append` and `/view`.

## ⚙️ Setup Instructions

Get the IP address of each node
ip addr

Open TCP ports for inter-node communication:
sudo firewall-cmd --add-port=<port_number>/tcp --permanent
sudo firewall-cmd --reload

Install Python
sudo yum install -y python

Install NCAT (to test inter node connectivity)
sudo yum install -y nmap-ncat

**Test Connectivity**
start a listener that accepts one connection
ncat -l <pott-number>

ping <IP_Node_B>
nc -zv <IP_Node_B> 5001

### Installation

Clone the repo on all three nodes:
```bash
git clone [https://github.com/<yourusername>/DC-Assignment2.git](https://github.com/Shankar-Vaithilingam/DC-Assignment2.git)
cd DC-Assignment2

**Start File Server (Node A)**
python3 file_server.py 5000

**Start User Nodes**
Node B:
python3 app.py <IP_Node_B> 5001 <IP_Node_C>:5002 <IP_FILESERVER>:5000 <IP_FILESERVER>:5000

Node C:
python3 app.py <IP_Node_C> 5002 <IP_Node_B>:5001 <IP_FILESERVER>:5000 <IP_FILESERVER>:5000

**Commands**
post <text> - Sends a message (enters critical section using DME).
view - Displays the shared chat log.
quit - Exits the CLI.

Autopost Feature (for Testing)
You can use --autopost or --autopost-file to automatically send a post after a short delay - useful for concurrency tests.
Examples:
# Autopost simple text
python3 app.py <IP_Node_B> 5001 <IP_Node_C>:5002 <IP_FILESERVER>:5000 <IP_FILESERVER>:5000 --autopost "Hello_from_B" --delay 3

# Autopost a large 1MB file
python3 app.py <IP_Node_B> 5001 <IP_Node_C>:5002 <IP_FILESERVER>:5000 <IP_FILESERVER>:5000 --autopost-file large_text.txt --delay 3

**Test Cases**
<img width="685" height="386" alt="image" src="https://github.com/user-attachments/assets/74c04a64-891e-4ac2-adf1-2522c14001cc" />
✅ All Passed

References:
Ricart, G. & Agrawala, A. K. (1981) - An Optimal Algorithm for Mutual Exclusion in Computer Networks.
Communications of the ACM, 24(1), 9-17

