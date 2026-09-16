# Streamlit girişi: ortak PDF/FAISS + kullanıcı başına ayrı sohbet oturumu.
from pathlib import Path
import os

import streamlit as st
import streamlit.components.v1 as components

from engine import Session, DocumentStore, SharedKnowledgeBase
from frontend import component_directory

ROOT = Path(__file__).resolve().parent
# Üç dosya birlikte güncellenmelidir: yeni runtime fark protokolü eski JS ile karıştırılmamalı.
# Şema anahtarı, hot-reload sırasında eski Session/component nesnesinin tekrar kullanılmasını önler.
SESSION_SCHEMA_VERSION = "2026-09-16-inline-citations-v8"


@st.cache_resource
def component_definition(schema_version):
    return components.declare_component("research_studio", path=component_directory())


@st.cache_resource
def document_store(schema_version):
    return DocumentStore(os.getenv("RESEARCH_DATA_DIR", str(ROOT / "saved_documents")))


def api_key():
    try:
        key = str(st.secrets.get("OPENAI_API_KEY", ""))
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        key = ""
    return key or os.getenv("OPENAI_API_KEY", "")


@st.cache_resource
def shared_knowledge_base(schema_version):
    # Bu nesne process boyunca TEK'tir: bütün kullanıcılar aynı PDF/FAISS indeksine bağlanır.
    return SharedKnowledgeBase(
        api_key=api_key(),
        store=document_store(schema_version),
        default_pdf=os.getenv("DEFAULT_PDF_PATH", str(ROOT / "default.pdf")),
    )


def receive_command():
    # Her browser kendi Session'ına komut yollar; Session yalnız chat state'ini taşır.
    command = st.session_state.get("research-studio")
    if command:
        st.session_state.research_session.dispatch(command)


# Fragment bütün uygulamayı değil bu bileşeni yoklar. Asıl hesaplama Session işçilerindedir.
# [D48] 250 ms (4 Hz) metni iri sıçramalarla gösteriyordu. 100 ms'de küçük
# fark paketleri alınır; değişiklik yoksa motor yalnız heartbeat üretir.
@st.fragment(run_every=0.1)
def studio():
    # OPTİMİZASYON: yalnız bu fragment yenilenir; PDF/model yükleme cache'tedir.
    # Hazır sunucu durumunun tarayıcıya ulaşması bu yoklama aralığını da bekleyebilir.
    session = st.session_state.research_session
    component_definition(SESSION_SCHEMA_VERSION)(
        snapshot=session.snapshot(incremental=True),
        key="research-studio",
        default=None,
        on_change=receive_command,
    )


def main():
    st.set_page_config(
        page_title="Akıllı Asistan",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """
        <style>
        html,body,[data-testid="stAppViewContainer"],.stApp{margin:0;padding:0;background:#fafbfc}
        [data-testid="stHeader"],[data-testid="stToolbar"],#MainMenu,footer{display:none}
        .stMainBlockContainer,.block-container{max-width:none;padding:0!important}
        [data-testid="stVerticalBlock"]{gap:0}
        iframe[title*="research_studio"]{display:block;width:100%;border:0}
        /* DÜZELTME [D34]: Streamlit rerun sırasında eski elementin opacity'sini düşürür.
           Bu element bütün sohbet iframe'ini içerdiği için tüm ekran soluyordu.
           Yalnız bu bileşeni görünür tut; diğer Streamlit elementlerini etkileme.
           Gerçek bekleme, iframe içindeki Gönderiliyor/Aranıyor durumuyla gösterilir. */
        [data-testid="stElementContainer"]:has(iframe[title*="research_studio"]){opacity:1!important;transition:none!important}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Kod/hot-reload sonrasında eski Session sınıfı canlı kalmasın.
    if st.session_state.get("_research_session_version") != SESSION_SCHEMA_VERSION:
        old = st.session_state.pop("research_session", None)
        if old is not None:
            try:
                old.close()
            except Exception:
                pass
        st.session_state["_research_session_version"] = SESSION_SCHEMA_VERSION

    # Session kullanıcıya özeldir; knowledge base ise st.cache_resource ile globaldir.
    if "research_session" not in st.session_state:
        st.session_state.research_session = Session(shared_knowledge_base(SESSION_SCHEMA_VERSION))

    studio()


if __name__ == "__main__":
    # `python app.py` ile çalıştırıldığında kendisini Streamlit CLI olarak açar.
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    if get_script_run_ctx(suppress_warning=True) is None:
        import sys
        from streamlit.web import cli

        sys.argv = [
            "streamlit",
            "run",
            "--server.headless=false",
            "--server.address=0.0.0.0",
            "--browser.gatherUsageStats=false",
            "--runner.postScriptGC=false",
            str(Path(__file__).resolve()),
            *sys.argv[1:],
        ]
        raise SystemExit(cli.main())

    main()
