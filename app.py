import os
import re
import uuid
import json
from datetime import datetime,timedelta
from flask_migrate import Migrate

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

shared_carts = {}
shared_wishlists = {}
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'instance', 'grocery.db'))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, '..', 'frontend', 'templates'),
    static_folder=os.path.join(BASE_DIR, '..', 'frontend', 'static'),
    static_url_path='/static'
)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate=Migrate(app,db)

# -------------------- Models --------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text, nullable=False)
    contact_number = db.Column(db.String(15), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(255), default='https://via.placeholder.com/300x200?text=No+Image')
    category = db.Column(db.String(80), default='General')
    stock = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_email = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    donation_amount = db.Column(db.Float, default=0.0)
    charity_name = db.Column(db.String(120), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)

class SharedCart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False)
    cart_data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Add these models to your existing models or in app.py after your existing Product model

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('wishlist_items', lazy=True))
    product = db.relationship('Product', backref=db.backref('wishlist_items', lazy=True))
    
    # Ensure unique combination of user_id and product_id
    _table_args_ = (db.UniqueConstraint('user_id', 'product_id', name='unique_user_product'),)

class SharedWishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(36), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wishlist_data = db.Column(db.Text, nullable=False)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    
    # Relationship
    user = db.relationship('User', backref=db.backref('shared_wishlists', lazy=True))



class Charity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default='')
    website = db.Column(db.String(255), default='')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# -------------------- Authentication Helper --------------------
def login_required(f):
    """Decorator to require login for certain routes"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to continue.", "warning")
            # Store the URL user was trying to access
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# -------------------- Validation Helpers --------------------
def is_valid_email(email):
    """Check if email format is valid"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_strong_password(password):
    """Check if password is strong (uppercase, lowercase, number, special character)"""
    if len(password) < 8:
        return False
    
    has_upper = bool(re.search(r'[A-Z]', password))
    has_lower = bool(re.search(r'[a-z]', password))
    has_digit = bool(re.search(r'\d', password))
    has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
    
    return has_upper and has_lower and has_digit and has_special

