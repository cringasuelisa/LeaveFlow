# LeaveFlow

Aplicatie web pentru gestionarea cererilor de concediu intr-o organizatie. Proiect
academic care acopera autentificare, roluri, persistenta in PostgreSQL, integrari
cu doua servicii cloud (Cloudinary + Resend) si publicare pe Render.com.

> Live: `https://leaveflow.onrender.com` (de adaugat dupa deploy)
> Repo: `https://github.com/<utilizator>/leaveflow` (de adaugat dupa push)

## Cuprins

1. Stack tehnologic
2. Functionalitati
3. Workflow utilizator
4. Rulare locala
5. Variabile de mediu
6. Conturi cloud (Cloudinary, Resend)
7. Publicare pe GitHub
8. Publicare pe Render
9. Capturi de ecran
10. Structura proiectului
11. Script video de prezentare (5 minute)

---

## 1. Stack tehnologic

- **Backend**: Django 4.2 LTS, Python 3.9+
- **Templating**: Django Templates + Bootstrap 5 + Bootstrap Icons
- **Baza de date**: PostgreSQL (productie), SQLite (dezvoltare)
- **Autentificare**: `django.contrib.auth` cu `CustomUser` (rol)
- **Stocare fisiere**: Cloudinary (semnaturi, atasamente)
- **Email**: Resend prin SMTP
- **Static files**: Whitenoise (servire eficienta in productie)
- **PDF**: ReportLab pentru generarea cererii oficiale
- **Hosting**: Render.com (web service + Postgres)
- **Variabile de mediu**: python-dotenv (`.env` local) + panoul Render

## 2. Functionalitati

| Categorie | Functionalitate |
|-----------|-----------------|
| Auth | Inregistrare, login, logout, persistenta sesiune 14 zile |
| Roluri | Angajat, Manager, Admin (acces diferentiat) |
| Cereri | Creare, listare, filtrare dupa status, detaliu |
| Atasamente | Upload optional document justificativ -> Cloudinary |
| Email | Notificare manageri la cerere noua, notificare angajat la decizie |
| Aprobare | Manager aproba cu semnatura desenata in canvas SAU upload imagine |
| Respingere | Manager respinge cu obligativitatea unei note explicative |
| Document oficial | Pagina printabila tip cerere, cu antet si semnatura |
| Export PDF | Descarcare PDF al cererii aprobate (ReportLab) |
| Admin | Django admin pentru utilizatori, cereri si semnaturi |

## 3. Workflow utilizator

```
ANGAJAT                                MANAGER
  |                                       |
  | 1. Login                              |
  | 2. Completeaza cerere                 |
  |    + atasament optional               |
  |    -> salvata cu status PENDING       |
  | 3. EMAIL automat -> manager  ====>    | 4. Login -> dashboard cu pending
  |                                       | 5. Deschide cererea
  |                                       | 6a. Aproba + semneaza (canvas/upload)
  |                                       |     -> semnatura salvata in Cloudinary
  |                                       | 6b. SAU Respinge cu motiv
  |    <==== EMAIL automat               | 7. Notificare angajat
  | 8. Vede statusul actualizat           |
  | 9. Daca e aprobat:                    |
  |    - vede pagina document oficial     |
  |    - descarca PDF                     |
```

## 4. Rulare locala

```bash
# 1. Cloneaza
git clone https://github.com/<utilizator>/leaveflow.git
cd leaveflow

# 2. Virtual environment
python3 -m venv .venv
source .venv/bin/activate            # macOS/Linux
# .venv\Scripts\activate            # Windows PowerShell

# 3. Dependinte
pip install --upgrade pip
pip install -r requirements.txt

# 4. Variabile de mediu
cp .env.example .env
# Editeaza .env si completeaza DJANGO_SECRET_KEY (orice string lung).
# Cheile Cloudinary/Resend sunt optionale local - aplicatia merge si fara ele
# (semnaturile se salveaza local, mailurile apar in consola).

# 5. Migratii + superuser
python manage.py migrate
python manage.py createsuperuser

# 6. Pornire
python manage.py runserver
```

