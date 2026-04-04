# V-OFFLINE CHAT 🚀

**Live App:** https://nexus-chat-web.onrender.com

A modern, real-time chat platform built with **Django**, **Django Channels**, and a premium **glassmorphism UI**. V-OFFLINE CHAT provides WebSocket-powered messaging, presence tracking, media sharing, emoji reactions, and a responsive 3-panel chat interface designed for production-quality performance and user experience.

---

## ✨ Features

| Feature                              | Status |
| ------------------------------------ | ------ |
| Real-time messaging (WebSocket)      | ✅      |
| Typing indicators                    | ✅      |
| Delivered / Read receipts            | ✅      |
| Emoji picker & reactions             | ✅      |
| Edit & delete messages               | ✅      |
| Media sharing (images, video, docs)  | ✅      |
| Online/offline presence & last seen  | ✅      |
| Dark / Light theme toggle            | ✅      |
| User search & profile viewing        | ✅      |
| Pin & archive conversations          | ✅      |
| Block / unblock users                | ✅      |
| Admin dashboard with analytics       | ✅      |
| Responsive (mobile, tablet, desktop) | ✅      |
| REST API (DRF)                       | ✅      |
| Docker deployment ready              | ✅      |

---

## 🚀 Quick Start (Development)

### Prerequisites

* Python 3.10+
* pip
* Git

### Setup

```bash
# 1. Clone repository
git clone <your-repo-url>
cd SDF

# 2. Create virtual environment
python -m venv venv

# Activate environment
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py makemigrations
python manage.py migrate

# 5. Create superuser
python manage.py createsuperuser

# 6. Start development server
python manage.py runserver
```

Open your browser:

```
http://127.0.0.1:8000
```

> Development mode uses **SQLite** and **InMemoryChannelLayer**, so Redis and PostgreSQL are not required locally.

---

## 🏗️ Project Structure

```
SDF/
├── nexus_chat/              # Django project configuration
│   └── settings/            # base.py, dev.py, prod.py
├── accounts/                # Authentication, profiles, presence
├── chat/                    # Messages, conversations, WebSocket consumers
├── core/                    # Landing page, admin dashboard
├── api/                     # REST API (Django REST Framework)
├── templates/               # HTML templates
├── static/                  # CSS, JavaScript, images
├── media/                   # Uploaded files
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🐳 Docker Deployment

### Build and Run

```bash
docker-compose up --build
```

### Run Migrations Inside Container

```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

---

## 📡 API Endpoints

| Endpoint                            | Method     | Description                |
| ----------------------------------- | ---------- | -------------------------- |
| `/api/users/`                       | GET        | List users                 |
| `/api/users/me/`                    | GET        | Current authenticated user |
| `/api/conversations/`               | GET        | User conversations         |
| `/api/conversations/{id}/messages/` | GET        | Messages of a conversation |
| `/api/messages/`                    | GET / POST | Messages CRUD              |

---

## 🔧 Tech Stack

**Backend**

* Django 4.2
* Django Channels
* Django REST Framework

**WebSocket**

* Channels with InMemory (development)
* Redis channel layer (production)

**Database**

* SQLite (development)
* PostgreSQL (production)

**Frontend**

* HTML5
* CSS3
* Vanilla JavaScript

**Design**

* Custom glassmorphism theme
* Inter font
* Material Icons

**Deployment**

* Docker
* Nginx
* Daphne ASGI server
* Render (cloud hosting)

---

## ⚙️ Production Notes

For production environments:

* Use PostgreSQL instead of SQLite
* Configure Redis for channel layer
* Set `DEBUG=False`
* Configure allowed hosts and environment variables
* Use Nginx for static/media serving

---

## 🧪 Admin Access

After creating a superuser:

```
http://127.0.0.1:8000/admin
```

Admin panel allows:

* User management
* Conversation monitoring
* Analytics overview
* Moderation controls

---

## 📱 Responsiveness

The UI is fully responsive and optimized for:

* Desktop (3-panel layout)
* Tablet
* Mobile (stacked WhatsApp-style interface)

---

## 🔒 Security

* CSRF protection
* Authentication middleware
* Secure file uploads
* Permission-based API access
* WebSocket authentication

---

## 📝 License

This project is licensed under the **MIT License**.

---

## ⭐ Project Goal

V-OFFLINE CHAT is designed as a **portfolio-level, production-ready chat platform** suitable for:

* Major academic projects
* Startup prototypes
* Real-world deployment learning
* Full-stack architecture demonstration

---

## 👨‍💻 Author

**Sai Nikhil**
Computer Science Engineering (Data Science)

---

## 🚀 Future Improvements

* Voice & video calling (WebRTC)
* Screen sharing
* AI assistant integration
* End-to-end encryption
* Progressive Web App (PWA)

---

If you like this project, consider giving it a ⭐ on GitHub.