# -------------------- Helpers --------------------
def init_db():
    db.create_all()
    print("Database tables created/verified.")
    
    try:
        if not User.query.filter_by(username='admin').first():
            admin = User(
                name='Administrator',
                username='admin', 
                email='admin@grocery.com',
                address='Admin Office',
                contact_number='1234567890'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")
    except Exception as e:
        print(f"Error with admin user: {e}")
        print("This might be due to schema mismatch. Please delete the database file manually.")
        print(f"Database location: {DB_PATH}")
        return
    
    try:
        if Product.query.count() == 0:
            seed_products = [
                Product(name='Fresh Apples (1kg)', description='Crisp and sweet red apples.', price=120.0, category='Fruits', image_url='https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Red_Apple.jpg/800px-Red_Apple.jpg'),
                Product(name='Bananas (1 dozen)', description='Ripe bananas full of potassium.', price=60.0, category='Fruits',  image_url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSiph_r-pTwfrGBghkxIdd3PEz0Z_oqH7wTeA&s'),
                Product(name='Whole Wheat Bread', description='Soft and healthy bread loaf.', price=45.0, category='Bakery', image_url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS3tzH2DPXSqmbOn3ygcB5KI5q-CIMbY3aQqA&s'),
                Product(name='Organic Milk (1L)', description='Farm fresh organic milk.', price=70.0, category='Dairy', image_url='https://mea.arla.com/4970d5/globalassets/arla-organic-milk/general/arla_organic_milk-product_range.jpg'),
                Product(name='Brown Eggs (12pc)', description='Free-range brown eggs.', price=85.0, category='Dairy', image_url='https://cdn.britannica.com/94/151894-050-F72A5317/Brown-eggs.jpg'),
                Product(name='Basmati Rice (5kg)', description='Long-grain aromatic rice.', price=520.0, category='Grains', image_url='https://flourworks.in/wp-content/uploads/2023/06/1-12.jpeg'), 
                Product(name='Notebook (200 pages)', description='College ruled notebook.', price=50.0, category='Stationary', image_url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSgONwv10P8D4pN_96QMbOVUlG63DXVFPgpHg&s'),
                Product(name='Ballpoint Pen (Pack of 5)', description='Smooth writing pens.', price=30.0, category='Stationary', image_url='https://static2.jetpens.com/images/a/000/253/253360.jpg?s=4378aba1d97fd5134ee408f1e42e5e9c'),
                Product(name='Fresh Carrots (1kg)', description='Organic carrots.', price=40.0, category='Vegetables', image_url='https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTWp3Vx2S_zSSRoLboLpODBfF2QR-HOXcKFKg&s'),
                Product(name='Tomatoes (1kg)', description='Fresh red tomatoes.', price=35.0, category='Vegetables', image_url='https://media.post.rvohealth.io/wp-content/uploads/2020/09/AN313-Tomatoes-732x549-Thumb.jpg'),
            ]
            db.session.bulk_save_objects(seed_products)
            db.session.commit()
            print("Sample products added.")
        else:
            print("Products already exist in database.")
    except Exception as e:
        print(f"Error seeding products: {e}")
    
    # Add sample charities
    try:
        if Charity.query.count() == 0:
            sample_charities = [
                Charity(name='Feed the Hungry', description='Providing meals to underprivileged families', website='https://feedthehungry.org'),
                Charity(name='Education for All', description='Supporting education for disadvantaged children', website='https://educationforall.org'),
                Charity(name='Clean Water Foundation', description='Bringing clean water to rural communities', website='https://cleanwater.org'),
                Charity(name='Medical Aid Society', description='Providing healthcare to those in need', website='https://medicalaid.org'),
                Charity(name='Environmental Care', description='Protecting our environment for future generations', website='https://environmentalcare.org'),
            ]
            db.session.bulk_save_objects(sample_charities)
            db.session.commit()
            print("Sample charities added.")
        else:
            print("Charities already exist in database.")
    except Exception as e:
        print(f"Error seeding charities: {e}")

def get_cart():
    return session.get('cart', {})

def save_cart(cart):
    session['cart'] = cart
    session.modified = True

def cart_items_details():
    cart = get_cart()
    items = []
    total = 0.0
    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if not product:
            continue
        subtotal = product.price * qty
        total += subtotal
        items.append({'product': product, 'qty': qty, 'subtotal': subtotal})
    return items, total

def get_wishlist_products(user_id):
    """Get all products in user's wishlist"""
    wishlist_items = Wishlist.query.filter_by(user_id=user_id).all()
    products = []
    for item in wishlist_items:
        product = Product.query.get(item.product_id)
        if product:
            products.append(product)
    return products

# -------------------- Storefront Routes --------------------
@app.route('/')
@app.route('/products')
def index():
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f'%{q}%'))
    if category:
        query = query.filter(Product.category == category)
    categories = [c[0] for c in db.session.query(Product.category).distinct().all()]
    products = query.order_by(Product.created_at.desc()).all()
    
    # Get user's wishlist if logged in
    user_wishlist = []
    if 'user_id' in session:
        user_wishlist = [item.product_id for item in Wishlist.query.filter_by(user_id=session['user_id']).all()]
    
    return render_template('index.html', products=products, q=q, category=category, categories=categories, user_wishlist=user_wishlist)

@app.route('/product/<int:pid>')
def product_detail(pid):
    product = Product.query.get_or_404(pid)
    in_wishlist = False
    if 'user_id' in session:
        in_wishlist = bool(Wishlist.query.filter_by(user_id=session['user_id'], product_id=pid).first())
    return render_template('product_detail.html', product=product, in_wishlist=in_wishlist)

# -------------------- Cart (Authentication Required) --------------------
@app.route('/cart')
@login_required
def cart_view():
    items, total = cart_items_details()
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add/<int:pid>', methods=['POST'])
@login_required
def add_to_cart(pid):
    product = Product.query.get_or_404(pid)
    qty = int(request.form.get('quantity', request.form.get('qty', 1)))
    cart = get_cart()
    cart[str(pid)] = cart.get(str(pid), 0) + max(qty, 1)
    save_cart(cart)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'product_name': product.name,
            'cart_count': len(cart)
        })
    flash(f'Added {product.name} to cart.', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/cart/remove/<int:pid>', methods=['POST'])
@login_required
def remove_from_cart(pid):
    cart = get_cart()
    if str(pid) in cart:
        del cart[str(pid)]
        save_cart(cart)
        flash('Item removed from cart.', 'info')
    return redirect(url_for('cart_view'))

@app.route('/cart/update/<int:pid>', methods=['POST'])
@login_required
def update_cart(pid):
    qty = int(request.form.get('quantity', 1))
    cart = get_cart()
    if qty > 0:
        cart[str(pid)] = qty
    elif str(pid) in cart:
        del cart[str(pid)]
    save_cart(cart)
    return redirect(url_for('cart_view'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    items, total = cart_items_details()
    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('index'))
    
    # Get active charities for donation selection
    charities = Charity.query.filter_by(active=True).all()
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        
        # Handle donation
        donation_amount = float(request.form.get('donation_amount', 0))
        charity_id = request.form.get('charity_id', '')
        charity_name = ''
        
        if donation_amount > 0 and charity_id:
            charity = Charity.query.get(charity_id)
            if charity:
                charity_name = charity.name
        
        if not (name and email and address):
            flash('Please fill all required fields.', 'warning')
            return redirect(url_for('checkout'))
        
        final_total = total + donation_amount
        
        order = Order(
            customer_name=name, 
            customer_email=email, 
            address=address, 
            total_amount=final_total,
            donation_amount=donation_amount,
            charity_name=charity_name
        )
        db.session.add(order)
        db.session.commit()
        
        for it in items:
            db.session.add(OrderItem(
                order_id=order.id, 
                product_id=it['product'].id, 
                quantity=it['qty'], 
                unit_price=it['product'].price
            ))
        db.session.commit()
        
        session['cart'] = {}  # clear cart
        
        success_message = f'Thank you! Order #{order.id} placed successfully.'
        if donation_amount > 0:
            success_message += f' Your donation of ₹{donation_amount} to {charity_name} is appreciated!'
        
        flash(success_message, 'success')
        return redirect(url_for('index'))
    
    return render_template('checkout.html', items=items, total=total, charities=charities)

@app.route('/cart/share')
@login_required
def share_cart():
    cart = get_cart()
    if not cart:
        flash("Your cart is empty.", "warning")
        return redirect(url_for('cart_view'))
    token = str(uuid.uuid4())
    shared_carts[token] = cart
    share_url = url_for('load_shared_cart', token=token, _external=True)
    flash(f"Share your cart with this link: {share_url}", "info")
    return redirect(url_for('cart_view'))

@app.route('/cart/share/<token>')
@login_required
def load_shared_cart(token):
    cart = shared_carts.get(token)
    if not cart:
        flash("Shared cart not found or expired.", "danger")
        return redirect(url_for('cart_view'))
    save_cart(cart)
    flash("Shared cart loaded.", "success")
    return redirect(url_for('cart_view'))

# -------------------- Wishlist Routes --------------------
@app.route('/wishlist')
@login_required
def wishlist():
    products = get_wishlist_products(session['user_id'])
    return render_template('wishlist.html', products=products)

@app.route('/wishlist/add/<int:pid>', methods=['POST'])
@login_required
def add_to_wishlist(pid):
    product = Product.query.get_or_404(pid)
    user_id = session['user_id']
    
    # Check if already in wishlist
    existing = Wishlist.query.filter_by(user_id=user_id, product_id=pid).first()
    if existing:
        flash(f'{product.name} is already in your wishlist.', 'info')
    else:
        wishlist_item = Wishlist(user_id=user_id, product_id=pid)
        db.session.add(wishlist_item)
        db.session.commit()
        flash(f'Added {product.name} to your wishlist.', 'success')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Added to wishlist'})
    
    return redirect(request.referrer or url_for('index'))

@app.route('/wishlist/remove/<int:pid>', methods=['POST'])
@login_required
def remove_from_wishlist(pid):
    user_id = session['user_id']
    wishlist_item = Wishlist.query.filter_by(user_id=user_id, product_id=pid).first()
    
    if wishlist_item:
        product = Product.query.get(pid)
        db.session.delete(wishlist_item)
        db.session.commit()
        flash(f'Removed {product.name if product else "item"} from your wishlist.', 'info')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': 'Removed from wishlist'})
    
    return redirect(request.referrer or url_for('wishlist'))

@app.route('/wishlist/share')
@login_required
def share_wishlist():
    user_id = session['user_id']
    wishlist_products = get_wishlist_products(user_id)
    
    if not wishlist_products:
        flash("Your wishlist is empty.", "warning")
        return redirect(url_for('wishlist'))
    
    # Create wishlist data
    wishlist_data = {
        'user_name': session.get('user', 'Someone'),
        'products': [{'id': p.id, 'name': p.name, 'price': p.price} for p in wishlist_products]
    }
    
    token = str(uuid.uuid4())
    shared_wishlist = SharedWishlist(
        token=token,
        user_id=user_id,
        wishlist_data=json.dumps(wishlist_data)
    )
    db.session.add(shared_wishlist)
    db.session.commit()
    
    share_url = url_for('view_shared_wishlist', token=token, _external=True)
    flash(f"Share your wishlist with this link: {share_url}", "info")
    return redirect(url_for('wishlist'))

@app.route('/wishlist/shared/<token>')
def view_shared_wishlist(token):
    shared_wishlist = SharedWishlist.query.filter_by(token=token).first()
    if not shared_wishlist:
        flash("Shared wishlist not found or expired.", "danger")
        return redirect(url_for('index'))
    
    wishlist_data = json.loads(shared_wishlist.wishlist_data)
    products = []
    
    for product_info in wishlist_data['products']:
        product = Product.query.get(product_info['id'])
        if product:
            products.append(product)
    
    return render_template('shared_wishlist.html', 
                         products=products, 
                         owner_name=wishlist_data['user_name'],
                         shared_date=shared_wishlist.created_at)

@app.route('/wishlist/add_to_cart/<int:pid>', methods=['POST'])
@login_required
def add_wishlist_to_cart(pid):
    """Add a wishlist item to cart and optionally remove from wishlist"""
    product = Product.query.get_or_404(pid)
    
    # Add to cart
    cart = get_cart()
    cart[str(pid)] = cart.get(str(pid), 0) + 1
    save_cart(cart)
    
    # Remove from wishlist if requested
    remove_from_wishlist_flag = request.form.get('remove_from_wishlist') == 'true'
    if remove_from_wishlist_flag:
        user_id = session['user_id']
        wishlist_item = Wishlist.query.filter_by(user_id=user_id, product_id=pid).first()
        if wishlist_item:
            db.session.delete(wishlist_item)
            db.session.commit()
    
    flash(f'Added {product.name} to cart.', 'success')
    return redirect(url_for('wishlist'))

@app.route('/wishlist/clear', methods=['POST'])
@login_required
def clear_wishlist():
    """Clear entire wishlist for current user"""
    user_id = session['user_id']
    wishlist_items = Wishlist.query.filter_by(user_id=user_id).all()
    
    for item in wishlist_items:
        db.session.delete(item)
    
    db.session.commit()
    flash("Wishlist cleared successfully.", "success")
    return redirect(url_for('wishlist'))

# -------------------- User Auth --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not is_valid_email(email):
            flash("Please enter a valid email.", "danger")
            return redirect(url_for('login'))

        if not password:
            flash("Password is required.", "danger")
            return redirect(url_for('login'))

        user = User.query.filter_by(email=email).first()

        if user:
            if user.check_password(password):
                session['user_id'] = user.id
                session['user'] = user.name
                flash(f"Welcome back, {user.name}!", "success")
                
                # Redirect to next URL if it exists
                next_url = session.pop('next_url', None)
                if next_url:
                    return redirect(next_url)
                return redirect(url_for('index'))
            else:
                flash("Invalid password. Please try again.", "danger")
                return redirect(url_for('login'))
        else:
            flash("Account not found. Please sign up first.", "warning")
            return redirect(url_for('signup', email=email))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        address = request.form.get('address', '').strip()
        contact_number = request.form.get('contact_number', '').strip()

        if not all([name, email, password, address, contact_number]):
            flash("All fields are required.", "danger")
            return redirect(url_for('signup'))

        if not is_valid_email(email):
            flash("Please enter a valid email.", "danger")
            return redirect(url_for('signup'))

        if not is_strong_password(password):
            flash("Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character, and be at least 8 characters long.", "danger")
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists. Please login instead.", "warning")
            return redirect(url_for('login'))

        try:
            new_user = User(
                name=name,
                username=email,
                email=email,
                address=address,
                contact_number=contact_number
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash("Account created successfully! Please login with your credentials.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash("An error occurred while creating your account. Please try again.", "danger")
            return redirect(url_for('signup'))

    email = request.args.get('email', '')
    return render_template('signup.html', email=email)

@app.route('/login_signup', methods=['GET', 'POST'])
def login_signup():
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user', None)
    session.pop('next_url', None)
    flash("Logged out successfully!", "info")
    return redirect(url_for('index'))

# -------------------- API --------------------
@app.route('/api/products')
def api_products():
    products = Product.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'price': p.price,
        'image_url': p.image_url,
        'category': p.category,
        'stock': p.stock,
    } for p in products])

# -------------------- Run App --------------------
if __name__ == '__main__':
    app.secret_key = app.config['SECRET_KEY']
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)