from .qdrant_client import get_qdrant_client
from openai import OpenAI
import os

TOP_K = int(os.getenv("RAG_TOP_K", 3))

# DeepSeek API client for LLM
client_llm = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)


def query_and_build_context(query_embedding, collection_name="site_collection"):
    client_qdrant = get_qdrant_client()

    # Use query_points for qdrant-client 1.x
    try:
        res = client_qdrant.query_points(
            collection_name=collection_name,
            query=query_embedding,
            limit=TOP_K
        ).points
    except Exception as e:
        print(f"Search failed: {e}")
        return []

    snippets = []
    if res:
        for r in res:
            # qdrant-client 1.x returns ScoredPoint objects with .payload and .score
            payload = r.payload if hasattr(r, 'payload') else r.get('payload', {})
            score = r.score if hasattr(r, 'score') else r.get('score')
            
            snippets.append(
                {
                    "text": payload.get("text") if isinstance(payload, dict) else str(payload),
                    "url": payload.get("url") if isinstance(payload, dict) else "",
                    "score": score
                }
            )

    return snippets


def call_llm_with_context(user_question: str, context_snippets: list):
    prompt_parts = ["You are a website assistant. Use only the provided context:"]
    for s in context_snippets:
        prompt_parts.append("---")
        prompt_parts.append(s["text"])
    prompt_parts.append(f"---\nQuestion: {user_question}")

    prompt = "\n".join(prompt_parts)

    response = client_llm.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful website assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    answer = response.choices[0].message.content

    return {"answer": answer}
