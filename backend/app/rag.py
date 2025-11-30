from .qdrant_client import get_qdrant_client
from openai import OpenAI
import os

TOP_K = int(os.getenv("RAG_TOP_K", 5))
client_openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def query_and_build_context(query_embedding, collection_name="site_collection"):
    client_qdrant = get_qdrant_client()

    res = client_qdrant.search(
        collection_name=collection_name,
        query_vector=query_embedding,
        limit=TOP_K
    )

    snippets = []
    for r in res:
        # qdrant-client 1.x returns ScoredPoint objects with .payload and .score
        payload = r.payload if hasattr(r, 'payload') else r.get('payload', {})
        score = r.score if hasattr(r, 'score') else r.get('score')
        
        snippets.append(
            {
                "text": payload.get("text") if isinstance(payload, dict) else payload,
                "url": payload.get("url") if isinstance(payload, dict) else "",
                "score": score
            }
        )

    return snippets


def call_llm_with_context(user_question: str, context_snippets: list):
    prompt_parts = ["Ты ассистент сайта. Используй только предоставленные данные:"]
    for s in context_snippets:
        prompt_parts.append("---")
        prompt_parts.append(s["text"])
    prompt_parts.append(f"---\nВопрос: {user_question}")

    prompt = "\n".join(prompt_parts)

    response = client_openai.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "Ты — helpful AI ассистент сайта."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    answer = response.choices[0].message.content

    return {
        "answer": answer,
        "prompt_used": prompt
    }
