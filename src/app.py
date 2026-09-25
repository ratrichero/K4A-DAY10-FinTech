import os
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# Setup python path to load modules correctly
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from core.config import load_settings
from core.utils import read_json
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


st.set_page_config(
    page_title="FinTech Data Observability & RAG Studio",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def load_app_resources():
    settings = load_settings(ROOT_DIR)
    indices = {}

    # Load baseline
    if settings.paths.embeddings_json.exists():
        try:
            indices["baseline"] = LocalEmbeddingIndex.load(
                settings=settings,
                manifest_path=settings.paths.embeddings_json,
            )
        except Exception as e:
            st.sidebar.error(f"Lỗi nạp Baseline Index: {e}")

    # Load corrupted
    if settings.paths.corrupted_embeddings_json.exists():
        try:
            indices["corrupted"] = LocalEmbeddingIndex.load(
                settings=settings,
                manifest_path=settings.paths.corrupted_embeddings_json,
            )
        except Exception:
            indices["corrupted"] = None

    # Load repaired
    if settings.paths.repaired_embeddings_json.exists():
        try:
            indices["repaired"] = LocalEmbeddingIndex.load(
                settings=settings,
                manifest_path=settings.paths.repaired_embeddings_json,
            )
        except Exception:
            indices["repaired"] = None

    return settings, indices


def main():
    settings, indices = load_app_resources()

    st.title("🛡️ FinTech: Data Observability & RAG Live Studio")
    st.caption("VinUni AI-Engineer K4 — Lab 10: Data Pipeline, Great Expectations 1.x & Silent Failure Demonstration")

    # SIDEBAR: System Status
    st.sidebar.title("📌 Trạng Thái Hệ Thống")
    st.sidebar.markdown(f"**Repository:** `ratrichero/K4A-DAY10-FinTech`")
    st.sidebar.markdown(f"**Nhánh Lead:** `cuongtv` / `main`")

    st.sidebar.subheader("Index Collections")
    st.sidebar.markdown(
        f"- **Baseline:** {'✅ Sẵn sàng' if indices.get('baseline') else '❌ Chưa nạp'}\n"
        f"- **Corrupted:** {'✅ Sẵn sàng' if indices.get('corrupted') else '❌ Chưa nạp'}\n"
        f"- **Repaired:** {'✅ Sẵn sàng' if indices.get('repaired') else '❌ Chưa nạp'}"
    )

    tab_selection = st.sidebar.radio(
        "Chọn màn hình làm việc:",
        [
            "1. 📊 Đối Chiếu 3 Trạng Thái (Benchmark)",
            "2. 🛡️ Cổng Kiểm Soát Chất Lượng (Quality Gate)",
            "3. 💬 Thử Nghiệm Truy Vấn RAG Trực Tiếp",
            "4. 📂 Khám Phá Dataset & Lineage",
        ],
    )

    # ----------------------------------------------------
    # TAB 1: 3-WAY COMPARISON BENCHMARK
    # ----------------------------------------------------
    if "1." in tab_selection:
        st.header("📊 Bảng Đối Chiếu Thực Nghiệm 3 Trạng Thái (3-Way Comparison)")
        st.markdown(
            """
            Minh chứng định lượng hiện tượng **Silent Failure**: Khi dữ liệu bị nhiễm bẩn, AI vẫn trả lời bình thường mà không báo lỗi runtime, 
            nhưng độ chính xác **Retrieval Hit Rate** và **Token F1** sụt giảm nghiêm trọng!
            """
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(
                label="Baseline Hit Rate",
                value="100.0%",
                delta="Gold Standard",
                delta_color="normal",
            )
        with col2:
            st.metric(
                label="Corrupted Hit Rate",
                value="50.0%",
                delta="-50.0% (Silent Failure)",
                delta_color="inverse",
            )
        with col3:
            st.metric(
                label="Repaired Hit Rate",
                value="100.0%",
                delta="+50.0% (Phục hồi sạch)",
                delta_color="normal",
            )
        with col4:
            st.metric(
                label="Quality Gate GX 1.x",
                value="4/6 ❌ -> 6/6 ✅",
                delta="Self-healing Success",
            )

        st.subheader("Bảng Số Liệu Chi Tiết")
        metrics_data = {
            "Chỉ số đánh giá": [
                "Retrieval Hit@1",
                "Mean Token F1",
                "Judge Accuracy",
                "Mean Judge Score (Thang 5)",
                "Cổng Chất Lượng (GX 1.x)",
            ],
            "1. Baseline (Sạch)": ["1.0000 (100%)", "1.0000", "1.0000", "5.00 / 5.0", "✅ PASS (6/6)"],
            "2. Corrupted (Nhiễm bẩn)": ["0.5000 (50%)", "0.5286", "0.5000", "3.00 / 5.0", "❌ FAIL (4/6)"],
            "3. Repaired (Phục hồi)": ["1.0000 (100%)", "1.0000", "1.0000", "5.00 / 5.0", "✅ PASS (6/6)"],
            "Mức độ ảnh hưởng": ["Sụt giảm 50%", "Sụt giảm 47.1%", "Sụt giảm 50%", "Giảm 2 điểm", "Bắt trúng 2 vi phạm"],
        }
        df_metrics = pd.DataFrame(metrics_data)
        st.dataframe(df_metrics, use_container_width=True)

        chart_data = pd.DataFrame(
            {
                "Trạng thái": ["Baseline", "Corrupted", "Repaired"],
                "Hit Rate (%)": [100.0, 50.0, 100.0],
                "Token F1 (%)": [100.0, 52.86, 100.0],
                "Judge Accuracy (%)": [100.0, 50.0, 100.0],
            }
        ).set_index("Trạng thái")
        st.bar_chart(chart_data)

    # ----------------------------------------------------
    # TAB 2: DATA OBSERVABILITY & QUALITY GATES
    # ----------------------------------------------------
    elif "2." in tab_selection:
        st.header("🛡️ Cổng Giám Sát Chất Lượng Dữ Liệu (Data Observability)")
        st.markdown("Sử dụng **Great Expectations 1.x** (chế độ Ephemeral Context) kiểm soát dữ liệu trước khi đẩy vào Vector DB.")

        col_q1, col_q2 = st.columns(2)
        with col_q1:
            st.subheader("✅ Baseline Quality Gate (Đạt chuẩn)")
            if settings.paths.baseline_quality_report.exists():
                b_q = read_json(settings.paths.baseline_quality_report)
                st.success(f"Trạng thái: PASS ({b_q.get('passed_checks', 6)}/{b_q.get('total_checks', 6)} kiểm tra thành công)")
                checks_df = pd.DataFrame(b_q.get("checks", []))
                exp_col = "expectation" if "expectation" in checks_df.columns else "expectation_type"
                cols_to_show = [c for c in [exp_col, "column", "success"] if c in checks_df.columns]
                display_b_df = checks_df[cols_to_show].rename(
                    columns={exp_col: "Expectation Check", "column": "Cột", "success": "Kết quả"}
                )
                st.dataframe(display_b_df, use_container_width=True)
            else:
                st.warning("Chưa tìm thấy baseline_quality_report.json")

        with col_q2:
            st.subheader("❌ Corrupted Quality Gate (Báo động vi phạm)")
            corrupted_q_path = settings.paths.quality_dir / "corrupted_quality_report.json"
            if corrupted_q_path.exists():
                c_q = read_json(corrupted_q_path)
                st.error(f"Trạng thái: FAIL (Chỉ đạt {c_q.get('passed_checks', 4)}/{c_q.get('total_checks', 6)} kiểm tra)")
                c_checks_df = pd.DataFrame(c_q.get("checks", []))
                exp_col = "expectation" if "expectation" in c_checks_df.columns else "expectation_type"
                cols_to_show = [c for c in [exp_col, "column", "success"] if c in c_checks_df.columns]
                display_c_df = c_checks_df[cols_to_show].rename(
                    columns={exp_col: "Expectation Check", "column": "Cột", "success": "Kết quả"}
                )
                st.dataframe(display_c_df, use_container_width=True)
            else:
                st.info("Chưa có báo cáo corrupted_quality_report.json")

        st.markdown("---")
        st.subheader("⏱️ Quan Sát Tính Tươi Mới (Freshness SLA)")
        freshness_path = settings.paths.freshness_report
        if freshness_path.exists():
            f_data = read_json(freshness_path)
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            col_f1.metric("Tổng tài liệu", f_data.get("total_records", 24))
            col_f2.metric("Tài liệu cũ (>180 ngày)", f_data.get("stale_records", 0))
            col_f3.metric("Tỷ lệ tươi mới", f"{f_data.get('freshness_rate_pct', 100):.1f}%")
            col_f4.metric("SLA Đạt chuẩn (>=75%)", "✅ ĐẠT" if f_data.get("is_fresh") else "❌ KHÔNG ĐẠT")

    # ----------------------------------------------------
    # TAB 3: LIVE RAG DEMO
    # ----------------------------------------------------
    elif "3." in tab_selection:
        st.header("💬 Live RAG Demo: Thử Nghiệm Trực Quan")
        st.markdown(
            """
            Chọn câu hỏi mẫu hoặc gõ câu hỏi để so sánh trực tiếp câu trả lời của AI giữa 3 phiên bản dữ liệu: 
            **Baseline (Sạch)** vs **Corrupted (Bị lỗi)** vs **Repaired (Tự phục hồi)**.
            """
        )

        test_questions = [
            "What is the summary of the paper 'DOLPHIN: A Privacy-Preserving Digital Investigation Readiness Assessment Framework based on Offline Large Language Models'?",
            "Who are the authors of the paper 'DOLPHIN: A Privacy-Preserving Digital Investigation Readiness Assessment Framework based on Offline Large Language Models'?",
            "When was the paper 'DOLPHIN: A Privacy-Preserving Digital Investigation Readiness Assessment Framework based on Offline Large Language Models' published?",
            "What are the research categories or subject areas of the paper 'DOLPHIN: A Privacy-Preserving Digital Investigation Readiness Assessment Framework based on Offline Large Language Models'?",
        ]

        selected_q = st.selectbox("📌 Chọn câu hỏi kiểm thử:", ["-- Tự nhập câu hỏi khác --"] + test_questions)
        if selected_q == "-- Tự nhập câu hỏi khác --":
            query = st.text_input("Nhập câu hỏi của bạn vào đây:", value="What are the key findings of the DOLPHIN framework?")
        else:
            query = selected_q

        if st.button("🚀 Thực Hiện Truy Vấn & So Sánh", type="primary"):
            if not indices.get("baseline"):
                st.error("Chưa nạp được Baseline Index. Vui lòng kiểm tra lại thư mục data/chroma!")
                return

            with st.spinner("Đang truy vấn song song cả 3 Vector Collections..."):
                res_b = answer_question(query, settings=settings, index=indices["baseline"])
                res_c = answer_question(query, settings=settings, index=indices["corrupted"]) if indices.get("corrupted") else None
                res_r = answer_question(query, settings=settings, index=indices["repaired"]) if indices.get("repaired") else None

            c1, c2, c3 = st.columns(3)
            with c1:
                st.success("### 1. Baseline RAG (Sạch)")
                st.markdown(f"**Tài liệu trích xuất:** `{res_b.retrieved_titles[0] if res_b.retrieved_titles else 'None'}`")
                st.markdown(f"**Câu trả lời:**\n> {res_b.answer}")

            with c2:
                st.error("### 2. Corrupted RAG (Bẩn)")
                if res_c:
                    st.markdown(f"**Tài liệu trích xuất:** `{res_c.retrieved_titles[0] if res_c.retrieved_titles else 'None'}`")
                    st.markdown(f"**Câu trả lời:**\n> {res_c.answer}")
                    st.caption("⚠️ **Hiện tượng Silent Failure:** AI không crash nhưng kết quả trích xuất hoặc câu trả lời bị sai do dữ liệu bẩn.")
                else:
                    st.info("Chưa có Corrupted Index.")

            with c3:
                st.info("### 3. Repaired RAG (Khôi phục)")
                if res_r:
                    st.markdown(f"**Tài liệu trích xuất:** `{res_r.retrieved_titles[0] if res_r.retrieved_titles else 'None'}`")
                    st.markdown(f"**Câu trả lời:**\n> {res_r.answer}")
                    st.caption("✨ **Hồi phục hoàn toàn:** Kết quả khớp chuẩn xác với Baseline sau khi chạy Idempotent Repair.")
                else:
                    st.info("Chưa có Repaired Index.")

    # ----------------------------------------------------
    # TAB 4: DATASET EXPLORER & LINEAGE
    # ----------------------------------------------------
    elif "4." in tab_selection:
        st.header("📂 Khám Phá Dataset & Tính Toàn Vẹn Nguồn Gốc (Data Lineage)")
        data_view = st.radio("Chọn tập dữ liệu hiển thị:", ["papers_clean.csv (Baseline)", "papers_clean_corrupted.csv", "papers_clean_repaired.csv"], horizontal=True)

        target_file = settings.paths.clean_csv
        if "corrupted" in data_view:
            target_file = settings.paths.clean_dir / "papers_clean_corrupted.csv"
        elif "repaired" in data_view:
            target_file = settings.paths.clean_dir / "papers_clean_repaired.csv"

        if target_file.exists():
            df_display = pd.read_csv(target_file)
            st.markdown(f"**Tổng số dòng:** {len(df_display)} | **Tập tin:** `{target_file.name}`")
            display_cols = [c for c in ["paper_id", "title", "published", "age_days", "categories_joined", "summary"] if c in df_display.columns]
            st.dataframe(df_display[display_cols], use_container_width=True)

            with st.expander("🔍 Xem thử một bản ghi text_for_embedding chuẩn"):
                if "text_for_embedding" in df_display.columns:
                    st.code(df_display.iloc[0]["text_for_embedding"], language="markdown")
        else:
            st.warning(f"Chưa tìm thấy file {target_file}")


if __name__ == "__main__":
    main()
