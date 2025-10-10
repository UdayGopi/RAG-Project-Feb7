Agentic RAG Application with LlamaIndex and Groq
This is a full-stack agentic RAG (Retrieval-Augmented Generation) application that provides context-aware responses to user queries based on uploaded documents and ingested URLs.

File Structure
Here is the recommended file structure for this project:

/
|-- app.py                  # Main Flask application file
|-- rag_agent.py            # Core logic for the RAG agent
|-- utils.py                # Optional utility functions
|-- requirements.txt        # Python dependencies
|-- .env                    # Environment variables (e.g., API keys)
|-- README.md               # This file
|-- /static/
|   |-- care-policy-hub.html  # The single-page frontend
|-- /documents/
|   |-- (Uploaded files will appear here)

Setup
1. Prerequisites
Python 3.8+

An API key from Groq.

2. Installation
Clone the repository and install the dependencies:

git clone <repository_url>
cd <repository_name>
pip install -r requirements.txt

3. Environment Variables
Create a .env file in the root directory by copying the .env.example file. Then, add your Groq API key:

GROQ_API_KEY="gsk_..."

4. Running the Application
Start the Flask backend server:

python app.py

The application will be available at http://127.0.0.1:5001.

How to Use
Open the application in your web browser.

Navigate to the Upload Docs tab.

Upload documents using the drag-and-drop area. Supported formats are .pdf, .docx, and .txt.

Ingest a URL by pasting a web address into the URL input field.

Click Upload & Ingest. The backend will process the files/URL and update its knowledge base.

Navigate back to the Chat tab and ask questions to get answers based on the content you provided.