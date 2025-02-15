import streamlit as st
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from hashlib import sha256
import smtplib
import time
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bson.objectid import ObjectId
import pandas as pd
from urllib.parse import quote_plus

# Initialize Database
def init_db():
    username = "harzrawat"
    password = "Harsh@517"
    cluster = "cluster0.uronj.mongodb.net"
    
    # Encode credentials
    encoded_username = quote_plus(username)
    encoded_password = quote_plus(password)
    
    # Create connection URI
    uri = f"mongodb+srv://{encoded_username}:{encoded_password}@{cluster}/?retryWrites=true&w=majority&appName=Cluster0"
    
    try:
        client = MongoClient(uri, server_api=ServerApi('1'))
        # Verify connection
        client.admin.command('ping')
        # print("Successfully connected to MongoDB Atlas!")
        db = client.library
        return db
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {e}")
        return None


def init_session_state():
    # Initialize persistent session state variables if they don't exist
    if "persistent_login" not in st.session_state:
        st.session_state.persistent_login = False
    if "persistent_username" not in st.session_state:
        st.session_state.persistent_username = None
    if "persistent_role" not in st.session_state:
        st.session_state.persistent_role = None


# Rest of the functions remain the same
def hash_password(password):
    return sha256(password.encode()).hexdigest()

def authenticate_user(username, password, db):
    user = db.users.find_one({"username": username, "password": hash_password(password)})
    if user:
        st.session_state["user_id"] = user["user_id"]  # Store user_id in session state
        return user["role"]
    return None

# SMTP Email Credentials (Replace with your email & app password)
EMAIL_ADDRESS = "harzrawat@gmail.com"
EMAIL_PASSWORD = "fxst rkmy mkcu nzcn"

def send_otp(email):
    otp = str(random.randint(100000, 999999))
    st.session_state["otp"] = otp
    st.session_state["otp_timestamp"] = time.time()
    st.session_state["otp_sent_to"] = email

    subject = "Your OTP for Registration"
    body = f"Your OTP for signing up is: {otp}. It will expire in 5 minutes."

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, email, msg.as_string())
        server.quit()

        st.success(f"OTP sent to {email}. Check your inbox (and spam folder).")
    except Exception as e:
        st.error("Failed to send OTP. Check email settings.")
        print(e)

def verify_otp(user_otp):
    if "otp" in st.session_state:
        if time.time() - st.session_state["otp_timestamp"] > 300:
            st.error("OTP expired! Request a new one.")
            return False
        return user_otp == st.session_state["otp"]
    return False

def get_admin_password(db, admin_username):
    admin = db.users.find_one({"username": admin_username, "role": "admin"})
    return admin["password"] if admin else None

# User Registration with Email OTP
def sign_up_page(db):
    st.title("📝 User Registration")

    admin_username = st.text_input("Admin Username", key="admin_username")
    admin_password = st.text_input("Admin Password", type="password", key="admin_password")

    username = st.text_input("Username", key="username")
    password = st.text_input("Password", type="password", key="password")
    user_id = st.text_input("User ID", key="user_id")
    name = st.text_input("Full Name", key="name")
    email = st.text_input("Email Address", key="email")

    if st.button("Send OTP", key="send_otp_btn"):
        send_otp(email)

    otp_input = st.text_input("Enter OTP", key="otp_input")

    if st.button("Sign Up", key="sign_up_btn"):
        stored_admin_password = get_admin_password(db, admin_username)
        if stored_admin_password and stored_admin_password == hash_password(admin_password):
            if db.users.find_one({"username": username}):
                st.error("Username already exists!")
            elif db.users.find_one({"user_id": user_id}):
                st.error("User ID already registered, try logging in directly.")
            elif not verify_otp(otp_input):
                st.error("Invalid or expired OTP!")
            else:
                db.users.insert_one({
                    "username": username,
                    "password": hash_password(password),
                    "user_id": user_id,
                    "name": name,
                    "email": email,
                    "role": "user"
                })
                st.success("User registered successfully! You can now log in.")
                st.session_state.pop("otp", None)
                st.session_state["sign_up"] = False
        else:
            st.error("Invalid Admin Credentials!")

    if st.button("Back to Login", key="back_to_login"):
        st.session_state["sign_up"] = False
        st.rerun()

