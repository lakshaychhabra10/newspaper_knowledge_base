Newspaper Knowledge Base (RAG Project)

Initialization

To synchronize your project , you need to run the following command in terminal :
uv sync

this will install the necessary dependencies

then you to need to have docker installed 

run the following command in docker :

docker run --name pgvector-container -e POSTGRES_USER=langchain -e POSTGRES_PASSWORD=langchain -e POSTGRES_DB=langchain -p 6024:5432 -d pgvector/pgvector:pg16

this will get your database started and the connection string will look like this

connection_string - postgresql+psycopg://langchain:langchain@localhost:6024/langchain

.env has the necesary credentials, these are :
- OPENAI_API_KEY : this is your open ai api key 
- DATABASE_CONNECTION : this is postgres connection string in the following format - postgresql+psycopg://username:password@host:port/database_name
- COLLECTION_NAME=newspaper_articles : this is the collection name of the place where all the vectors will be stored (prefer to keep it "newspaper_articles" only)


Time to downlaod your docs

2 ways to download :

(there are some sample files in the data folder available to test)

1. Manual Data Folder Updation - You may use @data_loader.py to OCR the pdfs using the argument --manual
2. Telegram auto download - downloads and auto OCRs, use the argument --telegram , use --limit 10 to limit the number of files to OCR


Time to Index the documents 

run index.py to index the documents - this will auto skip the docs already indexed (based on the "source" metadata ) and only index the new docs


Time to run the streamlit app
Use the following command in the terminal to run the dashboard
uv run streamlit run app.py

this will host the app on http://localhost:8501

you can type this url in the browser to test

happy testing!

