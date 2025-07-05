# RAG module for EconomIAssist using LangChain and Chroma
#
# This module provides functions to load, chunk, embed, and query documents from the data folder using a vector database (ChromaDB).
#
# Usage:
#   1. Run this script to build the vector store from data PDFs.
#   2. Use the `query_rag` function to retrieve contextually relevant information for a user query.

import os
import time
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import AzureOpenAIEmbeddings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATA_PATH = os.path.join(os.path.dirname(__file__), '../../data')
CHROMA_PATH = os.path.join(os.path.dirname(__file__), '../../chroma_db')

# Azure OpenAI configuration
def get_azure_embeddings():
    return AzureOpenAIEmbeddings(
        azure_deployment="text-embedding-ada-002",  # or your specific deployment name
        openai_api_version="2023-05-15",
        azure_endpoint="https://ocorb-maec0nzf-eastus2.openai.azure.com/",
        api_key=os.getenv("AZURE_OPENAI_EMBEDDINGS_API_KEY")
    )

# 1. Load PDF documents from EcoData
def load_documents():
    pdf_files = [os.path.join(DATA_PATH, f) for f in os.listdir(DATA_PATH) if f.endswith('.pdf')]
    documents = []
    for pdf in pdf_files:
        loader = PyPDFLoader(pdf)
        documents.extend(loader.load())
    return documents

# 2. Split documents into chunks
def split_documents(documents, chunk_size=1000, chunk_overlap=200):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(documents)

# 3. Build and persist Chroma vector store with batching and resume capability
def build_vector_store(resume=True):
    documents = load_documents()
    chunks = split_documents(documents)
    
    print(f"Total chunks to process: {len(chunks)}")
    
    # Debug: Print the first 5 chunks to check text extraction
    print("First few chunks after splitting:")
    for i, chunk in enumerate(chunks[:5]):
        print(f"Chunk {i+1}: {repr(chunk.page_content[:200])}")
    
    # Check if vector store already exists and resume is enabled
    start_batch = 0
    vectordb = None
    batch_size = 400
    
    if resume and os.path.exists(CHROMA_PATH):
        try:
            embeddings = get_azure_embeddings()
            vectordb = Chroma(
                persist_directory=CHROMA_PATH,
                embedding_function=embeddings
            )
            existing_count = vectordb._collection.count()
            print(f"Found existing vector store with {existing_count} documents")
            
            # Estimate which batch to start from (approximate)
            start_batch = (existing_count // batch_size) * batch_size
            print(f"Resuming from approximately batch {start_batch//batch_size + 1}")
        except Exception as e:
            print(f"Could not resume from existing vector store: {e}")
            print("Starting fresh...")
            import shutil
            shutil.rmtree(CHROMA_PATH)
            start_batch = 0
    else:
        if os.path.exists(CHROMA_PATH):
            import shutil
            shutil.rmtree(CHROMA_PATH)
    
    # Use Azure OpenAI embeddings
    embeddings = get_azure_embeddings()
    
    print("\n\nProcessing documents in batches to avoid rate limits...")
    
    for i in range(start_batch, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = i//batch_size + 1
        total_batches = (len(chunks) + batch_size - 1)//batch_size
        
        print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} chunks) - Progress: {(i/len(chunks)*100):.1f}%")
        
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                if i == 0 and vectordb is None:
                    # Create the initial vector store with the first batch
                    vectordb = Chroma.from_documents(
                        batch,
                        embeddings,
                        persist_directory=CHROMA_PATH
                    )
                else:
                    # Add subsequent batches to the existing vector store
                    if vectordb is None:
                        vectordb = Chroma(
                            persist_directory=CHROMA_PATH,
                            embedding_function=embeddings
                        )
                    vectordb.add_documents(batch)
                
                # Persist after each batch to avoid losing progress
                vectordb.persist()
                break  # Success, exit retry loop
                
            except Exception as e:
                retry_count += 1
                if "429" in str(e) or "rate limit" in str(e).lower():
                    wait_multiplier = retry_count * 2  # Exponential backoff
                    wait_duration = 60 * wait_multiplier
                    print(f"Rate limit hit (attempt {retry_count}/{max_retries}). Waiting {wait_duration} seconds...")
                    time.sleep(wait_duration)
                else:
                    print(f"Error processing batch {batch_num}: {e}")
                    if retry_count >= max_retries:
                        raise e
                    time.sleep(30)  # Wait before retrying non-rate-limit errors
        
        # Add delay between batches to respect rate limits (except for last batch)
        if i + batch_size < len(chunks):
            print("Waiting 2 seconds before next batch...")
            time.sleep(2)
    
    print(f"Successfully saved {len(chunks)} chunks to {CHROMA_PATH}.")

