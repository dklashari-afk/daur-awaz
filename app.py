"""
DAUR AWAZ — Official Citizen Complaint & Progress Portal
Town Committee Daur
Built by DK Lashari

VERSION: 2.0 (PostgreSQL + PWA + Privacy Fixes)
"""

from flask import Flask, render_template_string, request, redirect, session, url_for, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os, uuid, base64, calendar
from collections import OrderedDict
import pytz

# ============================================================
# FLASK APP INIT
# ============================================================
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "daur-awaz-secret-key-2024")

# ============================================================
# PAKISTAN TIME ZONE
# ============================================================
PKT = pytz.timezone('Asia/Karachi')

def get_pkt_time():
    """Returns current time in Pakistan Standard Time (UTC+5)"""
    return datetime.now(PKT)



# ============================================================
# DATABASE CONFIG — PostgreSQL with SSL fix
# ============================================================
DATABASE_URL = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # PostgreSQL (Vercel)
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
else:
    # SQLite (Local development)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "daur_awaz.db")
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH.replace("\\", "/")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# ============================================================
# CONFIG
# ============================================================
CITY_NAME_UR = "دوڑ"
CITY_NAME_EN = "Daur"
COUNCIL_NAME_EN = "Town Committee Daur"
COUNCIL_NAME_UR = "ٹاؤن کمیٹی دوڑ"
CHAIRMAN_NAME = os.environ.get("CHAIRMAN_NAME", "Chairman, Town Committee Daur")
CONTACT_PHONE = os.environ.get("CONTACT_PHONE", "0300-0000000")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "info@daurawaz.gov.pk")
OFFICE_ADDRESS = os.environ.get("OFFICE_ADDRESS", "Town Committee Office, Daur City")

AREAS = ["Daur Main Bazar", "Station Road", "Shahi Bazar", "Bhatti Colony", "Qazi Mohalla", "Other"]
# REMOVED: "Bijli / Street Light" — chairman ka electricity se wasta nahi
CATEGORIES = [
    ("Safai / Kachra", "fa-trash-can"),
    ("Pani ka Masla", "fa-faucet-drip"),
    ("Road / Gali", "fa-road"),
    ("Sewerage", "fa-water"),
    ("Encroachment", "fa-triangle-exclamation"),
    ("Other", "fa-ellipsis"),
]
STATUS_STYLES = {
    "Pending":     {"bg": "bg-amber-50",  "text": "text-amber-700",  "dot": "bg-amber-500",  "ur": "زیر التوا"},
    "In-Progress": {"bg": "bg-blue-50",   "text": "text-blue-700",   "dot": "bg-blue-500",   "ur": "جاری ہے"},
    "Resolved":    {"bg": "bg-emerald-50","text": "text-emerald-700","dot": "bg-emerald-500","ur": "حل ہوگئی"},
}

SEED_ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")
SEED_ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "admin123")

# ============================================================
# MODELS — WITH PKT TIME
# ============================================================
class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tracking_id = db.Column(db.String(24), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    cnic = db.Column(db.String(20))
    category = db.Column(db.String(50))
    location = db.Column(db.String(100))
    description = db.Column(db.Text)
    photo_data = db.Column(db.Text)
    status = db.Column(db.String(20), default="Pending")
    remarks = db.Column(db.Text)
    upvotes = db.Column(db.Integer, default=0)
    user_identifier = db.Column(db.String(100), nullable=False)
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_pkt_time)      # ← PKT TIME
    updated_at = db.Column(db.DateTime, default=get_pkt_time, onupdate=get_pkt_time)  


class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    role = db.Column(db.String(20), default="Assistant")
    created_at = db.Column(db.DateTime, default=get_pkt_time)      # ← 

# ============================================================
# DATABASE INIT (with app context)
# ============================================================
with app.app_context():
    db.create_all()
    if AdminUser.query.count() == 0:
        db.session.add(AdminUser(
            username=SEED_ADMIN_USER,
            password_hash=generate_password_hash(SEED_ADMIN_PASS),
            full_name="Chairman",
            role="Chairman",
        ))
        db.session.commit()

# ============================================================
# PWA MANIFEST & SERVICE WORKER
# ============================================================
@app.route('/manifest.json')
def manifest():
    return app.response_class(
        response='''{
  "name": "Daur Awaz",
  "short_name": "Daur Awaz",
  "description": "Official Citizen Complaint Portal, Town Committee Daur",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0B6E4F",
  "theme_color": "#0B6E4F",
  "orientation": "portrait",
  "icons": [
    {
      "src": "data:image/svg+xml," + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="#0B6E4F"/><circle cx="50" cy="50" r="48" fill="none" stroke="#C9A227" stroke-width="2.5"/><circle cx="50" cy="50" r="41" fill="none" stroke="#C9A227" stroke-width="1"/><path d="M50 22 L54 34 L67 34 L57 42 L61 55 L50 47 L39 55 L43 42 L33 34 L46 34 Z" fill="#C9A227"/><text x="50" y="72" text-anchor="middle" fill="#fff" font-size="13" font-weight="700" font-family="Arial">DAUR</text><text x="50" y="82" text-anchor="middle" fill="#EFE3B8" font-size="6" font-family="Arial">TOWN COMMITTEE</text></svg>'),
      "sizes": "192x192",
      "type": "image/svg+xml"
    }
  ]
}''',
        mimetype='application/json'
    )


@app.route('/service-worker.js')
def service_worker():
    return app.response_class(
        response='''self.addEventListener("install", e => {
  e.waitUntil(
    caches.open("daur-awaz-v1").then(cache => {
      return cache.addAll(["/", "/offline"]);
    })
  );
});
self.addEventListener("fetch", e => {
  e.respondWith(
    caches.match(e.request).then(response => {
      return response || fetch(e.request);
    })
  );
});''',
        mimetype='application/javascript'
    )


@app.route('/offline')
def offline():
    return render_template_string('''
<!DOCTYPE html><html><head><title>Offline</title>
<style>body{font-family:sans-serif;text-align:center;padding:50px;background:#0B6E4F;color:white}</style>
</head><body><h1>📱 Daur Awaz</h1><p>You are offline. Please connect to the internet.</p></body></html>
''')


# ============================================================
# SHARED UI
# ============================================================
HEAD = '''
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="data:image/svg+xml,{emblem_favicon}">
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config={{theme:{{extend:{{colors:{{gov:{{DEFAULT:'#0B6E4F',dark:'#054A35',gold:'#C9A227'}}}}}}}}}}</script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Nastaliq+Urdu:wght@500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css">
<style>
  body{{font-family:'Inter',sans-serif}}
  .urdu{{font-family:'Noto Nastaliq Urdu',serif;line-height:2.1;}}
  .emblem-ring{{background:conic-gradient(from 0deg,#0B6E4F,#C9A227,#0B6E4F);}}
  @media(max-width:640px){{.hero-text{{font-size:1.5rem !important;}} .hide-mobile{{display:none !important;}}}}
</style>
'''

