# THOR INGRVM: Network Integrity Fix Roadmap

## Problem: Windows Secure Upgrade Failure
The `py-libp2p` library's security handshake (Noise/TLS) is consistently failing on Windows loopback (127.0.0.1) due to early stream closures during the `multistream-select` phase.

## The "Build Prior" Fix: Mesh Bootstrap & Relay Service
To resolve this, we need to build a dedicated **Bootstrap Relay**.

### 1. Bootstrap Beacon (`bootstrap_node.py`)
- **Purpose:** Act as a central meeting point for mesh nodes.
- **Why it fixes it:** Direct P2P handshakes on Windows often fail because nodes can't agree on who "starts" the secure talk. A Relay facilitates the handshake by proxying the initial identification.

### 2. mDNS Discovery Layer
- **Purpose:** Automatically find other nodes on the LAN using local broadcast rather than static IP files.
- **Status:** Currently mocked; needs a real `zeroconf` implementation to stabilize local connections.

### 3. Identify Protocol Hardening
- We need to ensure the `Identify` protocol finishes *before* GossipSub/FloodSub starts. Currently, they are racing, which contributes to the handshake timeout.

## Action Plan
- [ ] Implement `bootstrap_node.py` (The "Lighthouse").
- [ ] Integrate `Identify` protocol events into `neural_node.py`.
- [ ] Move from Loopback (127.0.0.1) to LAN IPs (192.168.x.x) to test OS firewall behavior.
