# ==============================================================================
#           ULTIMATE & COMPLETE APPLICATION FILE: app.py
#       (A fully functional, self-contained Python script for the Task App)
# ==============================================================================

import os
import uuid
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, auth

# --- অ্যাপ এবং Firebase ইনিশিয়ালাইজেশন ---
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "a_very_strong_production_secret_key_final_build")

# .env ফাইল থেকে গোপন অ্যাডমিন পাথ লোড করুন
SECRET_ADMIN_PATH = os.getenv("SECRET_ADMIN_PATH", "secure-admin-panel-for-production-final-build-e5f8")

try:
    firebase_creds_json_str = os.getenv('FIREBASE_CREDENTIALS_JSON')
    if not firebase_creds_json_str:
        cred = credentials.Certificate("firebase_credentials.json")
    else:
        firebase_creds_dict = json.loads(firebase_creds_json_str)
        cred = credentials.Certificate(firebase_creds_dict)
    
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("SUCCESS: Firebase Initialized for the Final Application.")
except Exception as e:
    print(f"FATAL ERROR: Could not initialize Firebase. Error: {e}")
    db = None

# --- ডেকোরেটর (শুধুমাত্র লগইন চেকের জন্য) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("এই পেইজটি দেখার জন্য লগইন করুন।", "info")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Helper ফাংশন ---
def generate_referral_code():
    return str(uuid.uuid4()).split('-')[0].upper()

# --- Authentication and Basic Routes ---
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name, email, password = request.form['name'], request.form['email'], request.form['password']
        referrer_code = request.form.get('referrer_code', '').strip().upper()
        try:
            user_record = auth.create_user(email=email, password=password, display_name=name)
            user_data = {
                'name': name, 'email': email, 'balance': 0.0,
                'referred_by': referrer_code, 'my_referral_code': generate_referral_code(),
                'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('users').document(user_record.uid).set(user_data)
            flash('রেজিস্ট্রেশন সফল হয়েছে!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"একটি সমস্যা হয়েছে: {e}", "error")
            return redirect(url_for('signup'))

    config_data = {'firebase_api_key': os.getenv('FIREBASE_API_KEY'), 'firebase_auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN'), 'firebase_project_id': os.getenv('FIREBASE_PROJECT_ID'), 'firebase_messaging_sender_id': os.getenv('FIREBASE_MESSAGING_SENDER_ID'), 'firebase_app_id': os.getenv('FIREBASE_APP_ID')}
    return render_template('signup.html', ref_code=request.args.get('ref', ''), config=config_data)

@app.route('/login')
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    config_data = {'firebase_api_key': os.getenv('FIREBASE_API_KEY'), 'firebase_auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN'), 'firebase_project_id': os.getenv('FIREBASE_PROJECT_ID'), 'firebase_messaging_sender_id': os.getenv('FIREBASE_MESSAGING_SENDER_ID'), 'firebase_app_id': os.getenv('FIREBASE_APP_ID')}
    return render_template('login.html', config=config_data)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('আপনি সফলভাবে লগ আউট করেছেন।', 'info')
    return redirect(url_for('login'))

