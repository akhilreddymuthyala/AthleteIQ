# AthleteIQ

A Django‑based web application that lets users create prediction rooms, predict match outcomes, and track points.

## Features

- **Sports, Leagues & Matches** – Model hierarchy for sports, leagues and match schedules.
- **Prediction Rooms** – Public or private rooms with invite codes, admin management and member lists.
- **Predictions** – Users submit predictions per match; results are stored and scored.
- **Points & Leaderboard** – Automatic point calculation, streaks and accuracy tracking per room.
- **Announcements & Dynamic Predictions** – Real‑time announcements (e.g., runs, wickets) with a separate dynamic prediction system.
- **Chat** – Simple room‑based messaging.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/akhilreddymuthyala/AthleteIQ.git
cd sports_prediction

# Create a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (see .env.example)
cp .env.example .env
# Edit .env to add your secret key and database credentials

# Apply migrations
python manage.py migrate

# Create a superuser (admin)
python manage.py createsuperuser

# Run the development server
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` in your browser.

## Configuration

The project uses **python‑decouple** for configuration. Key settings in `config/settings.py` are:

- `SECRET_KEY` – secret for Django.
- `DEBUG` – enable/disable debug mode.
- Database credentials (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`).
- Optional webhook URLs for N8N (`N8N_ANNOUNCEMENT_WEBHOOK`, `N8N_RESULT_WEBHOOK`).

## Running Tests

```bash
python manage.py test core
```

## Deployment

The app is ready for deployment on any WSGI‑compatible server (Gunicorn, uWSGI, etc.). Remember to set `DEBUG=False` and configure allowed hosts.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Write tests for your changes.
4. Ensure `python manage.py test` passes.
5. Open a pull request.

## License

This project is licensed under the MIT License – see the `LICENSE` file for details.
