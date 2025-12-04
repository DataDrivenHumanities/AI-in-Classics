import sys
import types
import numpy as np
import pytest

# ---------------------------------------------------------------------
# Test-only stubs so we don't need sklearn or real TensorFlow.
# ---------------------------------------------------------------------

# Fake modelCreation module so `import modelCreation` works in completion.py
model_creation_stub = types.ModuleType("modelCreation")

_SEQ_LEN = 32

def _getSeqLen():
    return _SEQ_LEN

def _sequenceToInputFormat(text: str):
    # Just return some fixed-size numeric array; details don't matter here.
    return np.zeros((_SEQ_LEN,), dtype=float)

def _decode(idx: int) -> str:
    # Map index -> A..Z cycle
    return chr(ord("A") + (idx % 26))

model_creation_stub.getSeqLen = _getSeqLen
model_creation_stub.sequenceToInputFormat = _sequenceToInputFormat
model_creation_stub.decode = _decode

sys.modules["modelCreation"] = model_creation_stub

# Fake tensorflow module so `tf.keras.models.load_model(...)` works
tf_stub = types.ModuleType("tensorflow")
keras_stub = types.ModuleType("keras")
models_stub = types.ModuleType("models")

class _DummyModel:
    def compile(self, *args, **kwargs):
        return None

    def __call__(self, x, *args, **kwargs):
        # Dummy probability distribution
        return np.array([[0.1, 0.7, 0.2]])

def _load_model(path: str):
    return _DummyModel()

models_stub.load_model = _load_model
keras_stub.models = models_stub
tf_stub.keras = keras_stub

sys.modules["tensorflow"] = tf_stub

# Now import the real completion module (uses our stubs)
import backend.completion.completion as completion_module


def test_getNextCharsVector_basic():
    # Simple probability distribution
    prob_dist = np.array([0.05, 0.2, 0.6, 0.15])
    threshold = 0.1

    result = completion_module.getNextCharsVector(prob_dist, threshold)

    # It should be a list of characters ordered by probability (desc).
    assert isinstance(result, list)
    assert all(isinstance(c, str) for c in result)
    assert len(result) >= 1
