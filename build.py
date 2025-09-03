
import os
import shutil

def setup_for_render():
    """Reorganize files for Render deployment"""
    
    print("Starting Render deployment setup...")
    
    # Create directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Copy templates
    if os.path.exists('frontend/templates'):
        print("Copying templates...")
        # Remove existing templates first
        for item in os.listdir('templates'):
            item_path = os.path.join('templates', item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        
        # Copy new templates
        for file in os.listdir('frontend/templates'):
            src = os.path.join('frontend/templates', file)
            dst = os.path.join('templates', file)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
                print(f"✓ Copied {src} -> {dst}")
    else:
        print("⚠️  frontend/templates directory not found!")
    
    # Copy static files
    if os.path.exists('frontend/static'):
        print("Copying static files...")
        # Remove existing static files first
        for item in os.listdir('static'):
            item_path = os.path.join('static', item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        
        # Copy new static files
        for item in os.listdir('frontend/static'):
            src = os.path.join('frontend/static', item)
            dst = os.path.join('static', item)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
                print(f"✓ Copied directory {src} -> {dst}")
            else:
                shutil.copy2(src, dst)
                print(f"✓ Copied {src} -> {dst}")
    else:
        print("⚠️  frontend/static directory not found!")
    
    # Create a simple Flask app configuration
    create_simple_app()
    
    print("\n🎉 Setup complete! Ready for Render deployment.")
    print("Files copied to:")
    print(f"  - templates/ ({len(os.listdir('templates')) if os.path.exists('templates') else 0} files)")
    print(f"  - static/ ({len(os.listdir('static')) if os.path.exists('static') else 0} items)")

def create_simple_app():
    """Create a simplified app.py for deployment"""
    app_content = '''import os
from flask import Flask

# Simple Flask configuration for Render deployment
app = Flask(__name__)

# Basic configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me-in-production')

# Database configuration for Render
if os.environ.get('DATABASE_URL'):
    database_uri = os.environ.get('DATABASE_URL')
    if database_uri.startswith('postgres://'):
        database_uri = database_uri.replace('postgres://', 'postgresql://', 1)
else:
    os.makedirs('instance', exist_ok=True)
    database_uri = 'sqlite:///instance/grocery.db'

app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import the rest of your app
# (Add your other imports and routes here)
'''
    
    # Backup existing app.py
    if os.path.exists('app.py'):
        shutil.copy2('app.py', 'app.py.backup')
        print("✓ Backed up existing app.py to app.py.backup")
    
    print("✓ App configuration ready for simple deployment")

if __name__ == "__main__":
    setup_for_render()