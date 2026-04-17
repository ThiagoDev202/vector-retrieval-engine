---
title: FAISS IndexFlatIP vs IVF and HNSW
source: autoral
language: en
---

# FAISS IndexFlatIP vs IVF and HNSW

FAISS (Facebook AI Similarity Search) provides several index types with different trade-offs between search accuracy, memory usage, and query latency.

`IndexFlatIP` performs exact inner-product search by scanning every vector in the index. When vectors are L2-normalized beforehand, inner product equals cosine similarity, making this the reference implementation for semantic search correctness. It scales poorly beyond a few hundred thousand vectors because query time grows linearly with corpus size.

`IndexIVFPQ` (Inverted File with Product Quantization) addresses scale by first clustering vectors into `nlist` Voronoi cells and compressing each vector using product quantization. At query time, only `nprobe` cells are searched — typically 8–64 out of a total of 256–4096. This reduces memory by 4–32x and cuts latency significantly, at the cost of approximate results (recall around 90–98% depending on `nprobe`).

HNSW (Hierarchical Navigable Small World) builds a multi-layer proximity graph. Queries navigate the graph greedily from coarse to fine layers, achieving sub-millisecond latency at recall rates above 95% without requiring a training step. The trade-off is higher memory consumption: each node stores `M` (typically 16–32) neighbor links.

```python
import faiss, numpy as np

d = 384  # embedding dimension
index = faiss.IndexFlatIP(d)
vectors = np.random.rand(10_000, d).astype("float32")
faiss.normalize_L2(vectors)
index.add(vectors)
D, I = index.search(vectors[:1], k=5)
```

Choose `IndexFlatIP` for correctness during development; switch to IVF or HNSW for production at scale.
