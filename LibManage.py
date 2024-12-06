import streamlit as st
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import pandas as pd

import sys
print(sys.version)
import ssl
import socket

def check_tls_version():
    context = ssl.create_default_context()
    connection = context.wrap_socket(socket.socket(), server_hostname="www.google.com")
    connection.connect(('www.google.com', 443))
    tls_version = connection.version()
    print(f"TLS version used: {tls_version}")

check_tls_version()


# from pymongo.mongo_client import MongoClient
# from pymongo.server_api import ServerApi

# python -m pip install "pymongo[srv]"2

# Send a ping to confirm a successful connection


from pymongo import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus

class LibraryManagementApp:
    def __init__(self, username="harzrawat", password="Harsh@517", cluster="cluster0.uronj.mongodb.net"):
        """
        Initialize MongoDB connection
        """
        try:
            # Encode username and password
            encoded_username = quote_plus(username)
            encoded_password = quote_plus(password)

            # Create URI
            uri = f"mongodb+srv://{encoded_username}:{encoded_password}@{cluster}/?retryWrites=true&w=majority&appName=Cluster0"

            self.client = MongoClient(uri, server_api=ServerApi('1'))
            
            # Ping the deployment to confirm connection
            try:
                self.client.admin.command('ping')
                print("Pinged your deployment. You successfully connected to MongoDB!")
            except Exception as e:
                print(f"Error pinging MongoDB: {e}")

            # Initialize database and collections
            self.db = self.client['library_db']
            self.books_collection = self.db['books']
            self.members_collection = self.db['members']
            self.transactions_collection = self.db['transactions']
            self.collections = {
                'Books': self.books_collection,
                'Members': self.members_collection,
                'Transactions': self.transactions_collection
            }

        except pymongo.errors.ConnectionFailure as e:
            print(f"MongoDB connection error: {e}")



    def convert_objectid(self, value):
        """
        Convert ObjectId to string
        """
        if isinstance(value, ObjectId):
            return str(value)
        elif isinstance(value, dict):
            return {k: self.convert_objectid(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.convert_objectid(v) for v in value]
        return value

    def fetch_collection_data(self, collection_name, filters=None, sort_by=None, sort_order=1, limit=100):
        """
        Fetch data from specified collection with optional filtering and sorting
        """
        try:
            filters = filters or {}
            query = self.collections[collection_name].find(filters)
            
            if sort_by:
                query = query.sort(sort_by, sort_order)
            
            query = query.limit(limit)
            results = [self.convert_objectid(doc) for doc in query]
            return pd.DataFrame(results)
        
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            return pd.DataFrame()

    def add_book_form(self):
        """
        Streamlit form for adding books
        """
        st.header("📚 Add New Book")
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Book Title")
            isbn = st.text_input("ISBN")
            publication_year = st.number_input("Publication Year", min_value=1000, max_value=datetime.now().year)
        
        with col2:
            authors = st.text_input("Authors (comma-separated)")
            genre = st.text_input("Genres (comma-separated)")
            total_copies = st.number_input("Total Copies", min_value=1, value=1)
        
        publisher = st.text_input("Publisher")
        description = st.text_area("Book Description")
        
        if st.button("Add Book"):
            if not title or not authors:
                st.warning("Title and Authors are required!")
                return
            
            book_data = {
                'title': title,
                'authors': [author.strip() for author in authors.split(',')],
                'isbn': isbn,
                'genre': [g.strip() for g in genre.split(',')] if genre else [],
                'publication_year': publication_year,
                'publisher': publisher,
                'total_copies': total_copies,
                'available_copies': total_copies,
                'description': description,
                'added_date': datetime.now()
            }
            
            try:
                result = self.collections['Books'].insert_one(book_data)
                st.success(f"Book '{title}' added successfully! ID: {result.inserted_id}")
            except Exception as e:
                st.error(f"Error adding book: {e}")

    def add_member_form(self):
        """
        Streamlit form for registering members
        """
        st.header("👥 Register New Member")
        
        col1, col2 = st.columns(2)
        
        with col1:
            first_name = st.text_input("First Name")
            email = st.text_input("Email Address")
            membership_type = st.selectbox("Membership Type", [
                "Standard", "Premium", "Student", "Senior"
            ])
        
        with col2:
            last_name = st.text_input("Last Name")
            phone = st.text_input("Phone Number")
            date_of_birth = st.date_input("Date of Birth")
        
        address = st.text_area("Address")
        
        if st.button("Register Member"):
            # Validate inputs
            if not first_name or not last_name or not email:
                st.warning("First Name, Last Name, and Email are required!")
                return
            
            # Prepare member data
            member_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'membership_type': membership_type,
                'date_of_birth': datetime.combine(date_of_birth, datetime.min.time()),  # Convert date to datetime
                'address': address,
                'registration_date': datetime.now(),
                'borrowed_books': [],
                'active': True
            }
            
            try:
                result = self.members_collection.insert_one(member_data)
                st.success(f"Member {first_name} {last_name} registered successfully! ID: {result.inserted_id}")
            except Exception as e:
                st.error(f"Error registering member: {e}")
    
    def add_transaction_form(self):
        """
        Streamlit form for creating book transactions
        """
        st.header("📖 Book Borrowing Transaction")

        # Fetch books and members for dropdown
        books = list(self.collections['Books'].find({}, {'_id': 1, 'title': 1, 'available_copies': 1}))
        members = list(self.collections['Members'].find({}, {'_id': 1, 'first_name': 1, 'last_name': 1, 'email': 1}))

        # Create dropdowns
        book_titles = {str(book['_id']): book['title'] for book in books}
        member_names = {str(member['_id']): f"{member['first_name']} {member['last_name']}" for member in members}

        selected_book_id = st.selectbox("Select Book", options=book_titles.keys(), format_func=book_titles.get)
        selected_member_id = st.selectbox("Select Member", options=member_names.keys(), format_func=member_names.get)

        borrow_date = st.date_input("Borrow Date")
        due_date = st.date_input("Due Date")

        if st.button("Create Transaction"):
            try:
                transaction_data = {
                    'book_id': ObjectId(selected_book_id),
                    'book_title': book_titles[selected_book_id],
                    'member_id': ObjectId(selected_member_id),
                    'member_name': member_names[selected_member_id],
                    'borrow_date': datetime.combine(borrow_date, datetime.min.time()),
                    'due_date': datetime.combine(due_date, datetime.min.time()),
                    'status': 'Active'
                }

                # Insert transaction
                result = self.collections['Transactions'].insert_one(transaction_data)

                # Update book's available copies
                self.collections['Books'].update_one(
                    {'_id': ObjectId(selected_book_id)},
                    {'$inc': {'available_copies': -1}}
                )

                st.success(f"Transaction created successfully! ID: {result.inserted_id}")

            except Exception as e:
                st.error(f"Error creating transaction: {e}")


    def add_transaction(self, member_id, book_id, transaction_type, transaction_date):
        """
        Add a new transaction to the library
        """
        try:
            transaction = {
                "member_id": member_id,
                "book_id": book_id,
                "transaction_type": transaction_type,  # e.g., 'borrow' or 'return'
                "transaction_date": datetime.combine(transaction_date, datetime.min.time())  # Convert date to datetime
            }
            
            # Insert transaction into the collection
            result = self.collections['Transactions'].insert_one(transaction)
            st.success(f"Transaction created successfully with ID: {result.inserted_id}")
        except Exception as e:
            st.error(f"Error creating transaction: {e}")

    def display_collection_data(self):
        """
        Display collection data
        """
        st.header("📊 Library Data Viewer")
        
        # Step 1: Allow collection selection
        selected_collection = st.selectbox("Select Collection to View", list(self.collections.keys()))
        
        # Step 2: Fetch a sample record to dynamically determine columns
        sample_df = self.fetch_collection_data(selected_collection, limit=1)
        available_columns = list(sample_df.columns) if not sample_df.empty else []
        
        # Step 3: Sidebar options
        filters = {}  # Add filters logic here if needed
        sort_column = st.sidebar.selectbox("Sort By", available_columns)
        sort_order = st.sidebar.radio("Sort Order", ["Ascending", "Descending"])
        limit = st.sidebar.slider("Number of Records", 10, 500, 100)
        
        # Step 4: Fetch data from the selected collection
        df = self.fetch_collection_data(
            selected_collection, 
            filters=filters, 
            sort_by=sort_column, 
            sort_order=1 if sort_order == "Ascending" else -1,
            limit=limit
        )
        
        # Step 5: Display the data
        st.dataframe(df)

        # Optional: Show collection insights
        st.subheader("📈 Data Insights")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Records", len(df))
        with col2:
            if not df.empty and '_id' in df.columns:
                st.metric("First Record ID", df.iloc[0]['_id'])

    def run(self):
        """
        Main Streamlit app runner
        """
        st.sidebar.title("Library Management System")
        menu = st.sidebar.selectbox(
            "Menu",
            ["Add Book", "Register Member", "Create Transaction", "View Data"]
        )
        
        if menu == "Add Book":
            self.add_book_form()
        elif menu == "Register Member":
            self.add_member_form()
        elif menu == "Create Transaction":
            self.add_transaction_form()
        elif menu == "View Data":
            self.display_collection_data()

def main():
    st.set_page_config(page_title="Library Management System", page_icon="📚", layout="wide")
    app = LibraryManagementApp()
    app.run()

if __name__ == "__main__":
    main()
