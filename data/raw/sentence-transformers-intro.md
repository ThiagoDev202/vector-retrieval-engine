---
title: sentence-transformers em 5 minutos
source: autoral
language: pt-br
---

# sentence-transformers em 5 minutos

A biblioteca `sentence-transformers` implementa bi-encoders: modelos que transformam uma frase em um vetor denso de dimensão fixa, de forma que frases semanticamente próximas fiquem próximas no espaço vetorial. Isso é diferente de cross-encoders, que comparam dois textos juntos e são mais precisos, porém muito mais lentos para buscas em larga escala.

O ponto de entrada é `SentenceTransformer.encode()`:

```python
from sentence_transformers import SentenceTransformer

modelo = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
embeddings = modelo.encode(["Como instalar Python?", "Python installation guide"])
print(embeddings.shape)  # (2, 384)
```

O modelo `paraphrase-multilingual-MiniLM-L12-v2` produz vetores de 384 dimensões e suporta mais de 50 idiomas, incluindo português. Para projetos exclusivamente em inglês, `all-MiniLM-L6-v2` é mais rápido com qualidade similar. Modelos maiores como `all-mpnet-base-v2` geram vetores de 768 dimensões com melhor recall, mas triplicam o custo de inferência.

Antes de indexar em um armazenamento vetorial, normalize os embeddings para norma L2. Isso permite usar similaridade de produto interno (mais eficiente computacionalmente) no lugar de similaridade de cosseno:

```python
from sentence_transformers.util import normalize_embeddings
embeddings = normalize_embeddings(embeddings)
```

A normalização é um passo frequentemente esquecido que causa resultados incorretos em índices como `IndexFlatIP` do FAISS.