EMBLEM_SVG = """<svg width="{size}" height="{size}" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
<circle cx="50" cy="50" r="48" fill="#0B6E4F"/>
<circle cx="50" cy="50" r="48" fill="none" stroke="#C9A227" stroke-width="2.5"/>
<circle cx="50" cy="50" r="41" fill="none" stroke="#C9A227" stroke-width="1"/>
<path d="M50 22 L54 34 L67 34 L57 42 L61 55 L50 47 L39 55 L43 42 L33 34 L46 34 Z" fill="#C9A227"/>
<text x="50" y="72" text-anchor="middle" fill="#fff" font-size="13" font-weight="700" font-family="Arial">DAUR</text>
<text x="50" y="82" text-anchor="middle" fill="#EFE3B8" font-size="6" font-family="Arial">TOWN COMMITTEE</text>
</svg>"""

def emblem(size=48):
    return EMBLEM_SVG.format(size=size)

def emblem_favicon():
    import urllib.parse
    return urllib.parse.quote(EMBLEM_SVG.format(size=100))

def navbar(active=""):
    def link(href, label_en, label_ur, key):
        cls = "text-gov font-bold" if active == key else "text-gray-600 hover:text-gov"
        return f'<a href="{href}" class="{cls} text-sm transition">{label_en}</a>'
    return f'''
<header class="bg-white border-b sticky top-0 z-50 shadow-sm">
  <div class="bg-gov-dark text-white text-xs py-1.5 text-center px-4">
    <span class="urdu">ٹاؤن کمیٹی دوڑ — سرکاری شہری خدمات پورٹل</span>
    <span class="hidden sm:inline"> &nbsp;•&nbsp; Official Citizen Services Portal, Town Committee Daur</span>
  </div>
  <div class="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex justify-between items-center gap-3">
    <a href="/" class="flex items-center gap-3">
      {emblem(44)}
      <div class="leading-tight">
        <h1 class="font-extrabold text-base sm:text-lg text-gov-dark">Daur Awaz</h1>
        <p class="text-[11px] text-gray-500">{COUNCIL_NAME_EN}</p>
      </div>
    </a>
    <nav class="flex items-center gap-2 sm:gap-4">
      {link('/', 'Home', 'ہوم', 'home')}
      {link('/my-complaints', 'My Complaints', 'میری شکایات', 'my')}
      <a href="/login" class="px-3 sm:px-4 py-2 bg-gov text-white rounded-full text-xs sm:text-sm font-semibold hover:bg-gov-dark transition flex items-center gap-1.5">
        <i class="fa-solid fa-user-shield"></i> <span class="hidden sm:inline">Chairman</span> Login
      </a>
    </nav>
  </div>
</header>
'''

FOOTER = f'''
<footer class="bg-gov-dark text-gray-300 mt-16">
  <div class="max-w-6xl mx-auto px-6 py-10 grid sm:grid-cols-3 gap-8">
    <div>
      <div class="flex items-center gap-2 mb-3">{emblem(34)}<span class="text-white font-bold">Daur Awaz</span></div>
      <p class="text-sm text-gray-400">{COUNCIL_NAME_EN}. An official platform for citizens of Daur to report civic issues directly to the Chairman's office and track resolution progress.</p>
    </div>
    <div>
      <h4 class="text-white font-semibold mb-3 text-sm">Contact / رابطہ</h4>
      <p class="text-sm text-gray-400 mb-1"><i class="fa-solid fa-location-dot w-4"></i> {OFFICE_ADDRESS}</p>
      <p class="text-sm text-gray-400 mb-1"><i class="fa-solid fa-phone w-4"></i> {CONTACT_PHONE}</p>
      <p class="text-sm text-gray-400"><i class="fa-solid fa-envelope w-4"></i> {CONTACT_EMAIL}</p>
    </div>
    <div>
      <h4 class="text-white font-semibold mb-3 text-sm">Office Hours</h4>
      <p class="text-sm text-gray-400 mb-1">Monday – Saturday: 9:00 AM – 4:00 PM</p>
      <p class="text-sm text-gray-400">Friday: 9:00 AM – 12:30 PM</p>
    </div>
  </div>
  <div class="border-t border-white/10 py-4 text-center text-xs text-gray-400">
    © {datetime.now().year} {COUNCIL_NAME_EN} &nbsp;•&nbsp; Platform developed by DK Lashari
  </div>
</footer>
'''

def status_badge(status):
    s = STATUS_STYLES.get(status, STATUS_STYLES["Pending"])
    return f'<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold {s["bg"]} {s["text"]}"><span class="w-1.5 h-1.5 rounded-full {s["dot"]}"></span>{status}</span>'


# ============================================================
# PUBLIC HOME — UPDATED HERO TEXT
# ============================================================
PUBLIC_HTML = '''
<!DOCTYPE html><html lang="en"><head><title>Daur Awaz — Daur City Citizen Complaint Portal</title>{head}
<meta name="description" content="Official citizen complaint portal for Daur city. Report civic issues directly to the Chairman's office and track progress in real time.">
</head><body class="bg-[#F6F8F7]">
{navbar}

<section class="bg-gradient-to-b from-white to-[#F6F8F7] border-b">
  <div class="max-w-6xl mx-auto px-6 py-10 text-center">
    <span class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-gov/10 text-gov text-xs font-bold mb-4">
      <i class="fa-solid fa-shield-halved"></i> Official Government Citizen Service
    </span>
    <!-- UPDATED: "چیئرمین دوڑ تک" + removed "just like Pakistan Citizen Portal" -->
    <h2 class="urdu text-2xl sm:text-3xl text-gov-dark font-bold mb-2 hero-text">آپ کی آواز، براہ راست چیئرمین دوڑ تک</h2>
    <p class="text-gray-600 max-w-2xl mx-auto text-sm sm:text-base">Report civic problems in Daur city — sanitation, water, roads, sewerage — and track their resolution in real time.</p>
  </div>
</section>

<div class="max-w-6xl mx-auto px-4 sm:px-6 py-8 grid lg:grid-cols-3 gap-6">

  <div class="lg:col-span-1 space-y-4">
    <div class="bg-white rounded-2xl p-6 shadow-sm border">
      <h2 class="font-bold text-lg mb-1">شکایت درج کریں</h2>
      <p class="text-sm text-gray-500 mb-5">Register your complaint — it goes straight to the Chairman's dashboard.</p>
      <form method="POST" action="/submit" enctype="multipart/form-data" class="space-y-3.5">
        <input name="name" required placeholder="Aap ka pura naam" class="w-full px-4 py-2.5 rounded-xl bg-gray-50 border text-sm focus:outline-none focus:ring-2 focus:ring-gov/30 focus:border-gov">
        <input name="phone" required placeholder="Phone / WhatsApp number" class="w-full px-4 py-2.5 rounded-xl bg-gray-50 border text-sm focus:outline-none focus:ring-2 focus:ring-gov/30 focus:border-gov">
        <input name="cnic" placeholder="CNIC (optional)" class="w-full px-4 py-2.5 rounded-xl bg-gray-50 border text-sm focus:outline-none focus:ring-2 focus:ring-gov/30 focus:border-gov">
        <select name="location" class="w-full px-4 py-2.5 rounded-xl bg-gray-50 border text-sm">
          {area_options}
        </select>
        <select name="category" class="w-full px-4 py-2.5 rounded-xl bg-gray-50 border text-sm">
          {category_options}
        </select>
        <textarea name="description" required rows="4" placeholder="Masla tafseel se likhen..." class="w-full px-4 py-2.5 rounded-xl bg-gray-50 border text-sm focus:outline-none focus:ring-2 focus:ring-gov/30 focus:border-gov"></textarea>
        <div>
          <label class="text-xs text-gray-500 mb-1 block">Photo attach karein (optional)</label>
          <input type="file" name="photo" accept="image/*" class="w-full text-xs text-gray-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-gov/10 file:text-gov file:text-xs file:font-semibold">
        </div>
        <button class="w-full py-3 bg-gov text-white rounded-xl font-semibold text-sm hover:bg-gov-dark transition flex items-center justify-center gap-2">
          Complaint Submit Karein <i class="fa-solid fa-arrow-right"></i>
        </button>
      </form>
      {success_box}
    </div>

    <div class="bg-gov-dark text-white rounded-2xl p-6">
      <p class="text-xs text-gray-300 mb-3 font-semibold uppercase tracking-wide">Portal Overview</p>
      <div class="grid grid-cols-3 gap-3 text-center">
        <div><p class="text-2xl font-extrabold">{total}</p><p class="text-[11px] text-gray-300">Total</p></div>
        <div><p class="text-2xl font-extrabold text-amber-300">{pending}</p><p class="text-[11px] text-gray-300">Pending</p></div>
        <div><p class="text-2xl font-extrabold text-emerald-300">{resolved}</p><p class="text-[11px] text-gray-300">Resolved</p></div>
      </div>
      <a href="/track" class="mt-4 block text-center text-xs bg-white/10 hover:bg-white/20 rounded-lg py-2 transition">Track your complaint by ID →</a>
    </div>
  </div>

  <div class="lg:col-span-2">
    <div class="flex items-center justify-between mb-4 flex-wrap gap-3">
      <h3 class="font-bold text-lg">Public Complaint Wall — Daur City</h3>
      <form method="GET" action="/" class="flex gap-2">
        <input name="search" placeholder="Search by keyword..." class="px-3 py-2 rounded-lg border text-xs w-40 sm:w-56" value="{search_val}">
        <button class="px-3 py-2 bg-gray-100 rounded-lg text-xs font-semibold border">Search</button>
      </form>
    </div>
    <div class="grid gap-3.5">
      {complaint_cards}
    </div>
  </div>
</div>
{footer}
</body></html>
'''

