import sys
sys.path.append(".")

from app.core.rag_chain import answer_question

if __name__ == "__main__":
    question = input("Sorunuzu yazın: ")
    result = answer_question(question)

    print("\n--- CEVAP ---")
    print(result["answer"])

    print("\n--- KAYNAKLAR ---")
    for src in result["sources"]:
        print(f"- {src['source_file']} (sayfa {src['page']})")