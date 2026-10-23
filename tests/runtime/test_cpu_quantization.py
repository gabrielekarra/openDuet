"""Numerical contract for the optional CPU quantized backbone; real gates run separately."""

import pytest

from openduet.kev.backends import quantize_cpu

torch = pytest.importorskip("torch")


def test_dynamic_quantization_keeps_indices_and_float32_backbone_outputs():
    torch.manual_seed(51)

    class Backbone(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.embedding = torch.nn.Embedding(10, 16)
            self.norm = torch.nn.LayerNorm(16)
            self.linear = torch.nn.Linear(16, 8)
            self.register_buffer("indices", torch.arange(8))

        def forward(self, tokens):
            return self.linear(self.norm(self.embedding(tokens)))

    model = Backbone().eval()
    tokens = torch.tensor([[1, 2, 3]])
    expected = model(tokens).detach()
    packed = quantize_cpu(model.bfloat16())
    actual = packed(tokens)
    assert actual.dtype == torch.float32
    assert packed.indices.dtype == torch.int64
    assert torch.allclose(actual, expected, atol=0.03, rtol=0.03)
    assert packed.linear.weight().dtype == torch.qint8