def complaint_card_html(c, admin_view=False):
    photo_html = ""
    if c.photo_data:
        photo_html = f'<img src="/photo/{c.id}" class="w-full sm:w-28 h-28 object-cover rounded-xl border" alt="Complaint photo">'
    remark_html = ""
    if c.remarks:
        remark_html = f'''<div class="mt-2 text-xs bg-gov/5 border border-gov/15 rounded-lg px-3 py-2 text-gov-dark">
            <i class="fa-solid fa-comment-dots mr-1"></i><b>Chairman's Office:</b> {c.remarks}</div>'''
    return f'''
    <div class="bg-white rounded-2xl p-4 sm:p-5 border shadow-sm flex flex-col sm:flex-row gap-4">
      {photo_html}
      <div class="flex-1">
        <div class="flex gap-2 items-center mb-2 flex-wrap">
          {status_badge(c.status)}
          <span class="text-xs text-gray-500">{c.category} • {c.location} • {c.created_at.strftime('%d %b %Y')}</span>
        </div>
        <p class="font-semibold text-gray-800 text-sm">{c.description[:160]}{'...' if len(c.description or '') > 160 else ''}</p>
        <p class="text-xs text-gray-500 mt-1.5">Tracking ID: <b class="font-mono">{c.tracking_id}</b> • Filed by: {c.name}</p>
        {remark_html}
      </div>
      <div class="text-right flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-2">
        <p class="text-sm font-bold text-gray-700">👍 {c.upvotes}</p>
        <a href="/upvote/{c.id}" class="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-full transition">Upvote</a>
      </div>
    </div>
    '''


@app.route("/")
def home():
    search = request.args.get("search", "").strip()
    q = Complaint.query.filter_by(is_public=True)
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(Complaint.description.ilike(like), Complaint.location.ilike(like), Complaint.tracking_id.ilike(like)))
    complaints = q.order_by(Complaint.created_at.desc()).limit(50).all()

    total = Complaint.query.count()
    resolved = Complaint.query.filter_by(status="Resolved").count()
    pending = Complaint.query.filter_by(status="Pending").count()

    tracking_id = session.pop('tracking_id', None)
    success_box = ""
    if tracking_id:
        success_box = f'''<div class="mt-5 p-4 bg-emerald-50 border border-emerald-200 rounded-xl">
            <p class="text-sm font-bold text-emerald-800"><i class="fa-solid fa-circle-check mr-1"></i> Complaint Darj Ho Gayi!</p>
            <p class="text-xs text-emerald-700 mt-1">Tracking ID: <b class="font-mono">{tracking_id}</b> — is ID ko save kar lein, isse aap apni complaint <a href="/track?id={tracking_id}" class="underline font-semibold">track</a> kar sakte hain.</p></div>'''

    area_options = "".join(f'<option value="{a}">{a}</option>' for a in AREAS)
    category_options = "".join(f'<option value="{c}">{c}</option>' for c, _ in CATEGORIES)
    cards = "".join(complaint_card_html(c) for c in complaints) or '<div class="text-center text-gray-400 py-16 bg-white rounded-2xl border"><i class="fa-solid fa-inbox text-3xl mb-2"></i><p class="text-sm">Koi complaint nahi mili.</p></div>'

    return PUBLIC_HTML.format(
        head=HEAD.format(emblem_favicon=emblem_favicon()),
        navbar=navbar("home"),
        area_options=area_options,
        category_options=category_options,
        success_box=success_box,
        total=total, pending=pending, resolved=resolved,
        search_val=search,
        complaint_cards=cards,
        footer=FOOTER,
    )


@app.route("/submit", methods=["POST"])
def submit():
    tracking = f"DAUR-{datetime.now().year}-{str(uuid.uuid4())[:6].upper()}"
    phone = request.form.get("phone", "").strip()
    user_identifier = phone

    photo_data = None
    file = request.files.get("photo")
    if file and file.filename:
        raw = file.read()
        if len(raw) <= 2 * 1024 * 1024:
            mime = file.mimetype or "image/jpeg"
            photo_data = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

    c = Complaint(
        tracking_id=tracking,
        name=request.form.get("name", "").strip(),
        phone=phone,
        cnic=request.form.get("cnic", "").strip(),
        location=request.form.get("location"),
        category=request.form.get("category"),
        description=request.form.get("description", "").strip(),
        photo_data=photo_data,
        user_identifier=user_identifier,
        is_public=False,
    )
    db.session.add(c)
    db.session.commit()
    session['tracking_id'] = tracking
    return redirect("/")


