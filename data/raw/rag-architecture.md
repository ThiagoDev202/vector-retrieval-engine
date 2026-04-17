---
title: Arquitetura básica de RAG
source: autoral
language: pt-br
---

# Arquitetura básica de RAG

Retrieval-Augmented Generation (RAG) é um padrão arquitetural que conecta um modelo de linguagem a uma base de conhecimento externa, reduzindo alucinações ao fornecer contexto factual recuperado dinamicamente antes da geração da resposta.

O pipeline tem quatro componentes principais:

1. **Embedder**: converte a pergunta do usuário em um vetor denso usando um bi-encoder (ex.: `sentence-transformers`).
2. **Vector store**: índice vetorial (ex.: FAISS, Chroma, Qdrant) que armazena os embeddings do corpus de documentos.
3. **Retriever**: executa a busca por similaridade entre o vetor da pergunta e os vetores do corpus, retornando os `k` trechos mais relevantes.
4. **LLM**: recebe a pergunta original concatenada com os trechos recuperados no prompt e gera a resposta final.

```
Pergunta → Embedder → Vector Store → Top-k trechos
                                           ↓
                              Prompt = pergunta + trechos → LLM → Resposta
```

RAG reduz alucinações porque o LLM não precisa "lembrar" fatos do treinamento — as informações são fornecidas explicitamente no contexto. O limite é a qualidade do retriever: se os trechos recuperados forem irrelevantes, o LLM ainda pode errar.

Para melhorar a precisão após o retrieval, um **re-ranker** (cross-encoder) pontua cada par (pergunta, trecho) individualmente e reordena os candidatos antes de enviá-los ao LLM. Cross-encoders são mais lentos que bi-encoders, por isso se aplicam apenas ao conjunto já filtrado (tipicamente os 20–50 melhores candidatos, que são reduzidos a 3–5 após o re-ranking).
