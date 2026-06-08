import gradio as gr
from dotenv import load_dotenv
from pro_implementation.answer import answer_question

load_dotenv(override=True)


def chat(message: str, history: list) -> str:
    # history is a list of {"role": ..., "content": ...} dicts from gr.ChatInterface
    answer, _ = answer_question(message, history)
    return answer


if __name__ == "__main__":
    gr.ChatInterface(
        fn=chat,
        title="Radixweb Expert Assistant — PRO",
        description="Hybrid RAG · BM25 + Semantic · Local Reranker",
    ).launch()