@app.route("/photo/<int:id>")
def photo(id):
    c = Complaint.query.get_or_404(id)
    if not c.photo_data:
        return "", 404
    header, b64data = c.photo_data.split(",", 1)
    mime = header.split(":")[1].split(";")[0]
    return Response(base64.b64decode(b64data), mimetype=mime)


@app.route("/upvote/<int:id>")
def upvote(id):
    c = Complaint.query.get(id)
    if c:
        c.upvotes += 1
        db.session.commit()
    return redirect(request.referrer or "/")


# ============================================================
# MY COMPLAINTS
# ============================================================
MY_COMPLAINTS_HTML = '''
<!DOCTYPE html><html lang="en"><head><title>My Complaints — Daur Awaz</title>{head}</head>
<body class="bg-[#F6F8F7]">
{navbar}
<div class="max-w-4xl mx-auto px-4 sm:px-6 py-10">
  <h2 class="text-2xl font-bold text-gov-dark mb-2">میری شکایات</h2>
  <p class="text-sm text-gray-500 mb-6">Apni tracking ID ya phone number se apni complaints dekhein.</p>
  
  <form method="GET" action="/my-complaints" class="flex gap-3 mb-8">
    <input name="tracking_id" placeholder="Tracking ID (e.g. DAUR-2026-A1B2C3)" class="flex-1 px-4 py-3 rounded-xl border bg-white text-sm font-mono focus:outline-none focus:ring-2 focus:ring-gov/30">
    <input name="phone" placeholder="Phone number" class="flex-1 px-4 py-3 rounded-xl border bg-white text-sm focus:outline-none focus:ring-2 focus:ring-gov/30">
    <button class="px-5 py-3 bg-gov text-white rounded-xl text-sm font-semibold hover:bg-gov-dark transition">Search</button>
  </form>

  <div class="grid gap-4">
    {complaints}
  </div>
</div>
{footer}
</body></html>
'''

@app.route("/my-complaints")
def my_complaints():
    tracking_id = request.args.get("tracking_id", "").strip()
    phone = request.args.get("phone", "").strip()
    
    q = Complaint.query
    if tracking_id:
        q = q.filter_by(tracking_id=tracking_id)
    elif phone:
        q = q.filter_by(phone=phone)
    else:
        complaints = []
        cards = '<div class="text-center text-gray-400 py-10 bg-white rounded-2xl border"><p class="text-sm">Apni complaint dekhne ke liye tracking ID ya phone number likhein.</p></div>'
        return MY_COMPLAINTS_HTML.format(
            head=HEAD.format(emblem_favicon=emblem_favicon()),
            navbar=navbar("my"),
            complaints=cards,
            footer=FOOTER,
        )
    
    complaints = q.order_by(Complaint.created_at.desc()).all()
    cards = "".join(complaint_card_html(c) for c in complaints) or '<div class="text-center text-gray-400 py-10 bg-white rounded-2xl border"><p class="text-sm">Is ID ya phone se koi complaint nahi mili.</p></div>'
    
    return MY_COMPLAINTS_HTML.format(
        head=HEAD.format(emblem_favicon=emblem_favicon()),
        navbar=navbar("my"),
        complaints=cards,
        footer=FOOTER,
    )


# ============================================================
# TRACK COMPLAINT
# ============================================================
TRACK_HTML = '''
<!DOCTYPE html><html lang="en"><head><title>Track Complaint — Daur Awaz</title>{head}</head>
<body class="bg-[#F6F8F7]">
{navbar}
<div class="max-w-2xl mx-auto px-6 py-12">
  <div class="text-center mb-8">
    <h2 class="urdu text-2xl text-gov-dark font-bold mb-1">اپنی شکایت کی صورتحال دیکھیں</h2>
    <p class="text-gray-500 text-sm">Enter your Tracking ID to see live status and any official response.</p>
  </div>
  <form method="GET" action="/track" class="flex gap-2 mb-8">
    <input name="id" value="{qid}" placeholder="e.g. DAUR-2026-A1B2C3" class="flex-1 px-4 py-3 rounded-xl border bg-white text-sm font-mono focus:outline-none focus:ring-2 focus:ring-gov/30">
    <button class="px-5 py-3 bg-gov text-white rounded-xl text-sm font-semibold hover:bg-gov-dark transition">Track</button>
  </form>
  {result}
</div>
{footer}
</body></html>
'''

def timeline_html(c):
    steps = ["Pending", "In-Progress", "Resolved"]
    idx = steps.index(c.status) if c.status in steps else 0
    dots = ""
    for i, s in enumerate(steps):
        done = i <= idx
        color = "bg-gov text-white" if done else "bg-gray-100 text-gray-400"
        line = "" if i == len(steps) - 1 else f'<div class="flex-1 h-0.5 {"bg-gov" if i < idx else "bg-gray-200"}"></div>'
        dots += f'''<div class="flex items-center flex-1">
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold {color}">{i+1}</div>
            {line}</div>'''
    labels = "".join(f'<span class="flex-1 text-center">{s}</span>' for s in steps)
    return f'<div class="flex items-center mb-2">{dots}</div><div class="flex text-[11px] text-gray-500 font-semibold mb-6">{labels}</div>'

@app.route("/track")
def track():
    qid = request.args.get("id", "").strip()
    result = ""
    if qid:
        c = Complaint.query.filter_by(tracking_id=qid).first()
        if c:
            photo_html = f'<img src="/photo/{c.id}" class="w-full h-48 object-cover rounded-xl border mb-5" alt="Complaint photo">' if c.photo_data else ""
            remark_html = f'''<div class="mt-4 bg-gov/5 border border-gov/15 rounded-xl p-4 text-sm text-gov-dark">
                <b><i class="fa-solid fa-comment-dots mr-1"></i> Chairman's Office Response:</b><p class="mt-1">{c.remarks}</p></div>''' if c.remarks else ""
            result = f'''
            <div class="bg-white rounded-2xl border shadow-sm p-6">
              <div class="flex justify-between items-start mb-5 flex-wrap gap-2">
                <div><p class="text-xs text-gray-400">Tracking ID</p><p class="font-mono font-bold">{c.tracking_id}</p></div>
                {status_badge(c.status)}
              </div>
              {timeline_html(c)}
              {photo_html}
              <p class="text-xs text-gray-400 mb-1">Category / Location</p>
              <p class="text-sm font-semibold mb-4">{c.category} — {c.location}</p>
              <p class="text-xs text-gray-400 mb-1">Description</p>
              <p class="text-sm text-gray-700">{c.description}</p>
              <p class="text-xs text-gray-400 mt-4">Filed on {c.created_at.strftime('%d %b %Y, %I:%M %p')} by {c.name}</p>
              {remark_html}
            </div>'''
        else:
            result = '<div class="text-center text-gray-400 py-10 bg-white rounded-2xl border"><i class="fa-solid fa-magnifying-glass text-2xl mb-2"></i><p class="text-sm">Is ID se koi complaint nahi mili. ID dobara check karein.</p></div>'
    return TRACK_HTML.format(head=HEAD.format(emblem_favicon=emblem_favicon()), navbar=navbar("track"), qid=qid, result=result, footer=FOOTER)


