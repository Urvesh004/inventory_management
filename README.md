# InvenTrack — Inventory Management System

A Streamlit-based inventory management application with user authentication, role-based permissions, and full CRUD flows for products plus sales/purchases tracking and analytics.

## Features

- **Authentication** (SQLite-backed)
- **Role-based permissions** (admin vs staff)
- **Dashboard analytics**: stock levels, low-stock alerts, recent activity, revenue charts
- **Products**: add/edit/delete products, SKU + category management
- **Sales**: record sales and auto-decrement stock
- **Purchases**: record purchases and auto-increment stock
- **Reports**: revenue and inventory analytics (module-driven)
- **Activity Logs**: filter by user/action/module
- **Staff Access**: manage users and permissions (admin-only)

## Tech Stack

- Python
- Streamlit
- SQLite

## Getting Started

### 1) Run the app

```bash
streamlit run main.py
```

### 2) Default admin credentials

On first run, the database initializer creates a default admin user:

- **Username:** `admin`
- **Password:** `admin123`

## Project Structure

Key files:

- `main.py` — Streamlit entrypoint (login, sidebar navigation, routing)
- `database.py` — SQLite schema + authentication + permission helpers
- `dashboard.py` — Dashboard UI and analytics
- `products.py` — Product management UI
- `sales.py` — Sales UI
- `purcheses.py` — Purchases UI (note: filename is spelled this way in the repo)
- `reports.py` — Reports UI
- `logs.py` — Activity log UI
- `staff.py` — Staff/user & permissions UI (admin)
- `icons/` — UI icons used in the app

## Database

- SQLite database file: `inventory.db`
- Tables include: `users`, `permissions`, `products`, `sales`, `purchases`, `logs`

## Notes / Caveats

- `purcheses.py` is spelled `purcheses` (matching the existing import in `main.py`).

## License

Add your project license here (e.g., MIT).

