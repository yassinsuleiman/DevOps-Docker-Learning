# 🐳 Docker Multi-Container Challenge — Flask + Redis + NGINX

This project is the outcome of the **CoderCo Containers Challenge** — where I built, debugged, and scaled a **multi-container application** from scratch. It may look like a simple counter app, but under the hood it demonstrates many **core DevOps concepts**: containerization, persistence, configuration management, scaling, and load balancing.

This README is written to **showcase my work to recruiters and hiring managers**. It documents not just what I built, but also what I learned and how I solved real-world problems along the way.

---

## 🎯 The Challenge

**Objective:**

* Create a multi-container application using **Flask** + **Redis**
* Flask has two routes:

  * `/` → Welcome message
  * `/count` → Increments and displays a visit count stored in Redis
* Dockerize both services and orchestrate them with Docker Compose

**Bonus goals:**

* ✅ Persistent storage for Redis (volumes)
* ✅ Use environment variables for flexibility
* ✅ Scale Flask instances & load balance with NGINX

---

## 🛠 Tech Stack

* **Python Flask** → web framework
* **Redis** → in-memory key-value store
* **NGINX** → reverse proxy & load balancer
* **Docker & Docker Compose** → containerization & orchestration

---

## ⚙️ How to Run

```bash
# clone repository
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

# build & start
docker compose up --build
```

Visit:

* [http://localhost:5002/](http://localhost:5002/) → Welcome page
* [http://localhost:5002/count](http://localhost:5002/count) → Counter page

---

## 📸 Screenshots

> (*Replace with your own screenshots to impress recruiters*)

* ✅ Flask welcome page
* ✅ Counter incrementing with refresh
* ✅ Redis CLI showing stored count
* ✅ Docker Desktop view of all running containers

---

## 🚀 Features Implemented

### 1. Base Application

* Flask routes `/` and `/count`
* Redis as key-value store (`INCR hits`)

### 2. Dockerization

* Custom Dockerfile for Flask
* Official Redis image from Docker Hub
* Orchestration with Docker Compose

### 3. Persistent Storage

* Redis volume mounted to `/data`
* Counts persist across container restarts

### 4. Environment Variables

* Flask app reads Redis host & port via env vars
* Configurable in `docker-compose.yml`

### 5. Scaling with NGINX

* Scaled Flask to multiple instances
* NGINX reverse proxy load balances traffic
* Solves port conflicts & enables high availability

---

## 📚 What I Learned

This project was more than just writing YAML and Python — it was about solving **real-world DevOps problems**:

* 🐳 **Docker fundamentals**: building custom images, using official ones
* 📦 **Orchestration with Compose**: linking containers via service names (DNS)
* 💾 **Persistence**: volumes to survive container restarts
* 🔑 **Config management**: moving from hardcoded values → environment variables
* ⚖️ **Scaling & load balancing**: why we need NGINX in front of multiple replicas
* 🛠 **Debugging**: fixed YAML indentation errors, Docker daemon issues, wrong filenames (`app.py` vs `count.py`), Redis not persisting
* 💡 **Production mindset**: thinking beyond “it works on my machine” → resilience & flexibility

---

## 🌱 Future Improvements

* Add frontend (HTML/CSS/JS) for a polished look
* Secure Redis with password/auth
* Deploy to cloud (AWS ECS, Kubernetes, Azure)
* Add CI/CD pipeline with GitHub Actions

---

## 💼 Why This Project Matters

Although this started as a simple counter app, it represents a **production-like pattern**:

* A web service (Flask)
* A database/cache (Redis)
* A reverse proxy (NGINX)
* All managed by Docker Compose with persistence & scaling

It shows I can:

* Build & debug multi-container systems
* Apply DevOps best practices (persistence, scalability, configuration)
* Document & communicate technical projects clearly

For recruiters & hiring managers: this is not just code — it’s a **showcase of my ability to learn, apply, and ship real DevOps projects**.

---

👤 **Author:** Yassin Suleiman
📍 Switzerland | DevOps Engineer
