# AI Affiliate Auto-Post System with Dashboard and Stripe (v4.0)
# --------------------------------------------------
# Description: Generates affiliate blog posts with images and SEO,
# allows auto-posting to Blogger, and includes a web dashboard
# with user login and Stripe-based subscriptions.

import os
import random
import datetime
import requests
from flask import Flask, render_template_string, redirect, url_for, request, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from google.oauth2 import service_account
from googleapiclient.discovery import build
import stripe

# -------- Configuration --------
BLOG_ID = '2774539022475262259'  # Replace with your Blogger ID
SERVICE_ACCOUNT_FILE = 'client_secret_987011430580-degrkk1dhldk28tdipg49pq08f0n51cu.apps.googleusercontent.com.json'  # Integrated Google API credentials
IMAGE_API = 'https://source.unsplash.com/800x400/?'
STRIPE_SECRET_KEY = 'sk_test_51NzbwlK0Lms2GWRlLzDq4wGwT3L3Yw9kKMEBXyVaYwAswRgWSHHtZ5ZcdTtnrRfrr3DCZAjMBoNHZVeUTqX4MiR800gn8kFjIY'
STRIPE_PRICE_ID = 'price_1O0Th5K0Lms2GWRlA1fruLBR'

# -------- App Setup --------
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
stripe.api_key = STRIPE_SECRET_KEY

login_manager = LoginManager()
login_manager.init_app(app)

# -------- Mock Users --------
class User(UserMixin):
    def __init__(self, id):
        self.id = id

users = {'user@example.com': {'password': 'password123'}}

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# -------- Templates --------
LOGIN_TEMPLATE = """
<form method="post">
  <h2>Login</h2>
  <input type="text" name="email" placeholder="Email"><br>
  <input type="password" name="password" placeholder="Password"><br>
  <button type="submit">Login</button>
</form>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Affiliate Tool</title>
    <style>
        body { font-family: Arial; background: #f4f4f4; padding: 20px; }
        .container { background: white; padding: 20px; border-radius: 10px; max-width: 700px; margin: auto; }
        button { padding: 10px 20px; font-size: 16px; margin: 10px; }
        .log { background: #eee; padding: 10px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Affiliate Blog Tool</h1>
        {% if subscribed %}
        <form action="/generate" method="post">
            <button type="submit">📝 Generate Post</button>
        </form>
        <form action="/publish" method="post">
            <button type="submit">🚀 Publish to Blogger</button>
        </form>
        {% else %}
        <p>You must <a href="/subscribe">subscribe</a> to use the tool.</p>
        {% endif %}
        {% if log %}<div class="log">{{ log }}</div>{% endif %}
        <a href="/logout">Logout</a>
    </div>
</body>
</html>
"""

# -------- Core Logic --------
niches = [
    "AI tools for productivity",
    "Top tech gadgets under $50",
    "Work-from-home gear",
    "Best books for self-improvement",
    "Weight loss supplements that work",
    "Freelancing tools for designers",
    "Crypto wallets and tools",
    "Top coding courses online"
]

latest_filename = ""
latest_content = ""
latest_niche = ""

def generate_blog_post(niche):
    intro = f"In today's digital world, {niche.lower()} are trending fast. Want to make the most of it? Here's how."
    body = f"We’ve reviewed top options in this niche. These are trusted, trending, and perfect for your needs."
    list_items = "\n".join([
        f"- {niche} Product #{i+1} — [👉 Click to buy](https://your-affiliate-link.com)"
        for i in range(5)
    ])
    outro = "Don't miss out. Bookmark this post — your success is one tool away!"
    return f"# {niche}\n\n{intro}\n\n{body}\n\n{list_items}\n\n{outro}"

def fetch_image_url(keyword):
    return f"{IMAGE_API}{keyword.replace(' ', '+')}"

def save_post(niche):
    global latest_filename, latest_content, latest_niche
    content = generate_blog_post(niche)
    image_url = fetch_image_url(niche)
    html_image = f'<img src="{image_url}" alt="{niche}" style="width:100%;height:auto;">'
    today = datetime.date.today().strftime("%Y-%m-%d")
    filename = f"blog_post_{today}.html"

    if not os.path.exists("generated_posts"):
        os.makedirs("generated_posts")

    html_body = content.replace("\n", "<br>")
    html_full = f"{html_image}<br>{html_body}"

    with open(f"generated_posts/{filename}", "w", encoding="utf-8") as file:
        file.write(html_full)

    latest_filename = filename
    latest_content = html_full
    latest_niche = niche

    return f"✅ Post generated for niche: {niche}\nSaved as: generated_posts/{filename}"

