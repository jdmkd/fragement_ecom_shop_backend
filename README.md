# Django E-Commerce Backend

A robust, modular, and secure backend for an e-commerce platform, built with Django and Django REST Framework. This project is designed for scalability, maintainability, and easy integration with modern frontend frameworks.

## Project Structure & App Instructions

This backend is organized into several Django apps, each responsible for a core part of the e-commerce workflow:

- **accounts**: Handles user registration, authentication (JWT), login, logout, password reset, email verification, and user profile management.
- **catalog**: Manages product listings, categories, and product details. Provides endpoints for browsing and searching products.
- **cart**: Manages user shopping carts, including adding, updating, and removing items.
- **orders**: Handles order creation, order history, and order status tracking.
- **payments**: Integrates payment processing (e.g., via third-party gateways) and manages payment records.
- **shipping**: Manages shipping addresses, shipping methods, and delivery tracking.
- **inventory**: Tracks product stock levels and inventory operations.

Each app contains its own models, serializers, views, and urls for modularity and maintainability.

## Features
- Modular Django apps for all core e-commerce functions
- JWT authentication for secure, stateless sessions
- User registration, login, password reset, and email verification
- Product catalog and inventory management
- Cart and order management
- Payment and shipping modules
- CORS and CSRF protection for frontend integration
- Environment-based configuration for all sensitive data

## Getting Started

### Prerequisites
- Python 3.8+
- pip
- (Optional) PostgresQL or MySQL server if using MySQL instead of SQLite

### Installation
1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd shop_backend
   ```
2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Create a `.env` file:**
   Copy the template below and fill in your secrets:
   ```env
   SECRET_KEY=your-secret-key
   DEBUG=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   DB_ENGINE=django.db.backends.sqlite3
   DB_NAME=db.sqlite3
   DB_USER=
   DB_PASSWORD=
   DB_HOST=
   DB_PORT=
   ```
5. **Apply migrations:**
   ```bash
   python manage.py migrate
   ```
6. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```
7. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

## Running Locally
- The backend will be available at `http://127.0.0.1:8000/`
- CORS is configured for local frontend development (`http://localhost:3000`)


## API Guide

### Authentication & User Management (`/accounts/`)
| Endpoint                              | Method | Description                                      | Auth Required |
|----------------------------------------|--------|--------------------------------------------------|---------------|
| `/accounts/register/`                  | POST   | Register a new user (sends OTP to email)         | No            |
| `/accounts/verify-otp/`                | POST   | Verify OTP for account activation                | No            |
| `/accounts/resend-otp/`                | POST   | Resend OTP to user's email                       | No            |
| `/accounts/login/`                     | POST   | Obtain JWT access and refresh tokens             | No            |
| `/accounts/change-password/`           | POST   | Change password (authenticated users)            | Yes           |
| `/accounts/request-reset-email/`       | POST   | Request password reset email                     | No            |
| `/accounts/password-reset-confirm/<uidb64>/<token>/` | POST | Confirm password reset with token                | No            |
| `/accounts/user/`                      | GET    | Get current user details                         | Yes           |
| `/accounts/token/`                     | POST   | Obtain JWT token (username & password)           | No            |
| `/accounts/token/refresh/`             | POST   | Refresh JWT token                                | No            |
| `/accounts/token/verify/`              | POST   | Verify JWT token                                 | No            |

---

### Product Catalog (`/catalog/`)
| Endpoint                | Method | Description                        | Auth Required |
|-------------------------|--------|------------------------------------|---------------|
| `/catalog/products/`    | GET    | List all products                  | No            |
| `/catalog/products/`    | POST   | Create a new product               | Yes (admin)   |
| `/catalog/products/{id}/` | GET  | Retrieve product details           | No            |
| `/catalog/products/{id}/` | PUT  | Update product                     | Yes (admin)   |
| `/catalog/products/{id}/` | PATCH| Partial update product             | Yes (admin)   |
| `/catalog/products/{id}/` | DELETE| Delete product                    | Yes (admin)   |
| `/catalog/categories/`  | GET    | List all categories                | No            |
| `/catalog/categories/`  | POST   | Create a new category              | Yes (admin)   |
| `/catalog/categories/{id}/` | GET| Retrieve category details          | No            |
| `/catalog/categories/{id}/` | PUT| Update category                    | Yes (admin)   |
| `/catalog/categories/{id}/` | PATCH| Partial update category           | Yes (admin)   |
| `/catalog/categories/{id}/` | DELETE| Delete category                  | Yes (admin)   |

---

### Cart, Orders, Payments, Shipping, Inventory

> **Note:** The following apps have their structure in place, but no API endpoints are currently defined. You can extend these apps by adding views and URL patterns as needed.

- **cart**: Intended for shopping cart management.
- **orders**: Intended for order creation and tracking.
- **payments**: Intended for payment processing.
- **shipping**: Intended for shipping address and delivery management.
- **inventory**: Intended for inventory and stock management.

**How to extend:**  
To add or document new endpoints, define your views and add them to the respective `urls.py` file in each app.


## License
This project is licensed under the MIT License.
