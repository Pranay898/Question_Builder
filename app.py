import os
import streamlit as st
import pandas as pd
import sqlite3
import tempfile
from langchain_google_genai import GoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.schema import Document
from login_regist import check_login, register_user, update_user_role
from langchain.globals import set_verbose
set_verbose(True)

# Initialize the LLM
api_key = "AIzaSyCkhwdytqyr039-BnhACY2RzexSUZZcwB4"  # Replace with your actual API key
llm = GoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key, temperature=1.0)
os.environ["GOOGLE_API_KEY"] = api_key

# Streamlit UI with Enhanced CSS
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://static.vecteezy.com/system/resources/previews/013/118/479/large_2x/questions-mark-illustration-inside-of-background-for-faq-and-question-and-answer-time-free-photo.jpg");
        background-size: cover;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Poppins', sans-serif;
    }
    .stTitle {
        color: #FFD700;
        text-align: center;
        font-size: 2.8em;
        margin-top: 20px;
        font-weight: 700;
        text-shadow: 2px 2px 4px #000000;
    }
    .stMarkdown {
        color: #FFFFFF;
    }
    .stButton>button {
        background-color: #FF5733;
        color: white;
        border-radius: 15px;
        font-size: 1.3em;
        padding: 10px 25px;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #C70039;
    }
    .stDataFrame {
        background-color: rgba(255, 255, 255, 0.9);
        border-radius: 15px;
        padding: 10px;
        font-size: 1.1em;
        color: #000;
    }
    .sidebar .sidebar-content {
        background-color: #000000;
        color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Application Title
st.title("Automated Question Builder")

# Initialize session state for authentication and role management
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'role' not in st.session_state:
    st.session_state.role = None

# Authentication & Role Management
if not st.session_state.authenticated:
    auth_choice = st.selectbox("Login or Register", ["Login", "Register"])
    if auth_choice == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            role = check_login(username, password)
            if role:
                st.session_state.authenticated = True
                st.session_state.role = role
                st.success(f"Logged in as {role.capitalize()}")
            else:
                st.error("Login failed. Please check your credentials.")
    else:
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        if st.button("Register"):
            register_user(new_username, new_password)  # Assign default role "User"
            st.success("Registration successful! Please log in.")
else:
    # Sidebar for logout and role information
    with st.sidebar:
        st.markdown(f"**Logged in as:** {st.session_state.role.capitalize()}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.role = None
            st.session_state.clear()  # Clear the session state
            st.success("Logged out successfully. Please log in again.")

    # Admin-only section for managing user roles
    if st.session_state.authenticated and st.session_state.role == "admin":
        st.subheader("User Role Management")
        # Fetch all users and their roles
        with sqlite3.connect('user_data.db') as conn:
            c = conn.cursor()
            c.execute("SELECT username, role FROM users")
            users = c.fetchall()

        # Display a table with usernames and roles, and provide role-changing options
        for user, role in users:
            if user != "admin":  # Prevent changing the role of the main admin
                new_role = st.selectbox(
                    f"Role for {user}",
                    ["Admin", "Trainer", "User"],
                    index=["Admin", "Trainer", "User"].index(role),
                    key=user
                )
                if st.button(f"Update role for {user}"):
                    update_user_role(user, new_role)
                    st.success(f"Updated role for {user} to {new_role}")

    # Prompt Type Selection
    prompt_type = st.radio("Choose Prompt Type", ["PDF Upload", "Text Prompt"])

    # Handle PDF upload or text prompt
    chunks = []
    if prompt_type == "PDF Upload":
        uploaded_file = st.file_uploader("Upload a PDF file", type="pdf")
        if uploaded_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                temp_file_path = tmp_file.name

            loader = PyPDFLoader(temp_file_path)
            pages = loader.load_and_split()

            R_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=20)
            chunks = R_splitter.split_documents(pages)
            os.remove(temp_file_path)

    elif prompt_type == "Text Prompt":
        text_prompt = st.text_area("Enter your text prompt here")
        if text_prompt:
            chunks = [Document(page_content=text_prompt)]

    # Embedding and Vector Index Creation
    if chunks:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        vectorindex = FAISS.from_documents(chunks, embeddings)

        num_questions = st.number_input("Enter the number of questions to generate", min_value=1, value=5)
        difficulty = st.selectbox("Select the difficulty level", ["Easy", "Medium", "Hard"])

        if st.button("Generate Questions"):
            qa_pairs = []
            for i in range(num_questions):
                if chunks:
                    context = chunks[i % len(chunks)].page_content[:500]
                    prompt_template = (
                        f"Based on the following context, generate a {difficulty.lower()} question and provide a detailed answer:\n\n"
                        f"Context: {context}\n\n"
                        f"Question:"
                    )

                    try:
                        response = llm.generate([prompt_template])
                        if response and len(response.generations) > 0:
                            qa_pair = response.generations[0][0].text.strip()
                            qa_pairs.append(qa_pair)
                        else:
                            qa_pairs.append("No question and answer generated.")
                    except Exception as e:
                        qa_pairs.append(f"Error generating question and answer: {e}")

            df = pd.DataFrame({"Questions and Answers": qa_pairs})
            st.dataframe(df)

            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Questions as CSV",
                csv,
                "questions.csv",
                "text/csv",
                key='download-csv'
            )