# ============================================================
# CHAIRMAN LOGIN
# ============================================================
ADMIN_LOGIN = '''
<!DOCTYPE html><html lang="en"><head><title>Chairman Login — Daur Awaz</title>{head}</head>
<body class="bg-[#F6F8F7] min-h-screen flex items-center justify-center px-4">
<div class="bg-white rounded-2xl p-8 w-full max-w-sm border shadow-sm">
  <div class="flex justify-center mb-4">{emblem_lg}</div>
  <h1 class="font-bold text-xl text-center text-gov-dark">Chairman Login</h1>
  <p class="text-sm text-gray-500 mb-6 text-center">{council}</p>
  {error}
  <form method="POST" class="space-y-3.5">
    <input name="username" placeholder="Username" class="w-full px-4 py-3 rounded-xl bg-gray-50 border text-sm focus:outline-none focus:ring-2 focus:ring-gov/30">
    <input name="password" type="password" placeholder="Password" class="w-full px-4 py-3 rounded-xl bg-gray-50 border text-sm focus:outline-none focus:ring-2 focus:ring-gov/30">
    <button class="w-full py-3 bg-gov text-white rounded-xl font-semibold hover:bg-gov-dark transition">Login →</button>
  </form>
  <a href="/" class="block text-center text-xs text-gray-400 mt-5 hover:text-gov">← Back to public portal</a>
</div>
</body></html>
'''

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "")
        user = AdminUser.query.filter_by(username=u).first()
        if user and check_password_hash(user.password_hash, p):
            session["admin"] = True
            session["admin_id"] = user.id
            session["admin_username"] = user.username
            session["admin_name"] = user.full_name or user.username
            session["admin_role"] = user.role
            return redirect("/admin")
        error = '<p class="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-4 text-center">Ghalat username ya password.</p>'
    return ADMIN_LOGIN.format(head=HEAD.format(emblem_favicon=emblem_favicon()), emblem_lg=emblem(56), council=COUNCIL_NAME_EN, error=error)


# ============================================================
# CHAIRMAN DASHBOARD
# ============================================================
ADMIN_DASH = '''
<!DOCTYPE html><html lang="en"><head><title>Chairman Dashboard — Daur Awaz</title>{head}</head>
<body class="bg-[#F6F8F7]">
<header class="bg-gov-dark text-white">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex justify-between items-center flex-wrap gap-3">
    <div class="flex items-center gap-3">{emblem_sm}<div><h1 class="font-bold">Chairman Dashboard</h1><p class="text-xs text-gray-300">{council}</p></div></div>
    <div class="flex items-center gap-2 flex-wrap">
      <span class="text-xs text-gray-300 hidden sm:inline"><i class="fa-solid fa-circle-user mr-1"></i>{logged_in_name} ({logged_in_role})</span>
      <a href="/" class="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-full text-xs transition">Public View</a>
      <a href="/admin/reports" class="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-full text-xs transition"><i class="fa-solid fa-chart-column mr-1"></i>Reports</a>
      <a href="/admin/account" class="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-full text-xs transition"><i class="fa-solid fa-key mr-1"></i>My Account</a>
      <a href="/admin/users" class="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-full text-xs transition"><i class="fa-solid fa-users-gear mr-1"></i>Manage Users</a>
      <a href="/logout" class="bg-red-500/90 hover:bg-red-500 px-3 py-1.5 rounded-full text-xs transition">Logout</a>
    </div>
  </div>
</header>

<div class="max-w-6xl mx-auto px-4 sm:px-6 py-6">
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
    <div class="bg-white rounded-xl border p-4"><p class="text-2xl font-extrabold text-gov-dark">{total}</p><p class="text-xs text-gray-500">Total Complaints</p></div>
    <div class="bg-white rounded-xl border p-4"><p class="text-2xl font-extrabold text-amber-600">{pending}</p><p class="text-xs text-gray-500">Pending</p></div>
    <div class="bg-white rounded-xl border p-4"><p class="text-2xl font-extrabold text-blue-600">{inprogress}</p><p class="text-xs text-gray-500">In-Progress</p></div>
    <div class="bg-white rounded-xl border p-4"><p class="text-2xl font-extrabold text-emerald-600">{resolved}</p><p class="text-xs text-gray-500">Resolved</p></div>
  </div>

  <div class="flex items-center justify-between flex-wrap gap-3 mb-4">
    <div class="flex gap-2 flex-wrap">
      <a href="/admin" class="px-3 py-1.5 rounded-full text-xs font-semibold {f_all}">All</a>
      <a href="/admin?filter=Pending" class="px-3 py-1.5 rounded-full text-xs font-semibold {f_pending}">Pending</a>
      <a href="/admin?filter=In-Progress" class="px-3 py-1.5 rounded-full text-xs font-semibold {f_progress}">In-Progress</a>
      <a href="/admin?filter=Resolved" class="px-3 py-1.5 rounded-full text-xs font-semibold {f_resolved}">Resolved</a>
    </div>
    <form method="GET" action="/admin" class="flex gap-2">
      <input type="hidden" name="filter" value="{cur_filter}">
      <input name="search" value="{search_val}" placeholder="Search name / location / ID..." class="px-3 py-2 rounded-lg border text-xs w-56">
      <button class="px-3 py-2 bg-gray-800 text-white rounded-lg text-xs font-semibold">Search</button>
    </form>
  </div>

  <div class="grid gap-3">
    {rows}
  </div>
</div>
</body></html>
'''

def admin_row_html(c):
    photo_html = f'<img src="/photo/{c.id}" class="w-16 h-16 object-cover rounded-lg border flex-shrink-0" alt="">' if c.photo_data else '<div class="w-16 h-16 rounded-lg bg-gray-100 flex items-center justify-center text-gray-300 flex-shrink-0"><i class="fa-solid fa-image"></i></div>'
    public_btn = ''
    if not c.is_public:
        public_btn = f'<a href="/admin/public/{c.id}" class="text-xs text-center px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition">Approve for Public</a>'
    return f'''
    <div class="bg-white rounded-xl border p-4 flex flex-col md:flex-row gap-4">
      {photo_html}
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap mb-1">
          <span class="font-mono text-xs text-gray-400">{c.tracking_id}</span>
          {status_badge(c.status)}
          <span class="text-xs text-gray-400">{c.created_at.strftime('%d %b %Y')}</span>
          {f'<span class="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full">Public ✓</span>' if c.is_public else '<span class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">Private</span>'}
        </div>
        <p class="text-sm font-semibold text-gray-800">{c.description}</p>
        <p class="text-xs text-gray-500 mt-1">{c.category} • {c.location} • {c.name} ({c.phone}){' • CNIC: ' + c.cnic if c.cnic else ''}</p>
        {f'<p class="text-xs text-gov-dark bg-gov/5 border border-gov/15 rounded-lg px-2.5 py-1.5 mt-2 inline-block"><i class="fa-solid fa-comment-dots mr-1"></i>{c.remarks}</p>' if c.remarks else ''}
        <form method="POST" action="/remark/{c.id}" class="mt-2.5 flex gap-2">
          <input name="remarks" value="{c.remarks or ''}" placeholder="Official remarks / response likhein..." class="flex-1 px-3 py-1.5 rounded-lg border text-xs">
          <button class="px-3 py-1.5 bg-gray-800 text-white rounded-lg text-xs font-semibold">Save</button>
        </form>
      </div>
      <div class="flex md:flex-col gap-2 flex-shrink-0">
        <a href="/status/{c.id}/In-Progress" class="text-xs text-center px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition">Mark In-Progress</a>
        <a href="/status/{c.id}/Resolved" class="text-xs text-center px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition">Mark Resolved</a>
        <a href="/status/{c.id}/Pending" class="text-xs text-center px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg transition">Mark Pending</a>
        {public_btn}
        <a href="/delete/{c.id}" onclick="return confirm('Delete this complaint?')" class="text-xs text-center px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg transition">Delete</a>
      </div>
    </div>
    '''

