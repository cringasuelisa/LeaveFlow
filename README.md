# LeaveFlow

Aplicatie web pentru gestionarea cererilor de concediu intr-o organizatie.

**Live:** <https://leaveflow-yx0s.onrender.com/leaves/>

## Stack

- Django 4.2 + Bootstrap 5
- PostgreSQL (productie) / SQLite (local)
- Cloudinary - stocare semnaturi si atasamente
- Resend - notificari email
- Render.com - hosting

## Rulare locala

```bash
git clone https://github.com/cringasuelisa/LeaveFlow.git
cd LeaveFlow

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# editeaza .env si pune DJANGO_SECRET_KEY si (optional) cheile Cloudinary/Resend

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Aplicatia ruleaza la <http://127.0.0.1:8000/>.

## Variabile de mediu

Toate variabilele sunt in `.env.example`. Cele necesare:

| Variabila | Rol |
|-----------|-----|
| `DJANGO_SECRET_KEY` | Cheia Django |
| `DJANGO_DEBUG` | True/False |
| `DJANGO_ALLOWED_HOSTS` | Hostnames permise |
| `DATABASE_URL` | Postgres URL (optional local) |
| `CLOUDINARY_CLOUD_NAME` / `_API_KEY` / `_API_SECRET` | Stocare fisiere |
| `RESEND_API_KEY` | Trimitere mailuri |
| `DEFAULT_FROM_EMAIL` | Adresa expeditor |

## Deploy pe Render

Proiectul include `render.yaml` (Blueprint). Pasii:

1. Cont pe <https://render.com> conectat la GitHub
2. New + → Blueprint → selecteaza repo-ul
3. Completeaza in panoul Render variabilele Cloudinary + Resend (cele cu `sync: false` din yaml)
4. Apply