Aplicatia ruleaza la `http://127.0.0.1:8000/`. Te poti loga cu superuserul, sau
poti crea un cont angajat la `/leaves/register/` si unul de manager.

## 5. Variabile de mediu

Toate variabilele sunt centralizate in `.env.example`:

| Variabila | Rol | Necesara |
|-----------|-----|----------|
| `DJANGO_SECRET_KEY` | Cheia Django | Da |
| `DJANGO_DEBUG` | `True` local, `False` productie | Da |
| `DJANGO_ALLOWED_HOSTS` | Hostnames permise | Da in productie |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origini CSRF | In productie |
| `DATABASE_URL` | URL Postgres (`postgres://...`) | In productie; gol -> SQLite |
| `DATABASE_SSL` | `True` pentru Render Postgres | In productie |
| `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` | Stocare fisiere | Recomandat |
| `RESEND_API_KEY` | Trimitere mailuri | Recomandat |
| `DEFAULT_FROM_EMAIL` | Adresa expeditor | Recomandat |

## 6. Conturi cloud

### Cloudinary (semnaturi si atasamente)

1. Creeaza un cont gratuit pe <https://cloudinary.com>
2. In Dashboard -> "Account Details" copiaza **Cloud name**, **API Key**, **API Secret**
3. Pune-le in `.env` (local) si in Environment Variables al serviciului Render

### Resend (email)

1. Creeaza cont pe <https://resend.com>
2. In meniul "API Keys" creeaza o cheie noua si copiaz-o
3. Adresa de expeditor: poti folosi `onboarding@resend.dev` pentru teste sau
   un domeniu propriu verificat (recomandat la prezentare)
4. Adauga `RESEND_API_KEY` si `DEFAULT_FROM_EMAIL` in `.env` si in Render

### Render (hosting)

1. Cont gratuit pe <https://render.com>
2. Conecteaza GitHub-ul tau
3. Vezi sectiunea "Publicare pe Render" mai jos

## 7. Publicare pe GitHub

```bash
cd leaveflow

git init
git add .
git commit -m "Initial commit: LeaveFlow scaffold"

# Creeaza un repo gol pe GitHub (fara README/license/gitignore - le ai deja)
# Apoi leaga remote-ul:
git branch -M main
git remote add origin https://github.com/<utilizator>/leaveflow.git
git push -u origin main
```

> Atentie: `.env` e in `.gitignore` - **nu** e push-uit. Doar `.env.example` ajunge in repo.

## 8. Publicare pe Render

Optiunea cea mai simpla: **Blueprint** (citeste `render.yaml` automat).

1. Login pe <https://dashboard.render.com>
2. Click pe **New +** -> **Blueprint** -> selecteaza repo-ul `leaveflow`
3. Render detecteaza `render.yaml` si creeaza:
   - un serviciu web `leaveflow`
   - o baza de date `leaveflow-db` (Postgres free)
4. La sectiunea **Environment** completeaza variabilele care au `sync: false`:
   `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`,
   `RESEND_API_KEY`, `DEFAULT_FROM_EMAIL`
5. Click **Apply**

Render va rula:
1. `pip install -r requirements.txt`
2. `python manage.py collectstatic --no-input`
3. `python manage.py migrate --no-input`
4. `gunicorn leaveflow.wsgi:application`

Dupa primul deploy reusit:

```bash
# Creeaza un superuser direct pe server (din Render -> Shell)
python manage.py createsuperuser
```

Aplicatia va fi accesibila la `https://leaveflow.onrender.com` (sau alt subdomeniu).

> **Tip**: Free tier-ul Render hiberneaza serviciul dupa 15 minute fara trafic.
> La prezentare, deschide aplicatia cu 1 minut inainte ca sa fie "trezita".

## 9. Capturi de ecran

Pentru documentatie/prezentare adauga in folderul `docs/screenshots/` urmatoarele
capturi (numele indica fisierul recomandat):