# --- API Routes ---
@app.route('/api/set_session', methods=['POST'])
def set_session():
    id_token = request.json.get('idToken')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        user_doc = db.collection('users').document(uid).get()
        if not user_doc.exists: # Handle Google Sign-in for new users
            user_info = auth.get_user(uid)
            user_data = {
                'name': user_info.display_name or 'Google User', 'email': user_info.email,
                'balance': 0.0, 'my_referral_code': generate_referral_code(),
                'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('users').document(uid).set(user_data)
        
        session['user_id'] = uid
        session['user_name'] = user_doc.to_dict().get('name') if user_doc.exists else user_info.display_name
        return jsonify({"status": "success", "redirect_url": url_for('dashboard')})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 401

# --- User-Facing Pages ---
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    user_doc = db.collection('users').document(user_id).get()
    if not user_doc.exists:
        session.clear()
        return redirect(url_for('login'))
        
    user = user_doc.to_dict()
    referral_link = url_for('signup', ref=user.get('my_referral_code'), _external=True)

    referrals_query = db.collection('referrals').where('referrer_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
    my_referrals = [doc.to_dict() for doc in referrals_query]

    balance_query = db.collection('balance_history').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
    balance_history = [doc.to_dict() for doc in balance_query]
    
    return render_template('dashboard.html', user=user, referral_link=referral_link, my_referrals=my_referrals, balance_history=balance_history)

@app.route('/tasks')
@login_required
def tasks_page():
    tasks_query = db.collection('tasks').where('status', '==', 'active').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    categorized_tasks = {}
    for task_doc in tasks_query:
        task = task_doc.to_dict()
        task['id'] = task_doc.id
        category = task.get('category', 'General')
        if category not in categorized_tasks: categorized_tasks[category] = []
        categorized_tasks[category].append(task)
    return render_template('tasks.html', categorized_tasks=categorized_tasks)

@app.route('/task/<task_id>', methods=['GET', 'POST'])
@login_required
def view_task(task_id):
    task_ref = db.collection('tasks').document(task_id)
    task = task_ref.get().to_dict()
    if not task:
        flash("টাস্কটি খুঁজে পাওয়া যায়নি।", "error")
        return redirect(url_for('tasks_page'))
    
    task_type = task.get('task_type', 'unknown')
    if request.method == 'POST':
        submission_data = {
            'user_id': session['user_id'], 'task_id': task_id,
            'task_title': task.get('title'), 'reward': task.get('reward'),
            'status': 'pending', 'submitted_at': firestore.SERVER_TIMESTAMP
        }
        if task_type == 'screenshot_upload':
            screenshot_url = request.form.get('screenshot_url')
            if not screenshot_url:
                flash("স্ক্রিনশট আপলোড ব্যর্থ হয়েছে।", "error")
                return redirect(url_for('view_task', task_id=task_id))
            submission_data['proof'] = {'screenshot_url': screenshot_url}
        db.collection('task_submissions').add(submission_data)
        flash("আপনার কাজ জমা দেওয়া হয়েছে। পর্যালোচনার পর ব্যালেন্স যোগ করা হবে।", "success")
        return redirect(url_for('tasks_page'))

    template_map = {'screenshot_upload': 'task_types/screenshot_task.html'}
    template_file = template_map.get(task_type, None)
    if template_file:
        return render_template(template_file, task=task, task_id=task_id)
    else:
        flash("এই ধরণের টাস্কের জন্য কোনো পেইজ তৈরি করা হয়নি।", "error")
        return redirect(url_for('tasks_page'))


# --- UNIQUE LINK ADMIN PANEL ---
@app.route(f'/{SECRET_ADMIN_PATH}')
def admin_dashboard():
    pending_tasks_query = db.collection('task_submissions').where('status', '==', 'pending').order_by('submitted_at').stream()
    pending_tasks = [dict(task.to_dict(), **{'id': task.id}) for task in pending_tasks_query]
    return render_template('admin_dashboard.html', pending_tasks=pending_tasks, admin_path=SECRET_ADMIN_PATH)

@app.route(f'/{SECRET_ADMIN_PATH}/task/approve/<submission_id>')
def approve_task(submission_id):
    submission_ref = db.collection('task_submissions').document(submission_id)
    @firestore.transactional
    def update_in_transaction(transaction, submission_ref):
        snapshot = submission_ref.get(transaction=transaction)
        if not snapshot.exists or snapshot.to_dict().get('status') != 'pending': raise ValueError("Task processed or non-existent.")
        data = snapshot.to_dict()
        user_ref = db.collection('users').document(data['user_id'])
        transaction.update(user_ref, {'balance': firestore.Increment(data['reward'])})
        transaction.update(submission_ref, {'status': 'completed', 'processed_at': firestore.SERVER_TIMESTAMP})
        balance_history_ref = db.collection('balance_history').document()
        transaction.set(balance_history_ref, {'user_id': data['user_id'], 'amount': data['reward'], 'type': 'task_reward', 'description': f"Reward for: {data.get('task_title')}", 'timestamp': firestore.SERVER_TIMESTAMP})
    try:
        update_in_transaction(db.transaction(), submission_ref)
        flash("টাস্ক সফলভাবে অ্যাপ্রুভ করা হয়েছে!", "success")
    except Exception as e:
        flash(f"একটি সমস্যা হয়েছে: {e}", "error")
    return redirect(url_for('admin_dashboard'))

@app.route(f'/{SECRET_ADMIN_PATH}/task/reject/<submission_id>')
def reject_task(submission_id):
    db.collection('task_submissions').document(submission_id).update({'status': 'rejected', 'processed_at': firestore.SERVER_TIMESTAMP})
    flash("টাস্কটি বাতিল করা হয়েছে।", "info")
    return redirect(url_for('admin_dashboard'))

@app.route(f'/{SECRET_ADMIN_PATH}/manage-tasks')
def manage_tasks():
    tasks_query = db.collection('tasks').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    all_tasks = [dict(task.to_dict(), **{'id': task.id}) for task in tasks_query]
    return render_template('manage_tasks.html', all_tasks=all_tasks, admin_path=SECRET_ADMIN_PATH)

@app.route(f'/{SECRET_ADMIN_PATH}/create-task', methods=['GET', 'POST'])
def create_task():
    if request.method == 'POST':
        db.collection('tasks').add({
            'title': request.form['title'], 'description': request.form['description'],
            'category': request.form['category'], 'task_type': request.form['task_type'],
            'reward': float(request.form['reward']), 'target_url': request.form['target_url'],
            'status': 'active', 'icon_class': request.form['icon_class'],
            'created_at': firestore.SERVER_TIMESTAMP
        })
        flash('নতুন টাস্ক সফলভাবে তৈরি করা হয়েছে।', 'success')
        return redirect(url_for('manage_tasks'))
    return render_template('create_task.html', admin_path=SECRET_ADMIN_PATH)

@app.route(f'/{SECRET_ADMIN_PATH}/edit-task/<task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    task_ref = db.collection('tasks').document(task_id)
    if request.method == 'POST':
        task_ref.update({
            'title': request.form['title'], 'description': request.form['description'],
            'category': request.form['category'], 'task_type': request.form['task_type'],
            'reward': float(request.form['reward']), 'target_url': request.form['target_url'],
            'icon_class': request.form['icon_class']
        })
        flash('টাস্ক সফলভাবে আপডেট করা হয়েছে।', 'success')
        return redirect(url_for('manage_tasks'))
    task_data = task_ref.get().to_dict()
    return render_template('edit_task.html', task=task_data, task_id=task_id, admin_path=SECRET_ADMIN_PATH)

@app.route(f'/{SECRET_ADMIN_PATH}/delete-task/<task_id>')
def delete_task(task_id):
    db.collection('tasks').document(task_id).delete()
    flash('টাস্ক সফলভাবে ডিলিট করা হয়েছে।', 'success')
    return redirect(url_for('manage_tasks'))

@app.route(f'/{SECRET_ADMIN_PATH}/toggle-status/<task_id>')
def toggle_task_status(task_id):
    task_ref = db.collection('tasks').document(task_id)
    task = task_ref.get().to_dict()
    new_status = 'inactive' if task.get('status') == 'active' else 'active'
    task_ref.update({'status': new_status})
    flash(f'টাস্কের স্ট্যাটাস পরিবর্তন করে "{new_status}" করা হয়েছে।', 'info')
    return redirect(url_for('manage_tasks'))

# --- লোকাল টেস্টিং এর জন্য ---
if __name__ == '__main__':
    print(f"Admin panel is accessible at: http://127.0.0.1:8080/{SECRET_ADMIN_PATH}")
    app.run(host='0.0.0.0', port=8080, debug=True)