# 4. Query the vector store for relevant context
def query_rag(query, k=2, relevance_threshold=0.5):
    embeddings = get_azure_embeddings()
    
    vectordb = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )
    results = vectordb.similarity_search_with_relevance_scores(query, k=k)
    if not results or results[0][1] < relevance_threshold:
        print("No relevant results found.")
        return ""
    context = "\n\n---\n\n".join([doc.page_content for doc, _ in results])
    return context

if __name__ == "__main__":
    # Build the vector store with Azure embeddings
    build_vector_store(resume=True)
    
    # Example queries:
    print("\n=== TESTING QUERIES ===")
    print("PREGUNTA 1: ¿Qué es la economía?")
    print(query_rag("¿Qué es la economía?"))

    # print("\n***********\nPREGUNTA 2: ¿Cuáles son los principales indicadores económicos de Argentina?\n")
    # print(query_rag("¿Cuáles son los principales indicadores económicos de Argentina?"))

    # print("\n***********\nPREGUNTA 3: ¿Cómo afecta la inflación a la economía de un país?\n")
    # print(query_rag("¿Cómo afecta la inflación a la economía de un país?"))

    # print("\n ===TESTING QUERIES BY TEXT ===\n")
    
    # preguntas_con_texto.py

    # print("Texto: Principios-de-economía.pdf")
    # print("Pregunta: ¿Cuáles fueron las tres razones que motivaron a los autores a escribir un texto propio para el curso de economía en la Universidad de San Andrés?\n")
    # print(query_rag("¿Cuáles fueron las tres razones que motivaron a los autores a escribir un texto propio para el curso de economía en la Universidad de San Andrés?"))
    # print("\n")

    # print("Texto: EcoiaParaNoEcoistas.pdf")
    # print("Pregunta: ¿Qué ejemplo utiliza el prólogo para ilustrar cómo el poder de mercado puede perjudicar a los consumidores incluso fuera del ámbito empresarial tradicional?\n")
    # print(query_rag("¿Qué ejemplo utiliza el prólogo para ilustrar cómo el poder de mercado puede perjudicar a los consumidores incluso fuera del ámbito empresarial tradicional?"))
    # print("\n")

    # print("Texto: BCRA-PUSF-Informe-2024.pdf")
    # print("Pregunta: ¿Cuáles son los tres ejes de acción que el BCRA define como 'las 3 P' en su informe sobre la protección de las personas usuarias de servicios financieros?\n")
    # print(query_rag("¿Cuáles son los tres ejes de acción que el BCRA define como 'las 3 P' en su informe sobre la protección de las personas usuarias de servicios financieros?"))
    # print("\n")

    # print("Texto: ARCA-sistema_tarjetas_de_debito_y_credito_v1.0.pdf")
    # print("Pregunta: ¿Cuál es el objetivo del módulo Tarjetas de Débito/Crédito dentro del sistema de Trámites con Clave Fiscal?\n")
    # print(query_rag("¿Cuál es el objetivo del módulo Tarjetas de Débito/Crédito dentro del sistema de Trámites con Clave Fiscal?"))
    # print("\n")

    # print("Texto: ARCA-Procedimiento-gestion-clave-fiscal-doble-factor-TOKEN.pdf")
    # print("Pregunta: ¿Qué ocurre con una aplicación OTP existente cuando se activa la aplicación Token para clave fiscal nivel 4?\n")
    # print(query_rag("¿Qué ocurre con una aplicación OTP existente cuando se activa la aplicación Token para clave fiscal nivel 4?"))
    # print("\n")

    # print("Texto: ARCA-Manual-Autodeclaracion-Deudas-Aduaneras-Ley-27743-Usuarios-Externos.pdf")
    # print("Pregunta: ¿Qué fecha debe indicarse como 'Fecha Momento Imponible' al generar una LMAN por deudas aduaneras en pesos bajo la Ley 27.743?\n")
    # print(query_rag("¿Qué fecha debe indicarse como 'Fecha Momento Imponible' al generar una LMAN por deudas aduaneras en pesos bajo la Ley 27.743?"))
    # print("\n")

    # print("Texto: ARCA-Declaracion-de-Deudas-Aduaneras-para-sujetos-no-imex.pdf")
    # print("Pregunta: ¿Qué información debe incluirse en la solicitud de generación de una LMAN por parte de un sujeto sin perfil IMEX?\n")
    # print(query_rag("¿Qué información debe incluirse en la solicitud de generación de una LMAN por parte de un sujeto sin perfil IMEX?"))
    # print("\n")

    # print("Texto: ARCA-AutorizacionesElectronicasISTA.pdf")
    # print("Pregunta: ¿Qué formulario se emite como constancia cuando se crea una nueva autorización electrónica para transportistas ISTA?\n")
    # print(query_rag("¿Qué formulario se emite como constancia cuando se crea una nueva autorización electrónica para transportistas ISTA?"))
    # print("\n")