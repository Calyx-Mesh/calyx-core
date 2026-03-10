# Contributing to Project INGRVM

Welcome to the resistance. We are building a sovereign AI mesh, and we need your code. However, this is a **Solarpunk** project, which means we code differently here.

## 1. The Solarpunk Code Standard
*   **Efficiency First:** If you can do it in O(n), don't do it in O(n^2). Every CPU cycle wasted is energy wasted.
*   **Bio-Mimetic Naming:** We prefer `nerve_fiber` over `connection_pipe`, `metabolism` over `energy_manager`. The code should feel alive.
*   **No Black Boxes:** Every algorithm must be auditable. If we can't explain it, we don't merge it.

## 2. Pull Request (PR) Protocol
1.  **Fork & Branch:** Create a branch for your feature (`feature/new-ingrvm`).
2.  **The "Pre-Flight" Check:** You MUST run `python preflight.py` before submitting. If it fails, your PR is auto-rejected.
3.  **Documentation:** If you add a feature, update `SDK_GUIDE.md`.
4.  **Persona:** Your commit messages should be professional but can have personality.

## 3. Core Bounties (Where we need help)
*   **Optimization:** Optimizing `spike_protocol.py` for lower latency.
*   **Security:** Auditing `zk_proof_mock.py` and replacing mock hashes with real EZKL circuits.
*   **Mobile:** Porting `INGRVMClient.js` to a real React Native build.

## 4. Code of Conduct
*   **Be Constructive:** We are building a new world, not tearing down people.
*   **No Corp-Speak:** Speak like a human, not a PR department.
*   **Meritocracy:** The `RewardEngine` doesn't lie. Your code quality determines your reputation.

**Verify your logic. Sign your work. Plant the seed.**
