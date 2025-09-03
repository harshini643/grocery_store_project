# grocery_store_project
A simple Flask-based online grocery store with cart, wishlist, and charity donation features.
# 🛒 Grocery Store

A simple **Flask-based online grocery store** with features like shopping cart, wishlist, and charity donation support.

---

## 📌 Features
- 🛍️ Add products to **cart** and manage quantities  
- ❤️ Add/remove items from **wishlist**  
- 💝 **Support charity** with optional donations at checkout  
- 👤 User authentication (register/login)  
- 📦 Checkout with order details  

---

## ⚙️ Tech Stack
- **Backend:** Flask, SQLAlchemy, Flask-Migrate  
- **Frontend:** HTML, CSS, JavaScript, Jinja2 Templates  
- **Database:** SQLite (can be switched to PostgreSQL/MySQL)  

---

## 🚀 Getting Started

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/grocery-store.git
cd grocery-store
2️⃣ Create a Virtual Environment
python -m venv .venv
source .venv/bin/activate   # On Linux/Mac
.venv\Scripts\activate      # On Windows
3️⃣ Install Dependencies
pip install -r requirements.txt
4️⃣ Set up the Database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
5️⃣ Run the Application
flask --app app run


