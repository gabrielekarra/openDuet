"""The same typed pointer readout on CPU/CUDA and Apple silicon."""

from __future__ import annotations

import time

import numpy as np

from .adapter import decisions_from_logits, record_for
from .models import manifest, verify


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
        self.model = DecisionModel(str(base), self.tokenizer, device, head_dim=metadata["head_dim"])
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