1. `01_login.png` — pagina de login
2. `02_register.png` — formular inregistrare cu rol
3. `03_dashboard_employee.png` — dashboard angajat cu statistici
4. `04_leave_form.png` — formular cerere noua de concediu
5. `05_leave_detail_pending.png` — cerere in asteptare (vedere angajat)
6. `06_email_new_request.png` — captura email primit de manager
7. `07_dashboard_manager.png` — dashboard manager cu cereri pending
8. `08_approve_canvas.png` — pagina aprobare cu semnatura desenata in canvas
9. `09_approve_upload.png` — pagina aprobare cu upload imagine semnatura
10. `10_leave_detail_approved.png` — cerere aprobata cu semnatura vizibila
11. `11_email_decision.png` — captura email primit de angajat la aprobare
12. `12_document_official.png` — pagina document oficial (printabila)
13. `13_pdf_export.png` — PDF generat
14. `14_admin.png` — panoul Django admin
15. `15_render_dashboard.png` — Render cu serviciul live
16. `16_cloudinary_assets.png` — semnaturi listate in Cloudinary
17. `17_resend_logs.png` — log-uri trimitere email in Resend

## 10. Structura proiectului

```
LeaveFlow/
├── manage.py
├── requirements.txt
├── runtime.txt              # versiune Python pentru Render
├── Procfile                 # start command alternativ
├── build.sh                 # script build Render
├── render.yaml              # Blueprint Render (1-click deploy)
├── .env.example
├── .gitignore
├── README.md
├── leaveflow/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── leaves/
│   ├── models.py            # CustomUser, LeaveRequest, Signature
│   ├── forms.py             # RegisterForm, LeaveRequestForm, ApprovalForm, RejectionForm
│   ├── views.py             # CBV: Dashboard, CRUD cereri, Approve/Reject, PDF
│   ├── urls.py
│   ├── admin.py
│   ├── emails.py            # helperi pentru notificari
│   └── migrations/
└── templates/
    ├── base.html
    ├── registration/
    │   ├── login.html
    │   ├── register.html
    │   └── logged_out.html
    ├── leaves/
    │   ├── _status_badge.html
    │   ├── dashboard_employee.html
    │   ├── dashboard_manager.html
    │   ├── leave_form.html
    │   ├── leave_list.html
    │   ├── leave_detail.html
    │   ├── leave_approve.html
    │   ├── leave_reject.html
    │   └── leave_document.html
    └── emails/
        ├── new_request.html / .txt
        └── decision.html / .txt
```

## 11. Script video prezentare (~5 minute)

> **Pregatire**: ai gata 2 conturi (1 angajat, 1 manager) si o cerere noua de
> facut. Deschide in 3 tab-uri: aplicatia, Cloudinary, Resend (pentru log).

| Sectiune | Durata | Spune si arata |
|----------|-------:|---------------|
| Intro | 0:30 | "LeaveFlow este o aplicatie pentru gestionarea cererilor de concediu, construita pe Django + Postgres + Bootstrap 5, cu integrari Cloudinary si Resend, publicata pe Render." Arata pagina live. |
| Stack si arhitectura | 0:30 | Arata `README.md` -> sectiunile Stack si Workflow. |
| Inregistrare angajat | 0:30 | Mergi la `/leaves/register/`, creezi cont angajat. Subliniaza alegerea rolului. |
| Trimitere cerere | 0:45 | Login angajat, "Cerere noua", completezi tip + perioada + motiv + atasament. Trimiti. Apare pe dashboard cu status PENDING. |
| Email manager | 0:30 | Arata mailul primit (Inbox sau Resend dashboard -> Logs). |
| Aprobare cu semnatura | 0:45 | Login manager (alt browser/incognito), deschizi cererea, dai Aproba, demonstrezi canvas-ul: semnezi cu mouse-ul, trimiti. |
| Cloudinary | 0:20 | Arata in Cloudinary semnatura urcata. |
| Email angajat | 0:20 | Inapoi la angajat, arati emailul primit. |
| Document si PDF | 0:30 | Pe cererea aprobata, deschizi "Document oficial", apoi descarci PDF-ul. |
| Admin si concluzie | 0:20 | Scurt: arata `/admin/` cu utilizatorii si cererile. Multumesti. |

---

**Licenta**: MIT - proiect academic.
