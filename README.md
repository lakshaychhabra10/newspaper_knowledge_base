# Newspaper Knowledge Base (RAG Project)

- **Project Info** : We indexed Economic Times Newspaper content and then the user can ask questions over it. This is based on multi vector retrieval process.
- **Process** : Information is indexed in chunks ( suing Recursive Text Splitter ) and then the chunks are indexed in a vector database, then query retrieves n similar documents / chunks to the query and then the retrieved information is passed to the LLM for the answer
- **Drawbacks** : there is no memory, cannot chat back and forth
- **Improvements** : To add Query Transformation, enhancing the query in the initial stage itself

---

## Initialization

To synchronize your project , you need to run the following command in terminal :

```bash
uv sync
```

this will install the necessary dependencies

then you to need to have docker installed

run the following command in docker :

```bash
docker run --name pgvector-container -e POSTGRES_USER=langchain -e POSTGRES_PASSWORD=langchain -e POSTGRES_DB=langchain -p 6024:5432 -d pgvector/pgvector:pg16
```

this will get your database started and the connection string will look like this

```
connection_string - postgresql+psycopg://langchain:langchain@localhost:6024/langchain
```

`.env` has the necesary credentials, these are :

- **OPENAI_API_KEY** : this is your open ai api key
- **DATABASE_CONNECTION** : this is postgres connection string in the following format - postgresql+psycopg://username:password@host:port/database_name
- **COLLECTION_NAME=newspaper_articles** : this is the collection name of the place where all the vectors will be stored (prefer to keep it "newspaper_articles" only)
- **TELEGRAM_API_ID / TELEGRAM_API_HASH** : from https://my.telegram.org (telegram mode only)
- **TELEGRAM_PHONE** : your phone number with country code, for first-time login (telegram mode only)
- **TELEGRAM_GROUP** : group username, invite link, or chat id (telegram mode only)
- **TELEGRAM_FILE_PREFIX** : defaults to "ET Delhi" (telegram mode only)

---

## Time to downlaod your docs

2 ways to download :

(there are some sample files in the data folder available to test)

1. **Manual Data Folder Updation** - You may use data_loader.py to OCR the pdfs using the argument --manual
   - `uv run python data_loader.py --manual`
2. **Telegram auto download** - downloads and auto OCRs, use the argument --telegram , use --limit 10 to limit the number of files to OCR
   - `uv run python data_loader.py --telegram --limit 10`

---

## Time to Index the documents

run index.py to index the documents - this will auto skip the docs already indexed (based on the "source" metadata ) and only index the new docs

use the following terminal command for this :

```bash
uv run index.py
```

---

## Time to run the streamlit app

Use the following command in the terminal to run the dashboard

```bash
uv run streamlit run app.py
```

this will host the app on http://localhost:8501

you can type this url in the browser to test

happy testing!
