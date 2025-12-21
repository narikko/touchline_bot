# ⚽ Touchline - Discord Trading Card Bot

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED?logo=docker&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-red)
![AWS](https://img.shields.io/badge/Deployment-AWS-FF9900?logo=amazonaws&logoColor=white)

**Touchline** is a scalable, persistent trading card game (TCG) and economy bot for Discord. It allows users to collect, trade, and manage a team of soccer players in a global economy.

Unlike simple JSON-based bots, Touchline utilizes a **relational database (PostgreSQL)** with strict transaction management to ensure a glitch-free economy. The project was engineered to simulate professional production environments, utilizing Docker for consistency and CI/CD pipelines for automated testing.

## Key Features

### Robust Economy & Gacha
- **ACID-Compliant Transactions:** Built with **SQLAlchemy** to handle concurrent user trades and currency exchanges without race conditions.
- **Dynamic Inventory:** Support for thousands of unique player cards with varying rarities (Common to Legend).
- **Duplicate Logic:** Automatic duplicate detection that converts repeated pulls into currency based on "Board" upgrade levels.

### Transfer Market & Upgrades
- **Real-Time Market:** Users can list players for sale.
- **Club Upgrades:** A progression system where users invest coins to upgrade their facilities:
  - **🏟️ Stadium:** Increases chance of rolling players from your favorite club.
  - **👔 Board:** Boosts passive income and sales revenue.
  - **🏋️‍♂️ Training Facility:** Increases the rating value of your squad.
  - **📜 Transfer Market:** Reduces the wait time for market sales (from days to hours).
  - **🔭 Scout Network:** Expands your shortlist capacity to track target players.

### Technical Architecture
- **Service-Oriented Design:** Business logic is strictly decoupled from Discord UI (Cogs) using dedicated Service classes (e.g., `GachaService`, `UpgradeService`), ensuring high testability.
- **Infrastructure as Code:** Fully containerized using **Docker** and **Docker Compose**, guaranteeing environment parity between local development and the production server.
- **PostgreSQL Backend:** Utilizes `asyncpg` for high-performance asynchronous database operations.

## Local Setup & Installation

To run this bot locally for development:

### 1. Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- A Discord Bot Token from the [Developer Portal](https://discord.com/developers/applications).

### 2. Clone the Repository
```bash
git clone [https://github.com/narikko/Touchline.git](https://github.com/narikko/Touchline.git)
cd Touchline
## Credits
- Bot Icon made by [rizal2109] from [www.flaticon.com](https://www.flaticon.com/)
```
### Credits
- Bot Icon made by [rizal2109] from www.flaticon.com
- Player data sourced from public football datasets (SoFIFA).
