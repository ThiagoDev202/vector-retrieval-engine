---
title: Text chunking strategies for retrieval
source: autoral
language: en
---

# Text chunking strategies for retrieval

Chunking is how you split a large document into pieces before embedding and indexing. The choice of strategy directly affects recall (did we retrieve the relevant passage?) and precision (is the retrieved passage focused enough to be useful?).

**Fixed-size chunking** splits by a constant token count, typically 256–512 tokens. It is fast and deterministic but can cut sentences mid-way, injecting noise into the embedding. Adding an overlap — say, 10–20% of the chunk size — carries context across boundaries:

```python
def fixed_chunks(text: str, size: int = 400, overlap: int = 80) -> list[str]:
    tokens = text.split()
    step = size - overlap
    return [" ".join(tokens[i : i + size]) for i in range(0, len(tokens), step)]
```

**Sentence-based chunking** groups complete sentences up to a token budget using a tokenizer such as `tiktoken`. This respects linguistic boundaries but can produce variable-length chunks, making batch embedding slightly less efficient.

**Semantic chunking** embeds each sentence, then merges consecutive sentences whose cosine similarity exceeds a threshold. The result is topic-coherent chunks, but it requires a first-pass embedding over the entire document — roughly 2-3x the compute cost. For most RAG pipelines the trade-off is worthwhile when the corpus contains long, topic-switching documents.

A practical rule of thumb: start with 512-token chunks and 10% overlap, measure recall@5 on a held-out question set, then tune chunk size. Smaller chunks (128 tokens) improve precision at the cost of recall; larger ones (1024 tokens) do the opposite.
