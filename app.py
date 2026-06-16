from datetime import datetime
import os
from dotenv import load_dotenv
import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from sqlalchemy import create_engine, text

load_dotenv()

CONNECTION = os.getenv("DATABASE_CONNECTION")
COLLECTION = os.getenv("COLLECTION_NAME")
DATE_FORMAT = "%d-%m-%Y"

prompt = ChatPromptTemplate.from_template("""
Answer the question based only on the context below.
If the context doesn't contain enough information, say you don't know.

Question: {question}

Context:
{context}
""")


@st.cache_data(ttl=300)
def get_available_dates() -> list[str]:
    engine = create_engine(CONNECTION)
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT DISTINCT e.cmetadata->>'date' AS date
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = :collection
                  AND e.cmetadata->>'date' IS NOT NULL
            """),
            {"collection": COLLECTION},
        )
        dates = [row[0] for row in rows if row[0]]
    return sorted(dates, key=lambda d: datetime.strptime(d, DATE_FORMAT))


def build_date_filter(
    filter_mode: str,
    filter_dates: tuple[str, ...],
    available_dates: list[str],
) -> dict | None:
    if filter_mode == "All dates" or not filter_dates:
        return None

    if filter_mode == "On these dates":
        matching = list(filter_dates)
    elif filter_mode == "After this date":
        ref = datetime.strptime(filter_dates[0], DATE_FORMAT)
        matching = [
            d for d in available_dates if datetime.strptime(d, DATE_FORMAT) > ref
        ]
    elif filter_mode == "Before this date":
        ref = datetime.strptime(filter_dates[0], DATE_FORMAT)
        matching = [
            d for d in available_dates if datetime.strptime(d, DATE_FORMAT) < ref
        ]
    else:
        return None

    if not matching:
        return {"date": {"$in": []}}

    if len(matching) == 1:
        return {"date": matching[0]}
    return {"date": {"$in": matching}}


def format_docs(docs):
    parts = []
    for doc in docs:
        meta = doc.metadata
        header = f"[{meta.get('newspaper', 'Unknown')} | {meta.get('date', 'Unknown')}]"
        parts.append(f"{header}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


@st.cache_resource
def get_rag_chain(k: int, filter_mode: str, filter_dates: tuple[str, ...]):
    embeddings = OpenAIEmbeddings()
    db = PGVector(
        embeddings=embeddings,
        connection=CONNECTION,
        collection_name=COLLECTION,
    )
    available_dates = get_available_dates()
    metadata_filter = build_date_filter(filter_mode, filter_dates, available_dates)

    search_kwargs = {"k": k}
    if metadata_filter:
        search_kwargs["filter"] = metadata_filter
    retriever = db.as_retriever(search_kwargs=search_kwargs)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def rag_answer(question: str):
        docs = retriever.invoke(question)
        answer = (prompt | llm | StrOutputParser()).invoke({
            "question": question,
            "context": format_docs(docs),
        })
        return answer, docs

    return rag_answer


# --- UI ---
st.set_page_config(page_title="Newspaper Knowledge Base", page_icon="📰", layout="centered")
st.title("📰 Newspaper Q&A")
st.caption("Ask questions about Economic Times articles in your knowledge base.")

k = st.sidebar.slider("Chunks to retrieve (k)", min_value=2, max_value=12, value=6)
show_sources = st.sidebar.checkbox("Show sources", value=True)

available_dates = get_available_dates()
filter_mode = st.sidebar.radio(
    "Date filter",
    ["All dates", "On these dates", "After this date", "Before this date"],
)

if not available_dates:
    st.sidebar.warning("No dates found in the database.")
    filter_dates: tuple[str, ...] = ()
elif filter_mode == "On these dates":
    filter_dates = tuple(
        st.sidebar.multiselect("Select dates", options=available_dates)
    )
elif filter_mode in ("After this date", "Before this date"):
    filter_dates = (st.sidebar.selectbox("Date", options=available_dates),)
else:
    filter_dates = ()

if filter_mode != "All dates" and not filter_dates:
    st.sidebar.info("Select at least one date to apply the filter.")

question = st.text_input("Your question", placeholder="What is the outlook on gold prices?")

if st.button("Ask", type="primary") and question.strip():
    if filter_mode != "All dates" and not filter_dates:
        st.warning("Choose a date filter before asking a question.")
    else:
        with st.spinner("Searching and generating answer..."):
            rag_answer = get_rag_chain(k=k, filter_mode=filter_mode, filter_dates=filter_dates)
            answer, docs = rag_answer(question.strip())

        st.subheader("Answer")
        st.write(answer)

        if show_sources:
            st.subheader("Sources")
            if not docs:
                st.info("No matching sources found for the selected date filter.")
            for i, doc in enumerate(docs, 1):
                with st.expander(
                    f"{i}. {doc.metadata.get('date')} — {doc.metadata.get('source', 'unknown')}"
                ):
                    st.write(doc.page_content)
