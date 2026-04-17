---
title: "Embeddings: do TF-IDF aos transformers"
source: autoral
language: pt-br
---

# Embeddings: do TF-IDF aos transformers

Embeddings são representações numéricas de texto em espaços vetoriais de alta dimensão. A ideia central é que textos semanticamente próximos devem ocupar regiões próximas nesse espaço.

A abordagem mais simples, **bag-of-words**, representa um documento como um vetor de contagem de termos. O **TF-IDF** melhora isso ponderando cada termo pela raridade no corpus: termos muito frequentes (como "de", "o") recebem peso baixo, enquanto termos discriminativos recebem peso alto. Ambos produzem vetores **esparsos** — com dezenas de milhares de dimensões, a maioria zerada — e ignoram a ordem das palavras.

O **word2vec** (2013) foi o salto para representações **densas**: cada palavra é mapeada para um vetor de 100–300 dimensões treinado para que palavras com contextos similares fiquem próximas. Ainda assim, uma mesma palavra tem um único vetor independente do contexto ("banco" financeiro vs. "banco" de praça).

Os **transformers** (BERT, 2018, e seus sucessores) resolvem a ambiguidade contextual: cada token recebe um embedding calculado em função de todos os outros tokens na sequência via atenção. Modelos de sentence-embedding como `all-MiniLM-L6-v2` produzem vetores de **384 dimensões**; modelos maiores como `text-embedding-3-large` da OpenAI usam **1536 dimensões**.

Para busca semântica, embeddings densos superam TF-IDF porque capturam sinônimos e paráfrases. Uma consulta "como declarar variáveis em Python" recupera trechos sobre `=` e `int`, mesmo sem essas palavras na query.

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")  # 384-d
vectors = model.encode(["variáveis em Python", "atribuição de valores"])
```
