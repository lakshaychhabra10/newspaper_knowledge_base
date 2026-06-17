"""Index newspaper .txt files into PGVector."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_classic.indexes import SQLRecordManager, index
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine, text

load_dotenv()

DATA_DIR = Path("data")
CONNECTION = os.getenv("DATABASE_CONNECTION", "postgresql+psycopg://langchain:langchain@localhost:6024/langchain")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "newspaper_articles")
NAMESPACE = "newspaper_articles_namespace"


def date_from_path(path: Path) -> str:
    return path.stem.rsplit("_", 1)[-1]


def source_key(source: str) -> str:
    return str(Path(source).with_suffix(""))


def load_documents() -> list[Document]:
    return [
        Document(
            page_content=path.read_text(encoding="utf-8"),
            metadata={
                "date": date_from_path(path),
                "source": str(path),
                "newspaper": "Economic Times",
            },
        )
        for path in sorted(DATA_DIR.glob("*.txt"))
    ]


def get_indexed_sources(connection: str, collection: str) -> set[str]:
    engine = create_engine(connection)
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT DISTINCT e.cmetadata->>'source' AS source
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = :collection
                  AND e.cmetadata->>'source' IS NOT NULL
            """),
            {"collection": collection},
        )
        raw_sources = [row[0] for row in rows if row[0]]
    return {source_key(s) for s in raw_sources}


def main() -> None:
    docs = load_documents()
    if not docs:
        print("No .txt files found in data/")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splitted_documents = splitter.split_documents(docs)

    indexed_keys = get_indexed_sources(CONNECTION, COLLECTION_NAME)
    new_docs = [
        d for d in splitted_documents
        if source_key(d.metadata["source"]) not in indexed_keys
    ]

    print(f"Total chunks: {len(splitted_documents)}, new: {len(new_docs)}")

    if not new_docs:
        print("Nothing new to index.")
        return

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    vector_store = PGVector(
        connection=CONNECTION,
        collection_name=COLLECTION_NAME,
        embeddings=embeddings,
        use_jsonb=True,
    )
    record_manager = SQLRecordManager(namespace=NAMESPACE, db_url=CONNECTION)
    record_manager.create_schema()

    result = index(
        new_docs,
        record_manager,
        vector_store,
        cleanup="incremental",
        source_id_key="source",
    )
    print(result)


if __name__ == "__main__":
    main()