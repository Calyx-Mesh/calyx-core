try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    # Mock classes for type hinting and inheritance
    class nn:
        class Module: pass
        class ModuleList: pass
        def Identity(): pass
    class torch:
        class Tensor: pass
        def device(x): return x
        def tensor(x): return x
        def zeros(x): return x
        def zeros_like(x): return x
        def cat(x, dim=0): return x
        def narrow(x, dim, start, length): return x

from typing import List, Dict, Tuple, Any, Optional

try:
    import snntorch as snn
    from quantization import BinaryLinear
    HAS_ML = True
except (ImportError, NameError):
    HAS_ML = False

class JitLeaky(nn.Module):
    """
    A JIT-scriptable version of the Leaky Integrate-and-Fire neuron.
    Optimized for Phase 9 Mobile SDK.
    """
    def __init__(self, beta: float = 0.9, threshold: float = 1.0):
        super().__init__()
        # Use buffers so JIT knows they are part of the module
        if HAS_TORCH:
            self.register_buffer('beta', torch.tensor(beta))
            self.register_buffer('threshold', torch.tensor(threshold))
            self.register_buffer('mem', torch.zeros(1))
        else:
            self.beta = beta
            self.threshold = threshold
            self.mem = None

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Note: We removed the HAS_ML check here to satisfy the JIT compiler.
        # This module should only be used in Torch-enabled environments.
        if self.mem.shape != x.shape:
            self.mem = torch.zeros_like(x)
        
        self.mem = self.beta * self.mem + x
        spk = (self.mem >= self.threshold).to(x.dtype)
        self.mem = self.mem - (spk * self.threshold)
        return spk, self.mem

class MiniBrain(nn.Module):
    """
    Standard SNN Shard Architecture used across INGRVM nodes.
    JIT-Compatible (uses ModuleList and JitLeaky).
    """
    # Type annotations for JIT
    num_inputs: int
    num_hidden: int
    num_outputs: int
    beta: float
    vth: float

    def __init__(self, layer_start: int = 0, layer_end: int = 31):
        super().__init__()
        self.layer_start = layer_start
        self.layer_end = layer_end
        
        # Hardcoded for JIT stability
        self.num_inputs = 3
        self.num_hidden = 8
        self.num_outputs = 2
        self.beta = 0.99
        self.vth = 0.5
        
        self.fc_layers = nn.ModuleList()
        self.lif_layers = nn.ModuleList()
        
        if layer_start == 0:
            if HAS_ML:
                self.input_proj = BinaryLinear(self.num_inputs, self.num_hidden)
            else:
                self.input_proj = nn.Identity()
        else:
            self.input_proj = nn.Identity()
        
        for i in range(layer_start, layer_end + 1):
            in_dim = self.num_hidden
            out_dim = self.num_outputs if i == 31 else self.num_hidden
            
            if HAS_ML:
                self.fc_layers.append(BinaryLinear(in_dim, out_dim))
                self.lif_layers.append(JitLeaky(beta=self.beta, threshold=self.vth))

    def forward(self, x: torch.Tensor, current_layer: int) -> Tuple[torch.Tensor, int, List[Dict[str, str]]]:
        current_x = x
        execution_steps: List[Dict[str, str]] = []
        
        current_x = current_x.view(1, -1)
        
        # 1. Dynamic projection if shape mismatch
        if current_x.shape[-1] != self.num_hidden and current_layer != 0:
            current_x = torch.narrow(current_x, 1, 0, min(current_x.shape[1], self.num_hidden))
            if current_x.shape[1] < self.num_hidden:
                padding = torch.zeros(current_x.shape[0], self.num_hidden - current_x.shape[1]).to(current_x.device)
                current_x = torch.cat([current_x, padding], dim=1)
            execution_steps.append({"layer": str(current_layer), "op": "dynamic_resize"})

        # 2. Input projection
        if current_layer == 0 and self.layer_start == 0:
            current_x = self.input_proj(current_x)
            execution_steps.append({"layer": "0", "op": "input_proj"})

        # 3. Sequential processing
        start_idx = max(0, current_layer - self.layer_start)
        
        # JIT-friendly iteration
        idx = 0
        for fc, lif in zip(self.fc_layers, self.lif_layers):
            if idx >= start_idx:
                actual_layer_num = self.layer_start + idx
                current_x = fc(current_x)
                current_x, _ = lif(current_x)
                execution_steps.append({"layer": str(actual_layer_num), "op": "snn_step"})
            idx += 1
        
        return current_x, self.layer_end + 1, execution_steps

class MockBrain:
    """ Fallback for environments without ML libraries. """
    def __init__(self, layer_start: int = 0, layer_end: int = 5):
        self.layer_start = layer_start
        self.layer_end = layer_end
    def to(self, device): return self
    def __call__(self, x: Any, current_layer: int) -> Tuple[Any, int, List[Dict[str, str]]]:
        execution_steps = [{"layer": str(i), "op": "mock"} for i in range(max(current_layer, self.layer_start), self.layer_end + 1)]
        return x, self.layer_end + 1, execution_steps
