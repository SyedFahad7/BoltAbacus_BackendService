#!/usr/bin/env python
"""
Setup script for PVP system
This script installs required dependencies and runs migrations
"""

import os
import sys
import subprocess
import django
from django.core.management import execute_from_command_line

def install_dependencies():
    """Install required Python packages"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error installing dependencies: {e}")
        return False
    return True

def run_migrations():
    """Run Django migrations"""
    print("Running migrations...")
    try:
        # Set up Django environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BoltAbacus.settings')
        django.setup()
        
        # Run migrations
        execute_from_command_line(['manage.py', 'makemigrations'])
        execute_from_command_line(['manage.py', 'migrate'])
        
        print("✅ Migrations completed successfully")
        return True
    except Exception as e:
        print(f"❌ Error running migrations: {e}")
        return False

def create_superuser():
    """Create a superuser if needed"""
    print("Creating superuser...")
    try:
        # Check if superuser exists
        from Authentication.models import UserDetails
        if not UserDetails.objects.filter(role='admin').exists():
            print("No admin user found. Creating superuser...")
            # You can customize this or create it manually
            print("Please create an admin user manually using:")
            print("python manage.py createsuperuser")
        else:
            print("✅ Admin user already exists")
        return True
    except Exception as e:
        print(f"❌ Error checking superuser: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up PVP system for BoltAbacus...")
    print("=" * 50)
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Setup failed at dependency installation")
        return False
    
    # Run migrations
    if not run_migrations():
        print("❌ Setup failed at migrations")
        return False
    
    # Create superuser
    if not create_superuser():
        print("❌ Setup failed at superuser creation")
        return False
    
    print("=" * 50)
    print("✅ PVP system setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Start the server: python manage.py runserver")
    print("2. Update frontend API URL to point to this backend")
    print("3. Test PVP functionality")
    print("\n🔧 Available PVP endpoints:")
    print("- POST /createPVPRoom/ - Create a new PVP room")
    print("- POST /joinPVPRoom/ - Join an existing PVP room")
    print("- POST /getPVPRoomDetails/ - Get room details")
    print("- POST /getUserExperience/ - Get user experience points")
    print("- POST /getPVPGameResult/ - Get game results")
    print("\n🌐 WebSocket endpoint:")
    print("- ws://localhost:8000/ws/pvp/{room_id}/")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