@app.route("/admin")
def admin():
    if not session.get("admin"):
        return redirect("/login")
    f = request.args.get("filter", "")
    search = request.args.get("search", "").strip()
    q = Complaint.query
    if f:
        q = q.filter_by(status=f)
    if search:
        like = f"%{search}%"
        q = q.filter(db.or_(Complaint.name.ilike(like), Complaint.location.ilike(like), Complaint.tracking_id.ilike(like), Complaint.description.ilike(like)))
    complaints = q.order_by(Complaint.created_at.desc()).all()

    total = Complaint.query.count()
    pending = Complaint.query.filter_by(status="Pending").count()
    inprogress = Complaint.query.filter_by(status="In-Progress").count()
    resolved = Complaint.query.filter_by(status="Resolved").count()

    def fcls(key):
        return "bg-gray-800 text-white" if f == key else "bg-white border text-gray-600"

    rows = "".join(admin_row_html(c) for c in complaints) or '<div class="text-center text-gray-400 py-16 bg-white rounded-xl border">Koi complaint nahi mili.</div>'

    return ADMIN_DASH.format(
        head=HEAD.format(emblem_favicon=emblem_favicon()),
        emblem_sm=emblem(38), council=COUNCIL_NAME_EN,
        logged_in_name=session.get("admin_name", "Admin"), logged_in_role=session.get("admin_role", "Admin"),
        total=total, pending=pending, inprogress=inprogress, resolved=resolved,
        f_all=fcls(""), f_pending=fcls("Pending"), f_progress=fcls("In-Progress"), f_resolved=fcls("Resolved"),
        cur_filter=f, search_val=search,
        rows=rows,
    )


@app.route("/admin/public/<int:id>")
def approve_public(id):
    if not session.get("admin"):
        return redirect("/login")
    c = Complaint.query.get(id)
    if c:
        c.is_public = True
        db.session.commit()
    return redirect("/admin")


@app.route("/status/<int:id>/<status>")
def change_status(id, status):
    if not session.get("admin"):
        return redirect("/login")
    if status in STATUS_STYLES:
        c = Complaint.query.get(id)
        if c:
            c.status = status
            db.session.commit()
    return redirect(request.referrer or "/admin")


@app.route("/remark/<int:id>", methods=["POST"])
def remark(id):
    if not session.get("admin"):
        return redirect("/login")
    c = Complaint.query.get(id)
    if c:
        c.remarks = request.form.get("remarks", "").strip()
        db.session.commit()
    return redirect(request.referrer or "/admin")


@app.route("/delete/<int:id>")
def delete(id):
    if not session.get("admin"):
        return redirect("/login")
    c = Complaint.query.get(id)
    if c:
        db.session.delete(c)
        db.session.commit()
    return redirect("/admin")


# ============================================================
# MY ACCOUNT
# ============================================================
ACCOUNT_HTML = '''
<!DOCTYPE html><html lang="en"><head><title>My Account — Daur Awaz</title>{head}</head>
<body class="bg-[#F6F8F7]">
<header class="bg-gov-dark text-white">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex justify-between items-center flex-wrap gap-3">
    <div class="flex items-center gap-3">{emblem_sm}<div><h1 class="font-bold">My Account</h1><p class="text-xs text-gray-300">{council}</p></div></div>
    <a href="/admin" class="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-full text-xs transition">← Back to Dashboard</a>
  </div>
</header>
<div class="max-w-md mx-auto px-4 py-10">
  {message}
  <div class="bg-white rounded-2xl border shadow-sm p-6 mb-5">
    <h2 class="font-bold text-sm mb-1">Account Details</h2>
    <p class="text-xs text-gray-500 mb-4">Signed in as <b>{username}</b> ({role})</p>

    <form method="POST" action="/admin/account/name" class="flex gap-2 mb-1">
      <input name="full_name" value="{full_name}" placeholder="Display name" class="flex-1 px-3 py-2 rounded-lg border text-sm">
      <button class="px-4 py-2 bg-gray-800 text-white rounded-lg text-xs font-semibold">Save Name</button>
    </form>
  </div>

  <div class="bg-white rounded-2xl border shadow-sm p-6">
    <h2 class="font-bold text-sm mb-1">Change Password</h2>
    <p class="text-xs text-gray-500 mb-4">Apna current password confirm karein, phir naya password set karein.</p>
    <form method="POST" action="/admin/account/password" class="space-y-3">
      <input type="password" name="current_password" required placeholder="Current password" class="w-full px-3 py-2.5 rounded-lg border text-sm">
      <input type="password" name="new_password" required minlength="6" placeholder="New password (min 6 characters)" class="w-full px-3 py-2.5 rounded-lg border text-sm">
      <input type="password" name="confirm_password" required minlength="6" placeholder="Confirm new password" class="w-full px-3 py-2.5 rounded-lg border text-sm">
      <button class="w-full py-2.5 bg-gov text-white rounded-lg font-semibold text-sm hover:bg-gov-dark transition">Update Password</button>
    </form>
  </div>
</div>
</body></html>
'''

@app.route("/admin/account", methods=["GET"])
def account():
    if not session.get("admin"):
        return redirect("/login")
    user = AdminUser.query.get(session["admin_id"])
    if not user:
        session.clear()
        return redirect("/login")
    msg_html = ""
    msg = request.args.get("msg")
    if msg == "pw_ok":
        msg_html = '<div class="mb-5 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700 text-center">Password successfully updated.</div>'
    elif msg == "pw_wrong":
        msg_html = '<div class="mb-5 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 text-center">Current password ghalat hai.</div>'
    elif msg == "pw_mismatch":
        msg_html = '<div class="mb-5 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 text-center">Naya password aur confirmation match nahi karte.</div>'
    elif msg == "name_ok":
        msg_html = '<div class="mb-5 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700 text-center">Naam update ho gaya.</div>'
    return ACCOUNT_HTML.format(
        head=HEAD.format(emblem_favicon=emblem_favicon()), emblem_sm=emblem(38), council=COUNCIL_NAME_EN,
        message=msg_html, username=user.username, role=user.role, full_name=user.full_name or "",
    )


@app.route("/admin/account/password", methods=["POST"])
def account_password():
    if not session.get("admin"):
        return redirect("/login")
    user = AdminUser.query.get(session["admin_id"])
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")
    if not user or not check_password_hash(user.password_hash, current):
        return redirect("/admin/account?msg=pw_wrong")
    if new != confirm:
        return redirect("/admin/account?msg=pw_mismatch")
    user.password_hash = generate_password_hash(new)
    db.session.commit()
    return redirect("/admin/account?msg=pw_ok")


