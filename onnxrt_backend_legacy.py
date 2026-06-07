import dataclasses
import logging
import torch
import torch.fx
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from pathlib import Path

try:
    import onnx
    import onnxruntime as ort
    _SUPPORT_ONNXRT = True
except ImportError:
    _SUPPORT_ONNXRT = False
    ort = None

logger = logging.getLogger(__name__)

def is_onnxrt_backend_supported() -> bool:
    return _SUPPORT_ONNXRT and ort is not None

@dataclasses.dataclass(frozen=True)
class OrtBackendOptions:
    preferred_execution_providers: Optional[Sequence[str]] = None
    default_execution_providers: Optional[Sequence[str]] = None
    use_aot_autograd: bool = False  # Disabled for broader compatibility
    export_options: Optional[Any] = None
    sess_options: Optional[ort.SessionOptions] = None

class SimpleOrtBackend:
    """Simplified ONNX Runtime backend for older hardware / older PyTorch.
    Works with CPU-first setups, your macOS x86_64, and modest Intel CPUs.
    """
    
    def __init__(self, options: Optional[OrtBackendOptions] = None):
        self._options = options or OrtBackendOptions()
        self._session_cache: Dict = {}
        self.execution_count = 0

    def _get_providers(self) -> List[str]:
        """Safe provider selection for old hardware."""
        if self._options.preferred_execution_providers:
            return list(self._options.preferred_execution_providers)
        
        providers = []
        if torch.cuda.is_available():
            providers.append("CUDAExecutionProvider")
        providers.append("CPUExecutionProvider")  # Always fallback
        
        if self._options.default_execution_providers:
            providers.extend(self._options.default_execution_providers)
        
        # Remove duplicates while preserving order
        seen = set()
        return [p for p in providers if not (p in seen or seen.add(p))]

    def _export_to_onnx(self, graph_module: torch.fx.GraphModule, args) -> bytes:
        """Basic export that works on older PyTorch + ONNX versions."""
        try:
            # Simple torch.onnx.export path for maximum compatibility
            example_inputs = tuple(args) if isinstance(args, (list, tuple)) else (args,)
            
            # Use a temp file or bytes for older exporter compatibility
            onnx_bytes = torch.onnx.export(
                graph_module,
                example_inputs,
                None,  # Don't write to file
                export_params=True,
                opset_version=17,  # Widely supported
                do_constant_folding=True,
                input_names=[f"input_{i}" for i in range(len(example_inputs))],
                output_names=[f"output_{i}" for i in range(len(graph_module.graph.outputs))],
                dynamic_axes=None,  # Disable for stability on old hardware
                verbose=False
            )
            if isinstance(onnx_bytes, bytes):
                return onnx_bytes
            # Fallback if export returns model proto
            return onnx_bytes.SerializeToString() if hasattr(onnx_bytes, "SerializeToString") else b""
        except Exception as e:
            logger.warning(f"Standard export failed, trying simpler path: {e}")
            # Ultra-minimal fallback
            torch.onnx.export(
                graph_module, example_inputs, "temp.onnx",
                export_params=True, opset_version=13  # Even older opset
            )
            with open("temp.onnx", "rb") as f:
                data = f.read()
            Path("temp.onnx").unlink(missing_ok=True)
            return data

    def _ort_accelerated_call(self, graph_module: torch.fx.GraphModule, *args, **kwargs):
        """Core execution path - simple, reliable, CPU-friendly."""
        cache_key = id(graph_module)
        
        if cache_key not in self._session_cache:
            onnx_model_bytes = self._export_to_onnx(graph_module, args)
            
            sess_options = self._options.sess_options or ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            # CPU-friendly settings
            sess_options.intra_op_num_threads = 0  # Let OS decide
            sess_options.inter_op_num_threads = 0
            
            session = ort.InferenceSession(
                onnx_model_bytes,
                sess_options=sess_options,
                providers=self._get_providers()
            )
            
            self._session_cache[cache_key] = {
                "session": session,
                "input_names": [i.name for i in session.get_inputs()],
                "output_names": [o.name for o in session.get_outputs()]
            }
        
        cached = self._session_cache[cache_key]
        session = cached["session"]
        input_names = cached["input_names"]
        
        # Prepare inputs
        inputs = {}
        for name, arg in zip(input_names, args):
            if isinstance(arg, torch.Tensor):
                inputs[name] = arg.cpu().numpy() if arg.is_cuda else arg.numpy()
            else:
                inputs[name] = arg
        
        self.execution_count += 1
        outputs = session.run(cached["output_names"], inputs)
        
        # Convert back to tensors on original device
        result = []
        for out in outputs:
            tensor_out = torch.from_numpy(out)
            # Try to match original device if possible
            if args and isinstance(args[0], torch.Tensor):
                tensor_out = tensor_out.to(args[0].device)
            result.append(tensor_out)
        
        return tuple(result) if len(result) > 1 else result[0]

    def compile(self, graph_module: torch.fx.GraphModule, args):
        """Minimal compile - just wrap the forward call."""
        # Replace the forward with our accelerated version
        original_forward = graph_module.forward
        
        def compiled_forward(*args, **kwargs):
            return self._ort_accelerated_call(graph_module, *args, **kwargs)
        
        graph_module.forward = compiled_forward
        return graph_module

    def __call__(self, graph_module: torch.fx.GraphModule, args):
        """Entry point for torch.compile(backend=...)"""
        return self.compile(graph_module, args)

# Public API - use this
def torch_compile_backend(graph_module, args, *, options=None):
    backend = SimpleOrtBackend(options)
    return backend(graph_module, args)