# Login Page
def login_page(db):
    st.title("📚 Library Management Portal")
    
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")
    
    if st.button("Login", key="login_btn"):
        role = authenticate_user(username, password, db)
        if role:
            # Set both regular and persistent session state
            st.session_state.logged_in = True
            st.session_state.username = username
            st.session_state.role = role
            st.session_state.persistent_login = True
            st.session_state.persistent_username = username
            st.session_state.persistent_role = role
            st.rerun()
        else:
            st.error("Invalid Credentials")
    
    if st.button("Sign Up", key="go_to_signup"):
        st.session_state.sign_up = True
        st.rerun()
def user_dashboard(username, db):
    col1, col2 = st.columns([5, 1])  # 8:1 ratio for title and button
    with col1:
        st.title("📖 User Dashboard")
    with col2:
        if st.button("🔓Logout&#10162;"):
            logout()

    # Add error handling for user data
    user_data = db.users.find_one({"username": username})
    if not user_data:
        st.error(f"User data not found for username: {username}")
        logout()
        return

    user_id = user_data["user_id"]
    st.sidebar.subheader(f"Welcome, {username} (ID: {user_id})")

    # Section 1: Issue a Book
    st.subheader("📚 Issue a Book")

    # Fetch available ISBNs from the "books" collection
    books_data = list(db.books.find({}, {"_id": 0, "ISBN": 1, "book_name": 1}))
    if not books_data:
        st.warning("⚠️ No books available for issue.")
        return

    isbn_options = {book["ISBN"]: book["book_name"] for book in books_data}
    
    selected_isbn = st.selectbox("Select ISBN-Book", options=isbn_options.keys(), format_func=lambda x: f"{x} - {isbn_options[x]}")
    copies = st.number_input("No. of Copies", min_value=1, step=1)

    if st.button("Issue Book"):
        book_data = db.books.find_one({"ISBN": selected_isbn})

        if not book_data:
            st.error("❌ Book not found.")
        elif book_data["copies"] < copies:
            st.error(f"❌ Not enough copies available. Only {book_data['copies']} left.")
        else:
            issue_data = {
                "user_id": user_id,
                "book_name": isbn_options[selected_isbn],
                "ISBN": selected_isbn,
                "copies_issued": copies,
                "issued_on": time.strftime("%Y-%m-%d")
            }
            db.books_issued.insert_one(issue_data)

            # Reduce the available copies in the "books" collection
            db.books.update_one(
                {"ISBN": selected_isbn},
                {"$inc": {"copies": -copies}}
            )

            st.success("✅ Book issued successfully!")

    # Section 2: View Transactions
    st.subheader("📜 Your Transactions")

    # Issued Books Table
    st.write("### 📘 Issued Books")
    issued_books = list(db.books_issued.find({"user_id": user_id}, {"_id": 0}))
    if issued_books:
        st.table(issued_books)
    else:
        st.info("No books issued.")

    # Returned Books Table
    st.write("### 📗 Returned Books")
    returned_books = list(db.books_returned.find({"user_id": user_id}, {"_id": 0}))
    if returned_books:
        st.table(returned_books)
    else:
        st.info("No books returned.")
import datetime

def return_book(db, book_id):
    book = db.books_issued.find_one({"_id": ObjectId(book_id)})
    if book:
        book["returned_on"] = datetime.datetime.now().strftime("%Y-%m-%d")  # Add return date
        db.books_returned.insert_one(book)  # Insert into returned books
        db.books_issued.delete_one({"_id": ObjectId(book_id)})  # Remove from issued books

        # Increase the available copies in the "books" collection
        db.books.update_one(
            {"ISBN": book["ISBN"]},
            {"$inc": {"copies": book["copies_issued"]}}  # Increment copies by the returned amount
        )

        st.success(f"Book '{book['book_name']}' marked as returned! Available copies updated.")

# Admin Dashboard