def post_to_blogger(blog_id, title, content):
    SCOPES = ['https://www.googleapis.com/auth/blogger']
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('blogger', 'v3', credentials=credentials)
    post = {'kind': 'blogger#post', 'title': title, 'content': content}
    result = service.posts().insert(blogId=blog_id, body=post, isDraft=False).execute()
    return f"🚀 Blog post published: {result['url']}"

# -------- Routes --------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email in users and users[email]['password'] == password:
            login_user(User(email))
            return redirect(url_for('dashboard'))
        return "Invalid credentials"
    return LOGIN_TEMPLATE

@app.route('/dashboard')
@login_required
def dashboard():
    subscribed = session.get('subscribed', False)
    return render_template_string(DASHBOARD_TEMPLATE, log=None, subscribed=subscribed)

@app.route('/generate', methods=['POST'])
@login_required
def generate():
    if not session.get('subscribed'):
        return redirect(url_for('subscribe'))
    log = save_post(random.choice(niches))
    return render_template_string(DASHBOARD_TEMPLATE, log=log, subscribed=True)

@app.route('/publish', methods=['POST'])
@login_required
def publish():
    if not session.get('subscribed'):
        return redirect(url_for('subscribe'))
    if not latest_content:
        return render_template_string(DASHBOARD_TEMPLATE, log="⚠️ No content to publish. Please generate a post first.", subscribed=True)
    log = post_to_blogger(BLOG_ID, latest_niche, latest_content)
    return render_template_string(DASHBOARD_TEMPLATE, log=log, subscribed=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/subscribe')
@login_required
def subscribe():
    checkout_session = stripe.checkout.Session.create(
        success_url=url_for('success', _external=True),
        cancel_url=url_for('dashboard', _external=True),
        payment_method_types=['card'],
        mode='subscription',
        line_items=[{
            'price': STRIPE_PRICE_ID,
            'quantity': 1,
        }],
        customer_email=session.get('user_id')
    )
    return redirect(checkout_session.url, code=303)

@app.route('/success')
@login_required
def success():
    session['subscribed'] = True
    return redirect(url_for('dashboard'))

# -------- Run App --------
if __name__ == '__main__':
    app.run(debug=True)
# AI Affiliate Auto-Post System with Dashboard and Stripe (v4.0)
# --------------------------------------------------
# Description: Generates affiliate blog posts with images and SEO,
# allows auto-posting to Blogger, and includes a web dashboard
# with user login and Stripe-based subscriptions.

import os
import random
import datetime
import requests
from flask import Flask, render_template_string, redirect, url_for, request, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from google.oauth2 import service_account
from googleapiclient.discovery import build
import stripe

# -------- Configuration --------
BLOG_ID = '2774539022475262259'  # Replace with your Blogger ID
SERVICE_ACCOUNT_FILE = 'client_secret_987011430580-degrkk1dhldk28tdipg49pq08f0n51cu.apps.googleusercontent.com.json'  # Integrated Google API credentials
IMAGE_API = 'https://source.unsplash.com/800x400/?'
STRIPE_SECRET_KEY = 'sk_test_51NzbwlK0Lms2GWRlLzDq4wGwT3L3Yw9kKMEBXyVaYwAswRgWSHHtZ5ZcdTtnrRfrr3DCZAjMBoNHZVeUTqX4MiR800gn8kFjIY'
STRIPE_PRICE_ID = 'price_1O0Th5K0Lms2GWRlA1fruLBR'

# -------- App Setup --------
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
stripe.api_key = STRIPE_SECRET_KEY

login_manager = LoginManager()
login_manager.init_app(app)

# -------- Mock Users --------
class User(UserMixin):
    def __init__(self, id):
        self.id = id

users = {'user@example.com': {'password': 'password123'}}

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# -------- Templates --------
LOGIN_TEMPLATE = """
<form method="post">
  <h2>Login</h2>
  <input type="text" name="email" placeholder="Email"><br>
  <input type="password" name="password" placeholder="Password"><br>
  <button type="submit">Login</button>
</form>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Affiliate Tool</title>
    <style>
        body { font-family: Arial; background: #f4f4f4; padding: 20px; }
        .container { background: white; padding: 20px; border-radius: 10px; max-width: 700px; margin: auto; }
        button { padding: 10px 20px; font-size: 16px; margin: 10px; }
        .log { background: #eee; padding: 10px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Affiliate Blog Tool</h1>
        {% if subscribed %}
        <form action="/generate" method="post">
            <button type="submit">📝 Generate Post</button>
        </form>
        <form action="/publish" method="post">
            <button type="submit">🚀 Publish to Blogger</button>
        </form>
        {% else %}
        <p>You must <a href="/subscribe">subscribe</a> to use the tool.</p>
        {% endif %}
        {% if log %}<div class="log">{{ log }}</div>{% endif %}
        <a href="/logout">Logout</a>
    </div>
</body>
</html>
"""

# -------- Core Logic --------
niches = [
    "AI tools for productivity",
    "Top tech gadgets under $50",
    "Work-from-home gear",
    "Best books for self-improvement",
    "Weight loss supplements that work",
    "Freelancing tools for designers",
    "Crypto wallets and tools",
    "Top coding courses online"
]

latest_filename = ""
latest_content = ""
latest_niche = ""

def generate_blog_post(niche):
    intro = f"In today's digital world, {niche.lower()} are trending fast. Want to make the most of it? Here's how."
    body = f"We’ve reviewed top options in this niche. These are trusted, trending, and perfect for your needs."
    list_items = "\n".join([
        f"- {niche} Product #{i+1} — [👉 Click to buy](https://your-affiliate-link.com)"
        for i in range(5)
    ])
    outro = "Don't miss out. Bookmark this post — your success is one tool away!"
    return f"# {niche}\n\n{intro}\n\n{body}\n\n{list_items}\n\n{outro}"

def fetch_image_url(keyword):
    return f"{IMAGE_API}{keyword.replace(' ', '+')}"

def save_post(niche):
    global latest_filename, latest_content, latest_niche
    content = generate_blog_post(niche)
    image_url = fetch_image_url(niche)
    html_image = f'<img src="{image_url}" alt="{niche}" style="width:100%;height:auto;">'
    today = datetime.date.today().strftime("%Y-%m-%d")
    filename = f"blog_post_{today}.html"

    if not os.path.exists("generated_posts"):
        os.makedirs("generated_posts")

    html_body = content.replace("\n", "<br>")
    html_full = f"{html_image}<br>{html_body}"

    with open(f"generated_posts/{filename}", "w", encoding="utf-8") as file:
        file.write(html_full)

    latest_filename = filename
    latest_content = html_full
    latest_niche = niche

    return f"✅ Post generated for niche: {niche}\nSaved as: generated_posts/{filename}"

def post_to_blogger(blog_id, title, content):
    SCOPES = ['https://www.googleapis.com/auth/blogger']
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('blogger', 'v3', credentials=credentials)
    post = {'kind': 'blogger#post', 'title': title, 'content': content}
    result = service.posts().insert(blogId=blog_id, body=post, isDraft=False).execute()
    return f"🚀 Blog post published: {result['url']}"

# -------- Routes --------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
if email in users and users[email]["password"] == password:
    # Code to execute if email and password are correct

            login_user(User(email))
            return redirect(url_for('dashboard'))
        return "Invalid credentials"
    return LOGIN_TEMPLATE

@app.route('/dashboard')
@login_required
def dashboard():
    subscribed = session.get('subscribed', False)
    return render_template_string(DASHBOARD_TEMPLATE, log=None, subscribed=subscribed)

@app.route('/generate', methods=['POST'])
@login_required
def generate():
    if not session.get('subscribed'):
        return redirect(url_for('subscribe'))
    log = save_post(random.choice(niches))
    return render_template_string(DASHBOARD_TEMPLATE, log=log, subscribed=True)

@app.route('/publish', methods=['POST'])
@login_required
def publish():
    if not session.get('subscribed'):
        return redirect(url_for('subscribe'))
    if not latest_content:
        return render_template_string(DASHBOARD_TEMPLATE, log="⚠️ No content to publish. Please generate a post first.", subscribed=True)
    log = post_to_blogger(BLOG_ID, latest_niche, latest_content)
    return render_template_string(DASHBOARD_TEMPLATE, log=log, subscribed=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/subscribe')
@login_required
def subscribe():
    checkout_session = stripe.checkout.Session.create(
        success_url=url_for('success', _external=True),
        cancel_url=url_for('dashboard', _external=True),
        payment_method_types=['card'],
        mode='subscription',
        line_items=[{
            'price': STRIPE_PRICE_ID,
            'quantity': 1,
        }],
        customer_email=session.get('user_id')
    )
    return redirect(checkout_session.url, code=303)

@app.route('/success')
@login_required
def success():
    session['subscribed'] = True
    return redirect(url_for('dashboard'))

# -------- Run App --------
if __name__ == '__main__':
    app.run(debug=True)
