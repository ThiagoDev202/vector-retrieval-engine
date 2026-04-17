---
title: Cosine similarity, explained
source: autoral
language: en
---

# Cosine similarity, explained

Cosine similarity measures the angle between two vectors, ignoring their magnitudes. For vectors **a** and **b**, the formula is:

```
cos(θ) = (a · b) / (‖a‖ · ‖b‖)
```

The result ranges from -1 (opposite directions) to 1 (identical directions), with 0 indicating orthogonality. For text embeddings, values above 0.85 typically signal high semantic similarity.

The key insight for efficient implementation: if both vectors are pre-normalized to unit length (‖a‖ = ‖b‖ = 1), the denominator equals 1 and cosine similarity reduces to a plain dot product:

```python
import numpy as np

a = np.array([0.6, 0.8])
b = np.array([1.0, 0.0])

# Without normalization
cos_sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# After L2 normalization, dot product gives the same result
a_norm = a / np.linalg.norm(a)
b_norm = b / np.linalg.norm(b)
dot_product = np.dot(a_norm, b_norm)  # identical to cos_sim
```

This equivalence matters practically: FAISS `IndexFlatIP` computes inner products natively. By normalizing embeddings before indexing, you get exact cosine similarity search using the IP index — no need for a dedicated cosine index type.

Cosine similarity outperforms raw Euclidean distance for text because it is invariant to vector magnitude. A short sentence and a long paragraph expressing the same idea may have very different embedding magnitudes but nearly identical directions, making cosine the correct distance metric for semantic retrieval.