def admin_dashboard(db):
    # Layout for logout button at the top-right
    col1, col2 = st.columns([5, 1])
    with col1:
        st.title("📚 Admin Dashboard")
    with col2:
        if st.button("🔓Logout&#10162;"):
            logout()

    # Sidebar Dropdown
    st.sidebar.subheader("📌 Sections")
    section = st.sidebar.selectbox("Select Section", ["Issued Books", "Returned Books", "Available Books", "Add New Books"])

    if section == "Issued Books":
        
        # Issued Books Section
        st.subheader("📖 Issued Books")
        issued_books = list(db.books_issued.find())

        if issued_books:
            # Convert ObjectId to string for Streamlit compatibility
            for book in issued_books:
                book["_id"] = str(book["_id"])

            # Display Table Headers
            cols = st.columns([3, 3, 2, 2, 2, 2])  # Adjust width
            with cols[0]: st.write("Action")
            with cols[1]: st.write("Book Name")
            with cols[2]: st.write("ISBN")
            with cols[3]: st.write("Copies Issued")
            with cols[4]: st.write("User ID")
            with cols[5]: st.write("Date Issued")

            # Display Each Row
            for book in issued_books:
                cols = st.columns([3, 3, 2, 2, 2, 2])  # Ensure same column width

                # with cols[0]:  
                #     if st.button("🔄 Return", key=f"return_{book['_id']}"):
                #         return_book(db, book["_id"])
                #         st.rerun()
                with cols[0]:  
                    if st.button("🔄 Return", key=f"return_{book['_id']}"):
                        return_book(db, book["_id"])
                        st.session_state["return_message"] = f"✅ Book '{book['book_name']}' returned successfully!"
                        st.rerun()

                with cols[1]: st.write(book["book_name"])
                with cols[2]: st.write(book["ISBN"])
                with cols[3]: st.write(book["copies_issued"])
                with cols[4]: st.write(book["user_id"])
                with cols[5]: st.write(book["issued_on"])
            if "return_message" in st.session_state:
                st.success(st.session_state["return_message"])
                del st.session_state["return_message"]  # Remove message after displaying


        else:
            st.info("No books issued.")


    elif section == "Returned Books":
        st.subheader("📚 Returned Books")
        returned_books = list(db.books_returned.find())

        if returned_books:
            df_returned = pd.DataFrame(returned_books).rename(columns={
                "book_name": "Book Name",
                "ISBN": "ISBN",
                "copies_issued": "Copies Issued",
                "issued_on": "Date Issued",
                "returned_on": "Date Returned",
                "user_id": "Returned By (User ID)"
            })
            st.dataframe(df_returned)
        else:
            st.info("No books returned.")

    elif section == "Available Books":
        st.subheader("📗 Available Books")
        available_books = list(db.books.find())

        if available_books:
            df_books = pd.DataFrame(available_books).rename(columns={
                "book_name": "Book Name",
                "ISBN": "ISBN",
                "copies": "Available Copies",
                "author": "Author Name"
            })
            st.dataframe(df_books)
        else:
            st.info("No books available.")

    elif section == "Add New Books":
        st.subheader("📥 Add New Books")
        
        book_name = st.text_input("📖 Book Name")
        isbn = st.text_input("🔢 ISBN")
        copies = st.number_input("📦 Number of Copies", min_value=1, step=1)
        author = st.text_input("✍️ Author Name")

        if st.button("➕ Add Book"):
            if book_name and isbn and copies and author:
                new_book = {
                    "book_name": book_name,
                    "ISBN": isbn,
                    "copies": copies,
                    "author": author
                }
                db.books.insert_one(new_book)
                st.success(f"✅ Book '{book_name}' added successfully!")
            else:
                st.warning("⚠️ Please fill in all the fields.")

def logout():
    # Clear both regular and persistent session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    # Reinitialize session state
    init_session_state()
    st.rerun()


# Main App Logic
db = init_db()

if db is None:
    st.error("Failed to connect to MongoDB. Please check your connection settings.")
else:
    # Initialize session state
    init_session_state()
    
    # Check persistent login state
    if st.session_state.persistent_login:
        # Restore session from persistent state
        st.session_state.logged_in = True
        st.session_state.username = st.session_state.persistent_username
        st.session_state.role = st.session_state.persistent_role
        
        # Show appropriate dashboard
        if st.session_state.persistent_role == "admin":
            admin_dashboard(db)
        else:
            user_dashboard(st.session_state.persistent_username, db)
    else:
        # Regular authentication flow
        if "sign_up" not in st.session_state:
            st.session_state.sign_up = False
            
        if st.session_state.sign_up:
            sign_up_page(db)
        else:
            login_page(db)
