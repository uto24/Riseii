# ==============================================================================
#           ULTIMATE & COMPLETE APPLICATION FILE (RESTRUCTURED & FINAL)
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
import jinja2

# --- অ্যাপ এবং Firebase ইনিশিয়ালাইজেশন ---
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "final_build_secret_key_for_production_app")
SECRET_ADMIN_PATH = os.getenv("SECRET_ADMIN_PATH", "secure_admin_panel_final_build_e5f8")

try:
    firebase_creds_json_str = os.getenv('FIREBASE_CREDENTIALS_JSON')
    if not firebase_creds_json_str:
        cred = credentials.Certificate("firebase_credentials.json")
    else:
        firebase_creds_dict = json.loads(firebase_creds_json_str)
        cred = credentials.Certificate(firebase_creds_dict)
    
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("SUCCESS: Firebase Initialized.")
except Exception as e:
    print(f"FATAL ERROR: Could not initialize Firebase. Error: {e}")
    db = None

# --- ডেকোরেটর ---
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

def time_ago(dt):
    if not dt: return "N/A"
    if hasattr(dt, 'tzinfo') and dt.tzinfo: dt = dt.replace(tzinfo=None)
    diff = datetime.now() - dt
    if diff.days > 0: return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    if diff.seconds >= 3600: return f"{diff.seconds // 3600} hour{'s' if diff.seconds // 3600 > 1 else ''} ago"
    if diff.seconds >= 60: return f"{diff.seconds // 60} minute{'s' if diff.seconds // 60 > 1 else ''} ago"
    return "Just now"

# --- Authentication and Basic Routes ---
@app.route('/')
def index():
    is_logged_in = 'user_id' in session
    return render_template('index.html', is_logged_in=is_logged_in)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        facebook_profile = request.form.get('facebook_profile', '').strip()
        referrer_code = request.form.get('referrer_code', '').strip().upper()
        if not all([name, email, password]):
            flash("অনুগ্রহ করে নাম, ইমেইল এবং পাসওয়ার্ড পূরণ করুন।", "error")
            return redirect(url_for('signup'))
        try:
            user_record = auth.create_user(email=email, password=password, display_name=name)
            user_data = {
                'name': name, 'email': email, 'balance': 0.0,
                'facebook_profile': facebook_profile, 'referred_by': referrer_code, 
                'my_referral_code': generate_referral_code(), 'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('users').document(user_record.uid).set(user_data)
            # ... (আপনার রেফারেল লজিক এখানে) ...
            flash('রেজিস্ট্রেশন সফল হয়েছে!', 'success')
            return redirect(url_for('login'))
        except auth.EmailAlreadyExistsError:
            flash("এই ইমেইল দিয়ে ইতিমধ্যে একটি একাউন্ট খোলা আছে।", "error")
            return redirect(url_for('signup'))
        except Exception as e:
            flash("নিবন্ধনের সময় একটি অপ্রত্যাশিত সমস্যা হয়েছে।", "error")
            return redirect(url_for('signup'))
    is_logged_in = 'user_id' in session
    config_data = {'firebase_api_key': os.getenv('FIREBASE_API_KEY'), 'firebase_auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN'), 'firebase_project_id': os.getenv('FIREBASE_PROJECT_ID')}
    return render_template('signup.html', ref_code=request.args.get('ref', ''), config=config_data, is_logged_in=is_logged_in)

@app.route('/login')
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    is_logged_in = 'user_id' in session
    config_data = {'firebase_api_key': os.getenv('FIREBASE_API_KEY'), 'firebase_auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN'), 'firebase_project_id': os.getenv('FIREBASE_PROJECT_ID')}
    return render_template('login.html', config=config_data, is_logged_in=is_logged_in)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('আপনি সফলভাবে লগ আউট করেছেন।', 'info')
    return redirect(url_for('login'))

