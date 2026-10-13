import streamlit as st
import requests
import base64

st.set_page_config(
    page_title="منصة DocuAudit AI",
    page_icon="⚖️",
    layout="wide"
)

BACKEND_URL = "http://127.0.0.1:8000"

st.title("⚖️ منصة تدقيق المستندات الذكية (DocuAudit AI)")
st.markdown("فحص وتدقيق بنود العقود والمستندات بدقة لحظية موثوقة مع تحليل المخاطر وعارض PDF مدمج.")

# ---------------------------------------------------------------------
# القائمة الجانبية: رفع الملف والمعالجة
# ---------------------------------------------------------------------
with st.sidebar:
    st.header("📄 رفع المستند")
    uploaded_file = st.file_uploader("اختر ملف PDF للعقد أو المستند", type=["pdf"])
    
    if uploaded_file is not None:
        # حفظ الملف في الذاكرة لعرضه مباشرة في الصفحة
        st.session_state["pdf_bytes"] = uploaded_file.getvalue()
        st.session_state["pdf_name"] = uploaded_file.name

        if st.button("بدء المعالجة والفهرسة", type="primary"):
            with st.spinner("جاري استخراج النصوص وتجهيز الفهرسة..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                try:
                    res = requests.post(f"{BACKEND_URL}/upload_and_index", files=files)
                    if res.status_code == 200:
                        data = res.json()
                        st.success(f"✅ {data['message']}")
                        st.info(f"إجمالي الكتل: {data['total_chunks']} | عدد الصفحات: {data['pages_count']}")
                        st.session_state["ready_for_audit"] = True
                    else:
                        st.error(f"خطأ: {res.json().get('detail', 'فشلت المعالجة')}")
                except Exception as e:
                    st.error(f"تعذر الاتصال بالخادم الخلفي: {e}")

# ---------------------------------------------------------------------
# تقسيم الشاشة إلى عمودين: (عارض الـ PDF) + (لوحة التدقيق والمخاطر)
# ---------------------------------------------------------------------
col_pdf, col_audit = st.columns([1, 1], gap="medium")

# --- العمود الأيمن: عارض ملف الـ PDF المدمج ---
with col_pdf:
    st.subheader("📑 عارض الوثيقة الأصلية")
    if "pdf_bytes" in st.session_state:
        # تحويل ملف الـ PDF إلى صيغة base64 لعرضه كـ iframe
        base64_pdf = base64.b64encode(st.session_state["pdf_bytes"]).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="700" type="application/pdf" style="border-radius: 8px; border: 1px solid #ddd;"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.info("قم برفع ملف PDF من القائمة الجانبية ليظهر هنا مباشرة.")

# --- العمود الأيسر: لوحة التدقيق وتحليل المخاطر ---
with col_audit:
    st.subheader("🔍 لوحة التدقيق وتحليل البنود")
    
    clause_query = st.text_input(
        "أدخل بنداً للتدقيق عنه:",
        placeholder="مثال: الشروط الجزائية، فسخ العقد، مدة التسليم..."
    )

    quick_checks = ["-- بنود جاهزة للاختيار --", "الشروط الجزائية وغرامات التأخير", "شروط إنهاء وفسخ التعاقد", "التزامات السرية وعدم الإفصاح"]
    selected_quick = st.selectbox("أو اختر فحصاً سريعاً:", quick_checks)
    if selected_quick != "-- بنود جاهزة للاختيار --":
        clause_query = selected_quick

    if st.button("🚀 فحص وتحليل البند", type="primary"):
        if not clause_query.strip():
            st.warning("يرجى كتابة نص أو اختيار بند للتدقيق.")
        elif not st.session_state.get("ready_for_audit", False):
            st.warning("يرجى الضغط على زر 'بدء المعالجة والفهرسة' في القائمة الجانبية أولاً.")
        else:
            with st.spinner("جاري مطابقة المقاطع، تقدير المخاطر، والتوثيق..."):
                try:
                    payload = {"query": clause_query, "num_results": 3}
                    resp = requests.post(f"{BACKEND_URL}/audit_clause", json=payload)
                    
                    if resp.status_code == 200:
                        results = resp.json().get("evidence", [])
                        
                        if not results:
                            st.warning("لم يتم العثور على فقرات مطابقة في المستند.")
                        else:
                            st.session_state["latest_results"] = results
                            st.session_state["last_query"] = clause_query
                    else:
                        st.error(f"خطأ أثناء التدقيق: {resp.json().get('detail')}")
                except Exception as e:
                    st.error(f"تعذر الاتصال بالخادم: {e}")

    # عرض نتائج التدقيق وتقارير المخاطر إن وجدت
    if "latest_results" in st.session_state:
        st.markdown("---")
        st.write(f"### نتائج فحص: **{st.session_state.get('last_query', '')}**")
        
        report_text = f"تقرير فحص منصة DocuAudit AI\nالبند المطلوب: {st.session_state.get('last_query')}\n\n"

        for idx, item in enumerate(st.session_state["latest_results"], start=1):
            risk = item['risk_level']
            st.markdown(f"#### 📌 دليل #{idx} — **الصفحة: {item['page']}** | درجة الخطورة: `{risk}`")
            st.info(f"**التحليل والتوصية:** {item['recommendation']}")
            
            with st.expander("عرض النص المقتبس نصياً من العقد:", expanded=True):
                st.markdown(f"> *\"{item['excerpt']}\"*")
                st.caption(f"درجة التطابق اللفظي والدلالي: {item['similarity_score'] * 100}%")

            report_text += f"دليل #{idx} (صفحة {item['page']}) - خطورة: {risk}\n"
            report_text += f"النص: {item['excerpt']}\n"
            report_text += f"التوصية: {item['recommendation']}\n"
            report_text += "-"*40 + "\n"

        # زر تحميل تقرير التدقيق
        st.download_button(
            label="📥 تحميل تقرير التدقيق (TXT)",
            data=report_text,
            file_name="Audit_Report.txt",
            mime="text/plain"
        )