@app.route("/admin/account/name", methods=["POST"])
def account_name():
    if not session.get("admin"):
        return redirect("/login")
    user = AdminUser.query.get(session["admin_id"])
    if user:
        user.full_name = request.form.get("full_name", "").strip()
        db.session.commit()
        session["admin_name"] = user.full_name or user.username
    return redirect("/admin/account?msg=name_ok")


# ============================================================
# MANAGE USERS
# ============================================================
USERS_HTML = '''
<!DOCTYPE html><html lang="en"><head><title>Manage Users — Daur Awaz</title>{head}</head>
<body class="bg-[#F6F8F7]">
<header class="bg-gov-dark text-white">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex justify-between items-center flex-wrap gap-3">
    <div class="flex items-center gap-3">{emblem_sm}<div><h1 class="font-bold">Manage Users</h1><p class="text-xs text-gray-300">{council}</p></div></div>
    <a href="/admin" class="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-full text-xs transition">← Back to Dashboard</a>
  </div>
</header>
<div class="max-w-3xl mx-auto px-4 py-10">
  {message}
  <div class="bg-white rounded-2xl border shadow-sm p-6 mb-6">
    <h2 class="font-bold text-sm mb-1">Add a New Admin Account</h2>
    <p class="text-xs text-gray-500 mb-4">PA ya staff member ke liye alag login banayein — unhe apna asal password kabhi share na karein.</p>
    <form method="POST" action="/admin/users/add" class="grid sm:grid-cols-2 gap-3">
      <input name="full_name" required placeholder="Full name (e.g. Ahmed — PA to Chairman)" class="px-3 py-2.5 rounded-lg border text-sm sm:col-span-2">
      <input name="username" required placeholder="Username" class="px-3 py-2.5 rounded-lg border text-sm">
      <select name="role" class="px-3 py-2.5 rounded-lg border text-sm">
        <option value="Assistant">Assistant (PA)</option>
        <option value="Chairman">Chairman (full access)</option>
      </select>
      <input type="password" name="password" required minlength="6" placeholder="Password (min 6 characters)" class="px-3 py-2.5 rounded-lg border text-sm sm:col-span-2">
      <button class="sm:col-span-2 py-2.5 bg-gov text-white rounded-lg font-semibold text-sm hover:bg-gov-dark transition">Create Account</button>
    </form>
  </div>

  <div class="bg-white rounded-2xl border shadow-sm p-6">
    <h2 class="font-bold text-sm mb-4">Existing Admin Accounts ({count})</h2>
    <div class="grid gap-2.5">
      {rows}
    </div>
  </div>
</div>
</body></html>
'''

def user_row_html(u, current_user_id):
    is_you = u.id == current_user_id
    role_badge = "bg-gov/10 text-gov" if u.role == "Chairman" else "bg-gray-100 text-gray-600"
    delete_btn = '<span class="text-xs text-gray-400 px-3 py-1.5">This is you</span>' if is_you else f'<a href="/admin/users/delete/{u.id}" onclick="return confirm(\'Remove this account?\')" class="text-xs px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg transition">Remove</a>'
    return f'''
    <div class="flex items-center justify-between border rounded-xl px-4 py-3 flex-wrap gap-2">
      <div>
        <p class="text-sm font-semibold text-gray-800">{u.full_name or u.username} {' (you)' if is_you else ''}</p>
        <p class="text-xs text-gray-500">@{u.username} • <span class="px-2 py-0.5 rounded-full {role_badge} font-semibold">{u.role}</span></p>
      </div>
      {delete_btn}
    </div>
    '''

@app.route("/admin/users", methods=["GET"])
def users():
    if not session.get("admin"):
        return redirect("/login")
    msg_html = ""
    msg = request.args.get("msg")
    if msg == "created":
        msg_html = '<div class="mb-5 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700 text-center">New account ban gaya — login details unko securely share karein.</div>'
    elif msg == "taken":
        msg_html = '<div class="mb-5 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 text-center">Ye username pehle se mojood hai — koi aur username try karein.</div>'
    elif msg == "removed":
        msg_html = '<div class="mb-5 p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700 text-center">Account remove kar diya gaya.</div>'
    elif msg == "last":
        msg_html = '<div class="mb-5 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 text-center">Aakhri admin account delete nahi ho sakta.</div>'

    all_users = AdminUser.query.order_by(AdminUser.created_at.asc()).all()
    rows = "".join(user_row_html(u, session["admin_id"]) for u in all_users)
    return USERS_HTML.format(
        head=HEAD.format(emblem_favicon=emblem_favicon()), emblem_sm=emblem(38), council=COUNCIL_NAME_EN,
        message=msg_html, count=len(all_users), rows=rows,
    )


@app.route("/admin/users/add", methods=["POST"])
def users_add():
    if not session.get("admin"):
        return redirect("/login")
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    full_name = request.form.get("full_name", "").strip()
    role = request.form.get("role", "Assistant")
    if role not in ("Chairman", "Assistant"):
        role = "Assistant"

    if AdminUser.query.filter_by(username=username).first():
        return redirect("/admin/users?msg=taken")

    db.session.add(AdminUser(
        username=username,
        password_hash=generate_password_hash(password),
        full_name=full_name,
        role=role,
    ))
    db.session.commit()
    return redirect("/admin/users?msg=created")


@app.route("/admin/users/delete/<int:id>")
def users_delete(id):
    if not session.get("admin"):
        return redirect("/login")
    if id == session.get("admin_id"):
        return redirect("/admin/users")
    if AdminUser.query.count() <= 1:
        return redirect("/admin/users?msg=last")
    u = AdminUser.query.get(id)
    if u:
        db.session.delete(u)
        db.session.commit()
    return redirect("/admin/users?msg=removed")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ============================================================