# --- User-Facing Pages ---
@app.route('/dashboard')
@login_required
def dashboard():
    try:
        user_id = session['user_id']
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            session.clear()
            flash("আপনার একাউন্ট খুঁজে পাওয়া যায়নি।", "error")
            return redirect(url_for('login'))
        user = user_doc.to_dict()
        is_banned = user.get('status') == 'banned'
        referral_link = url_for('signup', ref=user.get('my_referral_code'), _external=True)
        notifications_query = db.collection('notifications').where('user_id', '==', user_id).where('is_read', '==', False).order_by('timestamp', direction=firestore.Query.DESCENDING)
        notifications = [dict(doc.to_dict(), **{'id': doc.id}) for doc in notifications_query.stream()]
        submissions_query = db.collection('task_submissions').where('user_id', '==', user_id).order_by('submitted_at', direction=firestore.Query.DESCENDING).limit(10).stream()
        task_history = [doc.to_dict() for doc in submissions_query]
        referrals_query = db.collection('referrals').where('referrer_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
        my_referrals = [doc.to_dict() for doc in referrals_query]
        balance_query = db.collection('balance_history').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
        balance_history = [doc.to_dict() for doc in balance_query]
        return render_template('dashboard.html', user=user, is_banned=is_banned, referral_link=referral_link, notifications=notifications, task_history=task_history, my_referrals=my_referrals, balance_history=balance_history, is_logged_in=True)
    except Exception as e:
        flash("ড্যাশবোর্ড লোড করতে সমস্যা হয়েছে।", "error")
        return redirect(url_for('login'))

@app.route('/tasks')
@login_required
def tasks_page():
    user_id = session['user_id']
    submissions_query = db.collection('task_submissions').where('user_id', '==', user_id).stream()
    completed_task_ids = {sub.to_dict().get('task_id') for sub in submissions_query}
    tasks_query = db.collection('tasks').where('status', '==', 'active').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    available_tasks = []
    for task_doc in tasks_query:
        if task_doc.id not in completed_task_ids:
            task_data = task_doc.to_dict()
            task_data['id'] = task_doc.id
            available_tasks.append(task_data)
    return render_template('tasks.html', available_tasks=available_tasks)

@app.route('/task/<task_id>', methods=['GET', 'POST'])
@login_required
def view_task(task_id):
    user_id = session['user_id']
    task_ref = db.collection('tasks').document(task_id)
    task_doc = task_ref.get()
    if not task_doc.exists or task_doc.to_dict().get('status') != 'active':
        flash("এই টাস্কটি আর উপলব্ধ নেই।", "error")
        return redirect(url_for('dashboard'))
    task = task_doc.to_dict()
    existing_submission = db.collection('task_submissions').where('user_id', '==', user_id).where('task_id', '==', task_id).limit(1).stream()
    if len(list(existing_submission)) > 0:
        flash("আপনি ইতিমধ্যে এই কাজটি জমা দিয়েছেন।", "info")
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        submission_data = {
            'user_id': user_id, 'task_id': task_id, 'task_title': task.get('title'),
            'reward': task.get('reward'), 'status': 'pending', 'submitted_at': firestore.SERVER_TIMESTAMP
        }
        task_type = task.get('task_type')
        if task_type in ['fb_post_screenshot', 'yt_watch_screenshot', 'fb_page_like_screenshot']:
            proof_url = request.form.get('screenshot_url')
            if not proof_url or 'http' not in proof_url:
                flash("স্ক্রিনশট আপলোড ব্যর্থ হয়েছে।", "error")
                return redirect(url_for('view_task', task_id=task_id))
            submission_data['proof'] = {'screenshot_url': proof_url}
        elif task_type in ['ad_watch_timer', 'website_visit_timer']:
            submission_data['proof'] = {'completed_by_timer': True}
        else:
            flash("অজানা টাস্কের ধরণ।", "error")
            return redirect(url_for('dashboard'))
        db.collection('task_submissions').add(submission_data)
        flash("আপনার কাজ সফলভাবে জমা দেওয়া হয়েছে।", "success")
        return redirect(url_for('dashboard'))
    template_name = f"task_types/{task.get('task_type', 'default')}.html"
    try:
        return render_template(template_name, task=task, task_id=task_id)
    except jinja2.exceptions.TemplateNotFound:
        flash("এই টাস্কটি দেখার জন্য একটি সমস্যা হচ্ছে।", "error")
        return redirect(url_for('dashboard'))

@app.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw_page():
    user_id = session['user_id']
    user_doc = db.collection('users').document(user_id).get()
    if not user_doc.exists:
        flash("ব্যবহারকারী খুঁজে পাওয়া যায়নি।", "error")
        return redirect(url_for('dashboard'))
    user_data = user_doc.to_dict()
    current_balance = user_data.get('balance', 0)
    referrals_query = db.collection('referrals').where('referrer_id', '==', user_id)
    referral_count = len(list(referrals_query.stream()))
    account_created_at = user_data.get('created_at')
    is_account_old_enough = False
    if account_created_at:
        if hasattr(account_created_at, 'tzinfo') and account_created_at.tzinfo:
            account_created_at = account_created_at.replace(tzinfo=None)
        is_account_old_enough = account_created_at < (datetime.now() - timedelta(days=1))
    all_conditions_met = (current_balance >= 150) and (referral_count >= 2) and is_account_old_enough
    if request.method == 'POST':
        if not all_conditions_met:
            flash("আপনি উইথড্র করার জন্য যোগ্য নন।", "error")
            return redirect(url_for('withdraw_page'))
        amount = request.form.get('amount')
        if float(amount) > current_balance:
            flash("আপনার ব্যালেন্সের চেয়ে বেশি টাকা উইথড্র করা সম্ভব নয়।", "error")
            return redirect(url_for('withdraw_page'))
        session['withdraw_details'] = {'amount': amount, 'number': request.form.get('accountNumber'), 'method': request.form.get('method')}
        return redirect(url_for('gase_page'))
    eligibility_data = {
        'current_balance': current_balance, 'is_balance_eligible': current_balance >= 150,
        'referral_count': referral_count, 'are_referrals_eligible': referral_count >= 2,
        'account_created_at': account_created_at.strftime('%d %b, %Y') if account_created_at else "N/A",
        'is_account_old_enough': is_account_old_enough, 'all_conditions_met': all_conditions_met
    }
    return render_template('withdraw.html', eligibility=eligibility_data, user=user_data)

@app.route('/gase', methods=['GET', 'POST'])
@login_required
def gase_page():
    if 'withdraw_details' not in session:
        flash("অনুগ্রহ করে প্রথমে উইথড্রর তথ্য পূরণ করুন।", "info")
        return redirect(url_for('withdraw_page'))
    if request.method == 'POST':
        trx_info = {
            'payment_method': request.form.get('payment_method'),
            'sender_number': request.form.get('sender_number'),
            'trx_id': request.form.get('trx_id')
        }
        if not all(trx_info.values()):
            flash("অনুগ্রহ করে সব তথ্য সঠিকভাবে পূরণ করুন।", "error")
            return redirect(url_for('gase_page'))
        withdraw_details = session.pop('withdraw_details', None)
        if not withdraw_details:
             flash("সেশনের মেয়াদ শেষ হয়ে গেছে, আবার চেষ্টা করুন।", "error")
             return redirect(url_for('withdraw_page'))
        db.collection('withdraw_requests').add({
            'user_id': session['user_id'], 'status': 'pending_verification',
            'withdraw_details': withdraw_details, 'gas_fee_info': trx_info,
            'requested_at': firestore.SERVER_TIMESTAMP
        })
        flash("আপনার উইথড্র রিকোয়েস্ট সফলভাবে জমা দেওয়া হয়েছে।", "success")
        return redirect(url_for('dashboard'))
    return render_template('gase.html')

# --- API Routes ---
@app.route('/api/set_session', methods=['POST'])
def set_session():
    id_token = request.json.get('idToken')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        user_doc = db.collection('users').document(uid).get()
        user_data = user_doc.to_dict() if user_doc.exists else None
        if not user_data:
            user_info = auth.get_user(uid)
            user_data = {
                'name': user_info.display_name or 'Google User', 'email': user_info.email,
                'balance': 0.0, 'my_referral_code': generate_referral_code(),
                'created_at': firestore.SERVER_TIMESTAMP
            }
            db.collection('users').document(uid).set(user_data)
        session['user_id'] = uid
        session['user_name'] = user_data.get('name')
        return jsonify({"status": "success", "redirect_url": url_for('dashboard')})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 401

@app.route('/api/notification/mark-as-read/<notification_id>', methods=['POST'])
@login_required
def mark_notification_as_read(notification_id):
    try:
        notification_ref = db.collection('notifications').document(notification_id)
        if notification_ref.get().to_dict().get('user_id') == session['user_id']:
            notification_ref.update({'is_read': True})
            return jsonify({"status": "success"}), 200
        return jsonify({"status": "error", "message": "Permission denied"}), 403
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ==============================================================================
#           UNIQUE LINK ADMIN PANEL
# ==============================================================================
@app.route(f'/{SECRET_ADMIN_PATH}')
def admin_dashboard():
    pending_tasks_query = db.collection('task_submissions').where('status', '==', 'pending').order_by('submitted_at').stream()
    tasks_with_user_info = []
    for task_doc in pending_tasks_query:
        task_data = task_doc.to_dict()
        task_data['id'] = task_doc.id
        user_info_doc = db.collection('users').document(task_data.get('user_id')).get()
        task_data['user_info'] = user_info_doc.to_dict() if user_info_doc.exists else {'name': 'Unknown User'}
        tasks_with_user_info.append(task_data)
    return render_template('admin/admin_dashboard.html', pending_tasks=tasks_with_user_info, admin_path=SECRET_ADMIN_PATH)

# --- Admin Task Management ---
@app.route(f'/{SECRET_ADMIN_PATH}/manage-tasks')
def manage_tasks():
    tasks_query = db.collection('tasks').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    all_tasks = [dict(task.to_dict(), **{'id': task.id}) for task in tasks_query]
    return render_template('admin/manage_tasks.html', all_tasks=all_tasks, admin_path=SECRET_ADMIN_PATH)

@app.route(f'/{SECRET_ADMIN_PATH}/create-task', methods=['GET', 'POST'])
def create_task():
    if request.method == 'POST':
        task_type = request.form['task_type']
        task_data = {
            'title': request.form['title'], 'description': request.form['description'],
            'reward': float(request.form['reward']), 'task_type': task_type,
            'status': 'active', 'created_at': firestore.SERVER_TIMESTAMP
        }
        if task_type == 'fb_post_screenshot':
            task_data.update({'caption': request.form.get('caption', ''), 'image_url': request.form.get('image_url', '')})
        elif task_type in ['yt_watch_screenshot', 'fb_page_like_screenshot', 'ad_watch_timer', 'website_visit_timer']:
            task_data['target_url'] = request.form.get(f"{task_type.split('_')[0]}_target_url", '')
        if task_type in ['ad_watch_timer', 'website_visit_timer']:
            task_data['timer_duration'] = int(request.form.get('timer_duration', 30))
        db.collection('tasks').add(task_data)
        flash('নতুন টাস্ক সফলভাবে তৈরি করা হয়েছে।', 'success')
        return redirect(url_for('manage_tasks'))
    return render_template('admin/create_task.html', admin_path=SECRET_ADMIN_PATH)

@app.route(f'/{SECRET_ADMIN_PATH}/edit-task/<task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    task_ref = db.collection('tasks').document(task_id)
    if request.method == 'POST':
        task_ref.update({k: v for k, v in request.form.items()})
        flash('টাস্ক সফলভাবে আপডেট করা হয়েছে।', 'success')
        return redirect(url_for('manage_tasks'))
    return render_template('admin/edit_task.html', task=task_ref.get().to_dict(), task_id=task_id, admin_path=SECRET_ADMIN_PATH)

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
        db.collection('balance_history').add({'user_id': data['user_id'], 'amount': data['reward'], 'type': 'task_reward', 'description': f"Reward for: {data.get('task_title')}", 'timestamp': firestore.SERVER_TIMESTAMP})
        db.collection('notifications').add({'user_id': data['user_id'], 'message': f"অভিনন্দন! আপনার '{data.get('task_title')}' টাস্কটি অ্যাপ্রুভ করা হয়েছে এবং ৳{data.get('reward')} আপনার একাউন্টে যোগ করা হয়েছে。", 'is_read': False, 'timestamp': firestore.SERVER_TIMESTAMP, 'type': 'success'})
    try:
        update_in_transaction(db.transaction(), submission_ref)
        flash("টাস্ক সফলভাবে অ্যাপ্রুভ করা হয়েছে!", "success")
    except Exception as e:
        flash(f"একটি সমস্যা হয়েছে: {e}", "error")
    return redirect(url_for('admin_dashboard'))

@app.route(f'/{SECRET_ADMIN_PATH}/task/reject/<submission_id>')
def reject_task(submission_id):
    submission_ref = db.collection('task_submissions').document(submission_id)
    data = submission_ref.get().to_dict()
    if data and data.get('status') == 'pending':
        submission_ref.update({'status': 'rejected', 'processed_at': firestore.SERVER_TIMESTAMP})
        db.collection('notifications').add({'user_id': data['user_id'], 'message': f"দুঃখিত, আপনার '{data.get('task_title')}' টাস্কটি বাতিল করা হয়েছে।", 'is_read': False, 'timestamp': firestore.SERVER_TIMESTAMP, 'type': 'error'})
        flash("টাস্কটি বাতিল করা হয়েছে।", "info")
    else:
        flash("টাস্কটি খুঁজে পাওয়া যায়নি বা ইতিমধ্যে প্রসেস করা হয়ে গেছে।", "error")
    return redirect(url_for('admin_dashboard'))

# --- Admin User Management ---
@app.route(f'/{SECRET_ADMIN_PATH}/users')
def manage_users():
    try:
        search_email = request.args.get('search_email', '').strip()
        users_ref = db.collection('users')
        if search_email:
            query = users_ref.where('email', '==', search_email)
        else:
            query = users_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(50)
        
        all_users = []
        for doc in query.stream():
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            user_data['joined_ago'] = time_ago(user_data.get('created_at'))
            referrals_query = db.collection('referrals').where('referrer_id', '==', doc.id)
            user_data['referral_count'] = len(list(referrals_query.stream()))
            all_users.append(user_data)
        
        total_users_agg = db.collection('users').count().get()
        total_users = total_users_agg[0][0].value

        return render_template('admin/users_list.html', all_users=all_users, total_users=total_users, search_email=search_email, admin_path=SECRET_ADMIN_PATH)
    except Exception as e:
        flash("ব্যবহারকারীদের তথ্য আনতে সমস্যা হয়েছে।", "error")
        return redirect(url_for('admin_dashboard'))

@app.route(f'/{SECRET_ADMIN_PATH}/users/toggle-ban/<user_id>')
def toggle_user_ban(user_id):
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()
    if user_doc.exists:
        new_status = 'banned' if user_doc.to_dict().get('status', 'active') == 'active' else 'active'
        user_ref.update({'status': new_status})
        flash(f"ব্যবহারকারীর স্ট্যাটাস '{new_status}'-এ পরিবর্তন করা হয়েছে।", "success")
    return redirect(url_for('manage_users'))

@app.route(f'/{SECRET_ADMIN_PATH}/users/delete/<user_id>', methods=['POST'])
def delete_user(user_id):
    try:
        auth.delete_user(user_id)
        db.collection('users').document(user_id).delete()
        flash(f"ব্যবহারকারী সফলভাবে ডিলিট করা হয়েছে।", "success")
    except Exception as e:
        flash(f"ব্যবহারকারী ডিলিট করতে সমস্যা হয়েছে: {e}", "error")
    return redirect(url_for('manage_users'))

@app.route(f'/{SECRET_ADMIN_PATH}/users/update-note/<user_id>', methods=['POST'])
def update_admin_note(user_id):
    try:
        note_text = request.json.get('note', '')
        db.collection('users').document(user_id).update({'admin_note': note_text})
        return jsonify({"status": "success", "message": "নোট সেভ হয়েছে।"}), 200
    except Exception:
        return jsonify({"status": "error"}), 500

@app.route(f'/{SECRET_ADMIN_PATH}/users/update-balance/<user_id>', methods=['POST'])
def update_user_balance(user_id):
    try:
        new_balance = float(request.json.get('balance', 0))
        db.collection('users').document(user_id).update({'balance': new_balance})
        db.collection('balance_history').add({'user_id': user_id, 'amount': new_balance, 'type': 'admin_adjustment', 'description': 'Balance updated by admin.', 'timestamp': firestore.SERVER_TIMESTAMP})
        return jsonify({"status": "success", "message": "ব্যালেন্স আপডেট হয়েছে।"}), 200
    except Exception:
        return jsonify({"status": "error"}), 500

@app.route(f'/{SECRET_ADMIN_PATH}/users/update-marking-status/<user_id>', methods=['POST'])
def update_user_marking_status(user_id):
    try:
        marking_status = request.json.get('marking_status', '')
        db.collection('users').document(user_id).update({'marking_status': marking_status})
        return jsonify({"status": "success", "message": "স্ট্যাটাস আপডেট হয়েছে।"}), 200
    except Exception:
        return jsonify({"status": "error"}), 500

# --- Custom Error Handler ---
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

# --- Main Execution ---
if __name__ == '__main__':
    print(f"Admin panel accessible at: http://127.0.0.1:8080/{SECRET_ADMIN_PATH}")
    app.run(host='0.0.0.0', port=8080, debug=True)
