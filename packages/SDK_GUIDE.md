# INGRVM Developer SDK: The 'Genome' Standard

This guide defines the standard process for creating, packaging, and deploying Spiking Neural Network (SNN) ingrvms to the INGRVM Mesh.

## 1. ingrvm Architecture (The Brain)
All ingrvms must be built using `snnTorch` and follow the `MiniBrain` template:
- **Input Layer:** Must handle normalized spike features (e.g., ASCII-to-Rate).
- **Hidden Layers:** Leaky Integrate-and-Fire (LIF) neurons with surrogate gradients.
- **Output Layer:** Firing-rate based decision (e.g., Classification).

## 2. The Manifest (`.json`)
Every ingrvm requires a `manifest.json` bundled inside the `.ingrvm` package:
```json
{
  "ingrvm_id": "unique_string_id",
  "name": "Human Readable Name",
  "version": "1.0.0",
  "author": "Developer ID",
  "layers": "3-8-2",
  "beta": 0.95,
  "threshold": 1.0,
  "description": "What this brain actually does."
}
```

## 3. The Packaging Process
1. **Train:** Use `train_ingrvm_0.py` to generate a `.pt` weights file.
2. **Pack:** Use `ingrvm_packager.py` to create the `.ingrvm` binary.
   - *Command:* `python ingrvm_packager.py`
3. **Audit:** Submit the package to a Tier II node for a **Pre-Frontal Cortex Audit**.
   - *Command:* `python validator_gate.py <package_path>`

## 4. Deployment
Once APPROVED, the ingrvm ID is registered on the **Shard Manager** and broadcast via the **Bootstrap Beacon**.

---
**Standardized for Sovereignty. Optimized for Life.** 🌿✨
