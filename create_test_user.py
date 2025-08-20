#!/usr/bin/env python
import os
import sys
import django
from datetime import date

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BoltAbacus.settings')
django.setup()

from Authentication.models import UserDetails, OrganizationTag
import hashlib

def create_test_user():
    # Create an organization tag first
    org_tag, created = OrganizationTag.objects.get_or_create(
        tagId=1,
        defaults={
            'organizationName': 'Test Organization',
            'tagName': 'BoltAbacus',
            'isIndividualTeacher': False,
            'numberOfTeachers': 1,
            'numberOfStudents': 1,
            'expirationDate': date.today(),
            'totalNumberOfStudents': 1,
            'maxLevel': 10,
            'maxClass': 10
        }
    )
    
    # Create a test admin user
    # Hash the password (simple MD5 for testing)
    password = "admin123"
    hashed_password = hashlib.md5(password.encode()).hexdigest()
    
    user, created = UserDetails.objects.get_or_create(
        email='admin@test.com',
        defaults={
            'firstName': 'Admin',
            'lastName': 'User',
            'phoneNumber': '1234567890',
            'role': 'admin',
            'encryptedPassword': hashed_password,
            'created_date': date.today(),
            'blocked': False,
            'tag': org_tag
        }
    )
    
    if created:
        print(f"Created test user: {user.email}")
        print(f"Password: {password}")
    else:
        print(f"User {user.email} already exists")
    
    # Create a test teacher user
    teacher_password = "teacher123"
    teacher_hashed_password = hashlib.md5(teacher_password.encode()).hexdigest()
    
    teacher, created = UserDetails.objects.get_or_create(
        email='teacher@test.com',
        defaults={
            'firstName': 'Test',
            'lastName': 'Teacher',
            'phoneNumber': '1234567891',
            'role': 'teacher',
            'encryptedPassword': teacher_hashed_password,
            'created_date': date.today(),
            'blocked': False,
            'tag': org_tag
        }
    )
    
    if created:
        print(f"Created test teacher: {teacher.email}")
        print(f"Password: {teacher_password}")
    else:
        print(f"Teacher {teacher.email} already exists")

if __name__ == '__main__':
    create_test_user()