# REPORTS
# ============================================================
REPORTS_HTML = '''
<!DOCTYPE html><html lang="en"><head><title>Reports — Daur Awaz</title>{head}</head>
<body class="bg-[#F6F8F7]">
<header class="bg-gov-dark text-white">
  <div class="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex justify-between items-center flex-wrap gap-3">
    <div class="flex items-center gap-3">{emblem_sm}<div><h1 class="font-bold">Reports & Progress</h1><p class="text-xs text-gray-300">{council}</p></div></div>
    <a href="/admin" class="bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-full text-xs transition">← Back to Dashboard</a>
  </div>
</header>

<div class="max-w-6xl mx-auto px-4 sm:px-6 py-8">

  <div class="grid sm:grid-cols-2 gap-4 mb-8">
    <div class="bg-white rounded-2xl border p-6">
      <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3"><i class="fa-regular fa-calendar mr-1"></i> This Month — {this_month_label}</p>
      <div class="grid grid-cols-4 gap-2 text-center mb-4">
        <div><p class="text-xl font-extrabold text-gray-800">{tm_total}</p><p class="text-[10px] text-gray-500">Total</p></div>
        <div><p class="text-xl font-extrabold text-amber-600">{tm_pending}</p><p class="text-[10px] text-gray-500">Pending</p></div>
        <div><p class="text-xl font-extrabold text-blue-600">{tm_progress}</p><p class="text-[10px] text-gray-500">In-Progress</p></div>
        <div><p class="text-xl font-extrabold text-emerald-600">{tm_resolved}</p><p class="text-[10px] text-gray-500">Resolved</p></div>
      </div>
      <div class="w-full h-2 rounded-full bg-gray-100 overflow-hidden"><div class="h-full bg-emerald-500" style="width:{tm_rate}%"></div></div>
      <p class="text-xs text-gray-500 mt-1.5">{tm_rate}% resolved this month</p>
    </div>

    <div class="bg-white rounded-2xl border p-6">
      <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3"><i class="fa-solid fa-calendar-days mr-1"></i> This Year — {this_year_label}</p>
      <div class="grid grid-cols-4 gap-2 text-center mb-4">
        <div><p class="text-xl font-extrabold text-gray-800">{ty_total}</p><p class="text-[10px] text-gray-500">Total</p></div>
        <div><p class="text-xl font-extrabold text-amber-600">{ty_pending}</p><p class="text-[10px] text-gray-500">Pending</p></div>
        <div><p class="text-xl font-extrabold text-blue-600">{ty_progress}</p><p class="text-[10px] text-gray-500">In-Progress</p></div>
        <div><p class="text-xl font-extrabold text-emerald-600">{ty_resolved}</p><p class="text-[10px] text-gray-500">Resolved</p></div>
      </div>
      <div class="w-full h-2 rounded-full bg-gray-100 overflow-hidden"><div class="h-full bg-emerald-500" style="width:{ty_rate}%"></div></div>
      <p class="text-xs text-gray-500 mt-1.5">{ty_rate}% resolved this year</p>
    </div>
  </div>

  <div class="bg-white rounded-2xl border p-6 mb-8">
    <h2 class="font-bold text-sm mb-4"><i class="fa-solid fa-chart-column mr-1.5 text-gov"></i> Monthly Breakdown</h2>
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500 border-b">
            <th class="py-2 pr-3">Month</th>
            <th class="py-2 px-3 text-center">Total</th>
            <th class="py-2 px-3 text-center">Pending</th>
            <th class="py-2 px-3 text-center">In-Progress</th>
            <th class="py-2 px-3 text-center">Resolved</th>
            <th class="py-2 pl-3">Resolution Rate</th>
          </tr>
        </thead>
        <tbody>
          {monthly_rows}
        </tbody>
      </table>
    </div>
  </div>

  <div class="bg-white rounded-2xl border p-6">
    <h2 class="font-bold text-sm mb-4"><i class="fa-solid fa-chart-simple mr-1.5 text-gov"></i> Yearly Breakdown</h2>
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-gray-500 border-b">
            <th class="py-2 pr-3">Year</th>
            <th class="py-2 px-3 text-center">Total</th>
            <th class="py-2 px-3 text-center">Pending</th>
            <th class="py-2 px-3 text-center">In-Progress</th>
            <th class="py-2 px-3 text-center">Resolved</th>
            <th class="py-2 pl-3">Resolution Rate</th>
          </tr>
        </thead>
        <tbody>
          {yearly_rows}
        </tbody>
      </table>
    </div>
  </div>

</div>
</body></html>
'''

def _rate(stats):
    return round((stats["Resolved"] / stats["total"]) * 100) if stats["total"] else 0

def _report_row(label, stats):
    rate = _rate(stats)
    bar_color = "bg-emerald-500" if rate >= 70 else ("bg-amber-500" if rate >= 40 else "bg-red-400")
    return f'''
    <tr class="border-b last:border-0">
      <td class="py-2.5 pr-3 font-semibold text-gray-800">{label}</td>
      <td class="py-2.5 px-3 text-center">{stats['total']}</td>
      <td class="py-2.5 px-3 text-center text-amber-600">{stats['Pending']}</td>
      <td class="py-2.5 px-3 text-center text-blue-600">{stats['In-Progress']}</td>
      <td class="py-2.5 px-3 text-center text-emerald-600">{stats['Resolved']}</td>
      <td class="py-2.5 pl-3">
        <div class="flex items-center gap-2">
          <div class="w-24 h-1.5 rounded-full bg-gray-100 overflow-hidden"><div class="h-full {bar_color}" style="width:{rate}%"></div></div>
          <span class="text-xs text-gray-500">{rate}%</span>
        </div>
      </td>
    </tr>'''

def _blank_stats():
    return {"total": 0, "Pending": 0, "In-Progress": 0, "Resolved": 0}

@app.route("/admin/reports")
def reports():
    if not session.get("admin"):
        return redirect("/login")

    all_complaints = Complaint.query.order_by(Complaint.created_at.asc()).all()

    monthly = OrderedDict()
    yearly = OrderedDict()

    for c in all_complaints:
        y, m = c.created_at.year, c.created_at.month
        mkey = (y, m)
        if mkey not in monthly:
            monthly[mkey] = _blank_stats()
        monthly[mkey]["total"] += 1
        monthly[mkey][c.status] = monthly[mkey].get(c.status, 0) + 1

        if y not in yearly:
            yearly[y] = _blank_stats()
        yearly[y]["total"] += 1
        yearly[y][c.status] = yearly[y].get(c.status, 0) + 1

    now = datetime.utcnow()
    this_month_stats = monthly.get((now.year, now.month), _blank_stats())
    this_year_stats = yearly.get(now.year, _blank_stats())

    monthly_sorted = sorted(monthly.items(), key=lambda kv: kv[0], reverse=True)
    yearly_sorted = sorted(yearly.items(), key=lambda kv: kv[0], reverse=True)

    monthly_rows = "".join(
        _report_row(f"{calendar.month_name[m]} {y}", stats) for (y, m), stats in monthly_sorted
    ) or '<tr><td colspan="6" class="text-center text-gray-400 py-8 text-sm">Abhi tak koi data nahi hai.</td></tr>'

    yearly_rows = "".join(
        _report_row(str(y), stats) for y, stats in yearly_sorted
    ) or '<tr><td colspan="6" class="text-center text-gray-400 py-8 text-sm">Abhi tak koi data nahi hai.</td></tr>'

    return REPORTS_HTML.format(
        head=HEAD.format(emblem_favicon=emblem_favicon()), emblem_sm=emblem(38), council=COUNCIL_NAME_EN,
        this_month_label=f"{calendar.month_name[now.month]} {now.year}",
        this_year_label=str(now.year),
        tm_total=this_month_stats["total"], tm_pending=this_month_stats["Pending"],
        tm_progress=this_month_stats["In-Progress"], tm_resolved=this_month_stats["Resolved"], tm_rate=_rate(this_month_stats),
        ty_total=this_year_stats["total"], ty_pending=this_year_stats["Pending"],
        ty_progress=this_year_stats["In-Progress"], ty_resolved=this_year_stats["Resolved"], ty_rate=_rate(this_year_stats),
        monthly_rows=monthly_rows, yearly_rows=yearly_rows,
    )


# ============================================================
# MAIN (for local development)
# ============================================================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
