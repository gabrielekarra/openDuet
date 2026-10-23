"""CPU weight-only quantization must preserve dtype, integer buffers and PEFT adapters."""

import pytest

torch = pytest.importorskip("torch")
quanto = pytest.importorskip("optimum.quanto")


def test_quantized_backbone_accepts_fp32_lora_without_changing_indices():
    from peft import LoraConfig, get_peft_model

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
    quanto.quantize(model, weights=quanto.qint8)
    quanto.freeze(model)
    adapted = get_peft_model(model, LoraConfig(r=2, lora_alpha=4, target_modules=["linear"]))
    actual = adapted(tokens)
    assert actual.dtype == torch.float32
    assert adapted.indices.dtype == torch.int64
    assert torch.allclose(actual, expected, atol=0.03, rtol=0.03)
    assert isinstance(adapted.linear.base_layer, quanto.QLinear)
    assert adapted.linear.base_layer.frozen
