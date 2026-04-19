# Full Web Project

A comprehensive Django web application with multiple features including user authentication, blog, forum, e-commerce, and RESTful API.

## Features

- **User Authentication**: Register, login, logout, and profile management
- **Blog**: Create, read, update, delete posts with categories and tags
- **Forum**: Create topics, post replies, and discuss in different forums
- **E-commerce**: Product listing, shopping cart, checkout, and order management
- **RESTful API**: Access all features through a RESTful API

## Requirements

- Python 3.8+
- Django 6.0+
- Django REST Framework

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run migrations:
   ```
   python manage.py migrate
   ```
4. Create superuser:
   ```
   python manage.py createsuperuser
   ```
5. Run the development server:
   ```
   python manage.py runserver
   ```

## Usage

- Access the admin panel at `http://localhost:8000/admin/`
- Access the main site at `http://localhost:8000/`
- Access the API at `http://localhost:8000/api/`

## Project Structure

- `accounts/`: User authentication and profile management
- `blog/`: Blog functionality with posts, categories, and tags
- `forum/`: Forum functionality with forums, topics, and posts
- `shop/`: E-commerce functionality with products, cart, and orders
- `api/`: RESTful API implementation
- `fullwebproject/`: Main project configuration
