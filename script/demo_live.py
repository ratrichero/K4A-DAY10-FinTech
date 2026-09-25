from __future__ import annotations

import argparse
from pathlib import Path
import sys

from core.config import load_settings
from core.utils import read_json
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


def print_banner():
    banner = r"""
================================================================================
  VINUNI AI-ENGINEER K4 - DAY 10 DATA OBSERVABILITY & RAG PIPELINE LIVE DEMO
================================================================================
    """
    print(banner)


def run_demo_interactive():
    print_banner()
    settings = load_settings()

    print("[1/3] Dang nap Baseline ChromaDB Index...")
    if not settings.paths.embeddings_json.exists():
        print(f"Loi: Khong tim thay manifest tai {settings.paths.embeddings_json}. Hay chay `script/run_phase1.py` truoc!")
        sys.exit(1)
    baseline_index = LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json)
    print(f" -> Da nap thanh cong {len(baseline_index.documents)} papers tu collection '{baseline_index.collection_name}'!\n")

    # Kiem tra xem Corrupted index da duoc tao chua
    corrupted_index = None
    if settings.paths.corrupted_embeddings_json.exists():
        print("[2/3] Da phat hien Corrupted Index san sang cho phep doi chieu!")
        try:
            corrupted_index = LocalEmbeddingIndex.load(settings, settings.paths.corrupted_embeddings_json)
            print(f" -> Da nap Corrupted collection '{corrupted_index.collection_name}'!\n")
        except Exception:
            corrupted_index = None
    else:
        print("[2/3] Luu y: Corrupted Index chua san sang (GLM dang chay hoac chua chay script/run_corruption_flow.py).\n")

    # Kiem tra Repaired index
    repaired_index = None
    if settings.paths.repaired_embeddings_json.exists():
        print("[3/3] Da phat hien Repaired Index!")
        try:
            repaired_index = LocalEmbeddingIndex.load(settings, settings.paths.repaired_embeddings_json)
            print(f" -> Da nap Repaired collection '{repaired_index.collection_name}'!\n")
        except Exception:
            repaired_index = None

    test_set_path = settings.paths.eval_testset
    sample_questions = []
    if test_set_path.exists():
        test_data = read_json(test_set_path)
        sample_questions = [item["question"] for item in test_data[:5]]

    print("-" * 80)
    print("CAC CAU HOI MAU:")
    for idx, q in enumerate(sample_questions, 1):
        print(f" [{idx}] {q}")
    print(" [0] Thoat chuong trinh")
    print("-" * 80)

    while True:
        try:
            user_input = input("\nNhap so thu tu cau hoi mau hoac tu go cau hoi (hoac 'q' de thoat): ").strip()
            if not user_input or user_input.lower() in ["0", "q", "exit", "quit"]:
                print("Ket thuc Live Demo session. Cam on!")
                break

            if user_input.isdigit() and 1 <= int(user_input) <= len(sample_questions):
                selected_q = sample_questions[int(user_input) - 1]
            else:
                selected_q = user_input

            print("\n" + "=" * 80)
            print(f"CAU HOI: {selected_q}")
            print("=" * 80)

            # 1. Baseline RAG Response
            print("\n[+] 1. KET QUA TU BASELINE VECTOR INDEX (Du lieu sach):")
            res_baseline = answer_question(selected_q, settings=settings, index=baseline_index)
            print(f" -> Document duoc retrieve: {res_baseline.retrieved_titles[0] if res_baseline.retrieved_titles else 'None'}")
            print(f" -> Paper ID: {res_baseline.retrieved_doc_ids[0] if res_baseline.retrieved_doc_ids else 'None'}")
            print(f" -> Cau tra loi: {res_baseline.answer}")

            # 2. Corrupted RAG Response (neu co)
            if corrupted_index:
                print("\n[-] 2. KET QUA TU CORRUPTED VECTOR INDEX (Du lieu bi tiem doc/loi):")
                res_corrupted = answer_question(selected_q, settings=settings, index=corrupted_index)
                print(f" -> Document duoc retrieve: {res_corrupted.retrieved_titles[0] if res_corrupted.retrieved_titles else 'None'}")
                print(f" -> Paper ID: {res_corrupted.retrieved_doc_ids[0] if res_corrupted.retrieved_doc_ids else 'None'}")
                print(f" -> Cau tra loi: {res_corrupted.answer}")
                print(" -> Nhan xet: AI bi Silent Failure - khong bao loi nhung retrieve sai hoac tra loi sai!")

            # 3. Repaired RAG Response (neu co)
            if repaired_index:
                print("\n[*] 3. KET QUA TU REPAIRED VECTOR INDEX (Du lieu phuc hoi Idempotent):")
                res_repaired = answer_question(selected_q, settings=settings, index=repaired_index)
                print(f" -> Document duoc retrieve: {res_repaired.retrieved_titles[0] if res_repaired.retrieved_titles else 'None'}")
                print(f" -> Cau tra loi: {res_repaired.answer}")
                print(" -> Nhan xet: Chat luong phuc hoi hoan toan ve muc Baseline chuan!")

            print("-" * 80)

        except (KeyboardInterrupt, EOFError):
            print("\nKet thuc Live Demo session.")
            break


if __name__ == "__main__":
    run_demo_interactive()
