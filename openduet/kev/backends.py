"""The same typed pointer readout on CPU/CUDA and Apple silicon."""

from __future__ import annotations

import os
import time

import numpy as np

from .adapter import decisions_from_logits, record_for
from .models import manifest, verify


def load_int8_model(base, tokenizer, head_dim):
    """Stream weights into quantized layers instead of materializing two backbones.

    Reuse Kev's encoder, cache and pointer readout unchanged. Only the backbone
    loader differs from upstream's constructor. LoRA stays in fp32 and is applied
    by PEFT over the frozen QLinear weights; the pointer head stays fp32 too.
    """
    import torch
    from transformers import AutoModelForCausalLM, QuantoConfig

    from .vendor.kev.model import DecisionModel, PointerHead, is_hybrid, pad_id

    class QuantizedDecisionModel(DecisionModel):
        def __init__(self):
            torch.nn.Module.__init__(self)
            foundation = AutoModelForCausalLM.from_pretrained(
                str(base),
                dtype=torch.float32,
                attn_implementation="eager",
                quantization_config=QuantoConfig(weights="int8"),
                device_map={"": "cpu"},
                local_files_only=True,
            )
            self.lm = foundation.model
            self.pad_id = pad_id(tokenizer)
            self.hybrid = is_hybrid(self.lm.config)
            self.option_isolation = False
            self.head = PointerHead(self.lm.config.hidden_size, dp=head_dim)
            self.device = "cpu"

    return QuantizedDecisionModel()


class TorchBackend:
    def __init__(self, device="cpu"):
        import torch
        from peft import PeftModel
        from transformers import AutoTokenizer

        from .vendor.kev.model import DecisionModel

        entries = {entry["role"]: entry for entry in manifest() if entry["backend"] == "torch"}
        checkpoint, base = verify(entries["decision"]), verify(entries["base"])
        metadata = torch.load(checkpoint / "head.pt", map_location="cpu", weights_only=True)
        self.tokenizer = AutoTokenizer.from_pretrained(checkpoint, local_files_only=True)
        dtype_name = os.environ.get("OPENDUET_KEV_DTYPE", "float32")
        if dtype_name not in {"float32", "bfloat16", "float16", "int8"} or (
            dtype_name == "float16" and device == "cpu"
        ):
            raise ValueError("Use float32/bfloat16, int8 on CPU, or float16 on CUDA")
        if dtype_name == "int8" and device != "cpu":
            raise ValueError("Dynamic INT8 is a CPU backend")
        self.model = (
            load_int8_model(base, self.tokenizer, metadata["head_dim"])
            if dtype_name == "int8"
            else DecisionModel(
                str(base),
                self.tokenizer,
                device,
                head_dim=metadata["head_dim"],
                dtype=getattr(torch, dtype_name),
            )
        )
        self.model.lm = PeftModel.from_pretrained(self.model.lm, checkpoint, local_files_only=True)
        self.model.head.load_state_dict(metadata["head"], strict=True)
        self.model.head.temperature = float(metadata.get("temperature", 1))
        if not np.isfinite(self.model.head.temperature) or self.model.head.temperature <= 0:
            raise ValueError("Invalid Kev temperature")
        self.model.eval()
        self.prefix = None
        self.state = None

    def decide_many(self, context, questions, *, calibrators=None, system=""):
        import torch

        started = time.perf_counter()
        record, owners = record_for(context, questions, system=system)
        encoded = self.model.encode(self.tokenizer, record, max_state=4096, max_branch=8192, strict=True)
        with torch.inference_mode():
            if self.state == record["state"] and self.prefix is not None:
                probabilities = self.model.probs_with_prefix(encoded, self.prefix)
            else:
                probabilities, self.prefix = self.model.probs_and_prefix(encoded)
                self.state = record["state"]
        logits = [np.log(np.maximum(row.detach().cpu().numpy(), 1e-300)) for row in probabilities]
        return decisions_from_logits(
            questions,
            owners,
            logits,
            temperature=self.model.head.temperature,
            calibrators=calibrators or [None] * len(questions),
            elapsed_ms=(time.perf_counter() - started) * 1000,
        )


class FakeBackend:
    """Synthetic fixture backend; production never silently falls back to this."""

    def decide_many(self, context, questions, *, calibrators=None, system=""):
        record, owners = record_for(context, questions, system=system)
        values = []
        for entry in record["questions"]:
            options = entry["options"]
            selected = options.index("yes") if "yes" in options else len(options) - 1
            values.append(np.asarray([8.0 if index == selected else -8.0 for index in range(len(options))]))
        return decisions_from_logits(
            questions,
            owners,
            values,
            temperature=1,
            calibrators=calibrators or [None] * len(questions),
            elapsed_ms=0,
        )
