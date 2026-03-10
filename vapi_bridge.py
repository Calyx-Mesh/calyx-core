from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Dict
import torch
from encoder import TextSpikeEncoder
from identity_manager import NodeIdentity
from spike_protocol import NeuralSpike, generate_task_id

app = FastAPI(title="INGRVM Vapi Bridge", version="1.0.0")

# --- Bridge Resources ---
encoder = TextSpikeEncoder(num_steps=10)
identity = NodeIdentity()
node_id = identity.get_public_key_b64()

@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    """
    Accepts webhooks from Vapi.com.
    Converts voice transcriptions into neuromorphic spike trains.
    """
    payload = await request.json()
    
    # 1. Extract the transcript from Vapi's 'message' structure
    # Vapi sends 'message' type 'transcript' or 'end-of-call-report'
    msg = payload.get("message", {})
    transcript = ""
    
    if msg.get("type") == "transcript":
        transcript = msg.get("transcript", "")
    elif msg.get("type") == "end-of-call-report":
        transcript = msg.get("analysis", {}).get("summary", "")
    
    if not transcript:
        return {"status": "SKIPPED", "reason": "No transcript content"}

    print(f"\n[VAPI BRIDGE] Received Voice Input: '{transcript}'")

    # 2. Encode to Spikes
    spike_train = encoder.encode(transcript)
    
    # 3. Create Signed NeuralSpike
    # For this bridge, we'll use the first temporal step as the representative spike
    dense_spikes = [int(s) for s in spike_train[0].tolist()]
    
    # Pad to match our 3-input MiniBrain
    if len(dense_spikes) < 3:
        dense_spikes += [0] * (3 - len(dense_spikes))
    else:
        dense_spikes = dense_spikes[:3]

    spike = NeuralSpike(
        task_id=generate_task_id(node_id, "vapi_voice_task"),
        ingrvm_id="ingrvm_0",
        node_id=node_id,
        input_hash="hash_placeholder" # Would be hashed transcript
    )
    spike.set_spikes(dense_spikes)
    
    # 4. Sign
    binary_data = spike.to_bin()
    spike.signature = identity.sign_data(binary_data)

    print(f"[VAPI BRIDGE] Injected Spike Train into Mesh for Task: {spike.task_id}")
    
    return {
        "status": "INJECTED",
        "task_id": spike.task_id,
        "transcript_preview": transcript[:20] + "..."
    }

if __name__ == "__main__":
    import uvicorn
    print("[VAPI BRIDGE] Gateway starting on http://127.0.0.1:8001")
    uvicorn.run(app, host="127.0.0.1", port=8001)
