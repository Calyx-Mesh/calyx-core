from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import torch
from encoder import TextSpikeEncoder
from neural_node import MiniBrain

app = FastAPI(title="INGRVM AI Gateway", version="1.0.0")

# --- Logic Initialization ---
# Mocking the local node's resources
encoder = TextSpikeEncoder(num_steps=10)
brain = MiniBrain()
# Load pre-initialized membrane states
mem1 = brain.lif1.init_leaky()
mem2 = brain.lif2.init_leaky()

class InferenceRequest(BaseModel):
    text: str
    ingrvm_id: str = "ingrvm_0"

class InferenceResponse(BaseModel):
    sentiment: str
    spikes_fired: int
    status: str

@app.get("/")
def read_root():
    return {"message": "INGRVM Gateway is Active", "aesthetic": "Solarpunk"}

@app.post("/infer", response_model=InferenceResponse)
async def infer(request: InferenceRequest):
    """
    Standard API endpoint for external apps to use the AI brain.
    """
    global mem1, mem2
    
    if not request.text:
        raise HTTPException(status_code=400, detail="Text input is required.")

    # 1. Encode
    spike_train = encoder.encode(request.text)
    
    # 2. Process
    total_spikes = 0
    fired_count = 0
    
    # Reset for this request
    mem1 = brain.lif1.init_leaky()
    mem2 = brain.lif2.init_leaky()
    
    for step in range(spike_train.shape[0]):
        # Pad/Slice to match brain input=3
        input_data = torch.zeros(3)
        chars_to_read = min(len(request.text), 3)
        input_data[:chars_to_read] = spike_train[step, :chars_to_read]
        
        # Single-step inference
        final_spk, mem1, mem2 = brain(input_data, mem1, mem2)
        total_spikes += int(final_spk.sum().item())
        if final_spk.sum() > 0: fired_count += 1

    # 3. Respond
    sentiment = "POSITIVE" if fired_count > 0 else "NEGATIVE"
    
    return InferenceResponse(
        sentiment=sentiment,
        spikes_fired=total_spikes,
        status="PROCESSED_LOCALLY"
    )

if __name__ == "__main__":
    import uvicorn
    from config import INGRVMConfig
    conf = INGRVMConfig()
    host = conf.get("node", "api_host") or "127.0.0.1"
    port = conf.get("node", "api_port") or 8000
    print(f"[GATEWAY] Starting INGRVM REST API on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
