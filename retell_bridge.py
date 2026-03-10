from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Dict, Optional
from encoder import TextSpikeEncoder
from identity_manager import NodeIdentity
from spike_protocol import NeuralSpike, generate_task_id

app = FastAPI(title="INGRVM Retell Bridge", version="1.0.0")

# --- Resources ---
encoder = TextSpikeEncoder(num_steps=10)
identity = NodeIdentity()
node_id = identity.get_public_key_b64()

@app.post("/retell/webhook")
async def retell_webhook(request: Request):
    """
    Accepts webhooks from Retell AI.
    Specifically handles 'call_analyzed' or 'call_ended' events.
    """
    payload = await request.json()
    event_type = payload.get("event")
    call = payload.get("call", {})
    
    # Extract data from Retell's structure
    # Retell provides transcripts and analysis (sentiment, custom data)
    transcript = call.get("transcript", "")
    analysis = call.get("analysis", {})
    
    if not transcript:
        return {"status": "SKIPPED", "reason": "No transcript"}

    print(f"
[RETELL BRIDGE] Received event '{event_type}' for Call {call.get('call_id')}")
    print(f"[RETELL BRIDGE] Content: '{transcript[:50]}...'")

    # 1. Neuromorphic Encoding
    # Convert the voice transcript into a spike train
    spike_train = encoder.encode(transcript)
    
    # 2. Package into signed NeuralSpike
    # We use the temporal pattern to represent the voice 'intent'
    spike = NeuralSpike(
        task_id=generate_task_id(node_id, f"retell_{call.get('call_id')}"),
        ingrvm_id="voice_intent_analysis",
        node_id=node_id,
        input_hash="hash_of_voice_transcript"
    )
    # Use representative spikes from the train
    spike.set_spikes([int(s) for s in spike_train[0].tolist()[:3]])
    
    # 3. Cryptographic Signature
    spike.signature = identity.sign_data(spike.to_bin())

    print(f"[RETELL BRIDGE] Spike generated and signed. PeerID: {node_id[:8]}...")
    
    return {
        "status": "CONVERTED_TO_SPIKES",
        "task_id": spike.task_id,
        "peer_id": node_id
    }

if __name__ == "__main__":
    import uvicorn
    print("[RETELL BRIDGE] Gateway starting on http://127.0.0.1:8002")
    uvicorn.run(app, host="127.0.0.1", port=8002)
