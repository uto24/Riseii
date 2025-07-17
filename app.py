# ==============================================================================
#           ULTIMATE & COMPLETE APPLICATION FILE (with Notifications): app.py
# ==============================================================================

import os
import uuid
import json
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, auth

# --- অ্যাপ এবং Firebase ইনিশিয়ালাইজেশন ---
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "final_build_secret_key_for_production_app")

# .env ফাইল থেকে গোপন অ্যাডমিন পাথ লোড করুন
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
    print("SUCCESS: Firebase Initialized for Final Application with Notifications.")
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

    config_data = {'firebase_api_key': os.getenv('FIREBASE_API_KEY'), 'firebase_auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN'), 'firebase_project_id': os.getenv('FIREBASE_PROJECT_ID')}
    return render_template('signup.html', ref_code=request.args.get('ref', ''), config=config_data)





@app.route('/login')
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    config_data = {'firebase_api_key': os.getenv('FIREBASE_API_KEY'), 'firebase_auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN'), 'firebase_project_id': os.getenv('FIREBASE_PROJECT_ID')}
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
        if not user_doc.exists:
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

@app.route('/api/notification/mark-as-read/<notification_id>', methods=['POST'])
@login_required
def mark_notification_as_read(notification_id):
    try:
        notification_ref = db.collection('notifications').document(notification_id)
        notification_doc = notification_ref.get()
        if notification_doc.exists and notification_doc.to_dict().get('user_id') == session['user_id']:
            notification_ref.update({'is_read': True})
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error", "message": "Permission denied"}), 403
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# app.py ফাইলের dashboard ফাংশনটির সম্পূর্ণ সংশোধিত রূপ
# app.py ফাইলের ভেতরে এই দুটি ফাংশন রাখুন বা প্রতিস্থাপন করুন
# ফাইলের উপরে from datetime import datetime, timedelta ইম্পোর্ট করা আছে কিনা নিশ্চিত করুন

@app.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw_page():
    """
    ইউজারের উইথড্র করার যোগ্যতা যাচাই করে এবং ফর্ম দেখায়।
    ফর্ম সাবমিট হলে তথ্য সেশনে সেভ করে গ্যাস ফি পেইজে রিডাইরেক্ট করে।
    """
    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        flash("ব্যবহারকারী খুঁজে পাওয়া যায়নি।", "error")
        return redirect(url_for('dashboard'))

    user_data = user_doc.to_dict()

    # --- শর্তগুলো পরীক্ষা করা ---
    
    # শর্ত ১: সর্বনিম্ন ব্যালেন্স
    current_balance = user_data.get('balance', 0)
    is_balance_eligible = current_balance >= 150

    # শর্ত ২: সর্বনিম্ন রেফারেল
    # এই কোয়েরিটি কার্যকর করার জন্য Firestore Index প্রয়োজন হতে পারে
    referrals_query = db.collection('referrals').where('referrer_id', '==', user_id)
    referral_count = len(list(referrals_query.stream()))
    are_referrals_eligible = referral_count >= 5

    # শর্ত ৩: অ্যাকাউন্টের বয়স
    account_created_at = user_data.get('created_at')
    is_account_old_enough = False
    if account_created_at:
        # সময়কে timezone-aware থেকে naive-এ রূপান্তর করা হচ্ছে
        if hasattr(account_created_at, 'tzinfo') and account_created_at.tzinfo:
            account_created_at = account_created_at.replace(tzinfo=None)
        
        three_days_ago = datetime.now() - timedelta(days=3)
        is_account_old_enough = account_created_at < three_days_ago

    # সমস্ত শর্ত পূরণ হয়েছে কিনা তা চেক করা
    all_conditions_met = is_balance_eligible and are_referrals_eligible and is_account_old_enough

    # যখন ইউজার 'Get Passkey & Proceed' বাটনে ক্লিক করে
    if request.method == 'POST':
        # যদি ইউজার যোগ্য না হয়, তাহলে তাকে আবার উইথড্র পেইজেই ফেরত পাঠানো হবে
        if not all_conditions_met:
            flash("দুঃখিত, আপনি এখনো উইথড্র করার জন্য সম্পূর্ণ যোগ্য হননি।", "error")
            return redirect(url_for('withdraw_page'))
            
        # ফর্ম থেকে তথ্য সংগ্রহ করা
        amount_to_withdraw = request.form.get('amount')
        account_number = request.form.get('accountNumber')
        payment_method = request.form.get('method')
        
        # ব্যালেন্সের চেয়ে বেশি উইথড্র করার চেষ্টা করছে কিনা তা পরীক্ষা করা
        if float(amount_to_withdraw) > current_balance:
            flash("আপনার ব্যালেন্সের চেয়ে বেশি টাকা উইথড্র করা সম্ভব নয়।", "error")
            return redirect(url_for('withdraw_page'))

        # তথ্যগুলো সেশনে সেভ করে গ্যাস ফি পেইজে পাঠানো হচ্ছে
        session['withdraw_details'] = {
            'amount': amount_to_withdraw,
            'number': account_number,
            'method': payment_method
        }
        return redirect(url_for('gase_page'))

    # GET রিকোয়েস্টের জন্য টেমপ্লেটে ডেটা পাঠানো হচ্ছে
    eligibility_data = {
        'current_balance': current_balance,
        'is_balance_eligible': is_balance_eligible,
        'referral_count': referral_count,
        'are_referrals_eligible': are_referrals_eligible,
        'account_created_at': account_created_at.strftime('%d %b, %Y') if account_created_at else "N/A",
        'is_account_old_enough': is_account_old_enough,
        'all_conditions_met': all_conditions_met
    }

    return render_template('withdraw.html', eligibility=eligibility_data, user=user_data)


@app.route('/gase', methods=['GET', 'POST'])
@login_required
def gase_page():
    """
    গ্যাস ফি পেমেন্টের তথ্য গ্রহণ করে এবং চূড়ান্ত উইথড্র রিকোয়েস্ট তৈরি করে।
    """
    user_id = session['user_id']
    
    # যদি সেশনে উইথড্রর তথ্য না থাকে, তাহলে ইউজারকে আবার উইথড্র পেইজে পাঠানো হবে
    if 'withdraw_details' not in session:
        flash("অনুগ্রহ করে প্রথমে উইথড্রর তথ্য পূরণ করুন।", "info")
        return redirect(url_for('withdraw_page'))

    # যখন ইউজার গ্যাস ফি পেমেন্টের তথ্য সাবমিট করবে
    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        sender_number = request.form.get('sender_number')
        trx_id = request.form.get('trx_id')

        if not all([payment_method, sender_number, trx_id]):
            flash("অনুগ্রহ করে গ্যাস ফি পেমেন্টের সব তথ্য সঠিকভাবে পূরণ করুন।", "error")
            return redirect(url_for('gase_page'))

        # সেশন থেকে উইথড্রর তথ্য পুনরুদ্ধার করা
        withdraw_details = session.pop('withdraw_details', None) # তথ্য ব্যবহার করার পর সেশন থেকে মুছে ফেলা হচ্ছে
        if not withdraw_details:
             flash("সেশনের মেয়াদ শেষ হয়ে গেছে, অনুগ্রহ করে আবার চেষ্টা করুন।", "error")
             return redirect(url_for('withdraw_page'))

        # একটি নতুন 'withdraw_requests' কালেকশনে রিকোয়েস্ট সেভ করা
        db.collection('withdraw_requests').add({
            'user_id': user_id,
            'status': 'pending_verification', # স্ট্যাটাস: অ্যাডমিন এখন এটি রিভিউ করবে
            'withdraw_details': withdraw_details,
            'gas_fee_info': {
                'payment_method': payment_method,
                'sender_number': sender_number,
                'trx_id': trx_id
            },
            'requested_at': firestore.SERVER_TIMESTAMP
        })

        flash("আপনার উইথড্র রিকোয়েস্ট এবং পেমেন্টের তথ্য সফলভাবে জমা দেওয়া হয়েছে। অ্যাডমিন ভেরিফাই করার পর আপনার পেমেন্ট প্রসেস করা হবে।", "success")
        return redirect(url_for('dashboard'))


    # GET রিকোয়েস্টের জন্য gase.html পেইজটি রেন্ডার করা
    return render_template('gase.html')






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

    # ১. Fetching notifications (আপনার কোডে এটি আছে)
    notifications_query = db.collection('notifications').where('user_id', '==', user_id).where('is_read', '==', False).order_by('timestamp', direction=firestore.Query.DESCENDING)
    notifications = [dict(doc.to_dict(), **{'id': doc.id}) for doc in notifications_query.stream()]
    
    # ২. Fetching task submission history (আপনার কোডে এটি আছে)
    submissions_query = db.collection('task_submissions').where('user_id', '==', user_id).order_by('submitted_at', direction=firestore.Query.DESCENDING).limit(10).stream()
    task_history = [doc.to_dict() for doc in submissions_query]

    # --- নতুন করে যোগ করা অংশ ---
    # ৩. Fetching Referral History
    referrals_query = db.collection('referrals').where('referrer_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
    my_referrals = [doc.to_dict() for doc in referrals_query]

    # ৪. Fetching Balance History
    balance_query = db.collection('balance_history').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10).stream()
    balance_history = [doc.to_dict() for doc in balance_query]
    # --- নতুন অংশ শেষ ---

    # --- render_template এ নতুন ভেরিয়েবলগুলো যোগ করা ---
    return render_template(
        'dashboard.html', 
        user=user, 
        referral_link=referral_link, 
        notifications=notifications, 
        task_history=task_history,
        my_referrals=my_referrals,      # <-- এই ভেরিয়েবলটি যোগ করা হয়েছে
        balance_history=balance_history # <-- এই ভেরিয়েবলটিও যোগ করা হয়েছে
    )
    # app.py -> view_task ফাংশনটি ডিবাগিং এর জন্য পরিবর্তন করুন

# app.py ফাইলের ভেতরে এই ফাংশনটি রাখুন বা প্রতিস্থাপন করুন


# app.py ফাইলের ভেতরে এই নতুন ফাংশনটি যোগ করুন

@app.route('/tasks')
@login_required
def tasks_page():
    """
    সমস্ত অ্যাক্টিভ টাস্কের একটি তালিকা দেখায়।
    """
    user_id = session['user_id']
    
    # প্রথমে ইউজারের করা সব টাস্কের আইডিগুলো একটি সেটে নিয়ে আসা হচ্ছে
    submissions_query = db.collection('task_submissions').where('user_id', '==', user_id).stream()
    completed_task_ids = {sub.to_dict().get('task_id') for sub in submissions_query}

    # এখন সব 'active' টাস্ক আনা হচ্ছে
    tasks_query = db.collection('tasks').where('status', '==', 'active').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    
    available_tasks = []
    for task_doc in tasks_query:
        task_id = task_doc.id
        # যদি টাস্কটি ইতিমধ্যে করা না হয়ে থাকে, তাহলেই লিস্টে যোগ করা হবে
        if task_id not in completed_task_ids:
            task_data = task_doc.to_dict()
            task_data['id'] = task_id
            available_tasks.append(task_data)
            
    return render_template('tasks.html', available_tasks=available_tasks)



@app.route('/task/<task_id>', methods=['GET', 'POST'])
@login_required
def view_task(task_id):
   
    user_id = session['user_id']
    task_ref = db.collection('tasks').document(task_id)
    task_doc = task_ref.get()

    # ১. টাস্কটি ডাটাবেসে আছে কিনা বা active কিনা তা পরীক্ষা করা
    if not task_doc.exists or task_doc.to_dict().get('status') != 'active':
        flash("দুঃখিত, এই টাস্কটি আর উপলব্ধ নেই।", "error")
        return redirect(url_for('dashboard')) # পরিবর্তন: tasks_page এর পরিবর্তে dashboard
    
    task = task_doc.to_dict()

    # ২. ইউজার এই টাস্কটি ইতিমধ্যে জমা দিয়েছে কিনা তা পরীক্ষা করা
    existing_submission_query = db.collection('task_submissions') \
                                  .where('user_id', '==', user_id) \
                                  .where('task_id', '==', task_id) \
                                  .limit(1) \
                                  .stream()

    if len(list(existing_submission_query)) > 0:
        flash("আপনি ইতিমধ্যে এই কাজটি জমা দিয়েছেন।", "info")
        return redirect(url_for('dashboard')) # পরিবর্তন: tasks_page এর পরিবর্তে dashboard

    # ৩. ফর্ম সাবমিশন হ্যান্ডেল করা (POST request)
    if request.method == 'POST':
        # একটি বেস সাবমিশন ডিকশনারি তৈরি করা
        submission_data = {
            'user_id': user_id,
            'task_id': task_id,
            'task_title': task.get('title', 'Untitled Task'),
            'reward': task.get('reward', 0),
            'status': 'pending',
            'submitted_at': firestore.SERVER_TIMESTAMP
        }
        
        task_type = task.get('task_type')

        # ক. স্ক্রিনশট-ভিত্তিক টাস্কগুলোর জন্য প্রুফ গ্রহণ
        if task_type in ['fb_post_screenshot', 'yt_watch_screenshot', 'fb_page_like_screenshot', 'screenshot_upload_task']:
            proof_url = request.form.get('screenshot_url')
            if not proof_url or 'http' not in proof_url:
                flash("স্ক্রিনশট আপলোড ব্যর্থ হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।", "error")
                return redirect(url_for('view_task', task_id=task_id))
            
            submission_data['proof'] = {'screenshot_url': proof_url}
        
        # খ. টাইমার-ভিত্তিক টাস্কগুলোর জন্য প্রুফ গ্রহণ
        elif task_type in ['ad_watch_timer', 'website_visit_timer']:
            submission_data['proof'] = {'completed_by_timer': True}
        
        # গ. অন্যান্য বা অজানা টাস্কের ধরণ
        else:
            flash("অজানা টাস্কের ধরণ। সাবমিট করা সম্ভব নয়।", "error")
            return redirect(url_for('dashboard')) # পরিবর্তন: tasks_page এর পরিবর্তে dashboard

        # ৪. ডাটাবেসে সাবমিশন সেভ করা
        db.collection('task_submissions').add(submission_data)
        flash("আপনার কাজ সফলভাবে জমা দেওয়া হয়েছে। পর্যালোচনার পর ব্যালেন্স যোগ করা হবে।", "success")
        return redirect(url_for('dashboard')) # পরিবর্তন: tasks_page এর পরিবর্তে dashboard

    # ৫. সঠিক টেমপ্লেট রেন্ডার করা (GET request)
    template_name = f"task_types/{task.get('task_type', 'default')}.html"
    
    try:
        return render_template(template_name, task=task, task_id=task_id)
    except Exception as e:
        # যদি কোনো কারণে টেমপ্লেট ফাইল খুঁজে পাওয়া না যায়
        print(f"Template not found for '{template_name}'. Error: {e}")
        flash("এই টাস্কটি দেখার জন্য একটি সমস্যা হচ্ছে।", "error")
        return redirect(url_for('dashboard')) # পরিবর্তন: tasks_page এর পরিবর্তে dashboard
    
# --- UNIQUE LINK ADMIN PANEL ---
@app.route(f'/{SECRET_ADMIN_PATH}')
def admin_dashboard():
    # প্রথমে সব পেন্ডিং টাস্ক আনা হচ্ছে
    pending_tasks_query = db.collection('task_submissions').where('status', '==', 'pending').order_by('submitted_at').stream()
    
    tasks_with_user_info = []
    
    # প্রতিটি টাস্কের জন্য ইউজারের তথ্য আনা হচ্ছে
    for task_doc in pending_tasks_query:
        task_data = task_doc.to_dict()
        task_data['id'] = task_doc.id  # সাবমিশন ডকুমেন্ট আইডি

        user_id = task_data.get('user_id')
        if user_id:
            try:
                # টাস্কের সাথে সম্পর্কিত ইউজারের ডকুমেন্ট আনা হচ্ছে
                user_info_doc = db.collection('users').document(user_id).get()
                if user_info_doc.exists:
                    # টাস্কের ডেটার সাথে ইউজারের নাম ও ইমেইল যোগ করা হচ্ছে
                    task_data['user_info'] = user_info_doc.to_dict()
                else:
                    # যদি কোনো কারণে ইউজার খুঁজে পাওয়া না যায়
                    task_data['user_info'] = {'name': 'Unknown User', 'email': 'N/A'}
            except Exception as e:
                print(f"Could not fetch user {user_id}: {e}")
                task_data['user_info'] = {'name': 'Error Fetching', 'email': 'N/A'}
        else:
            task_data['user_info'] = {'name': 'No User ID', 'email': 'N/A'}
            
        tasks_with_user_info.append(task_data)
        
    return render_template('admin_dashboard.html', pending_tasks=tasks_with_user_info, admin_path=SECRET_ADMIN_PATH)
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
    submission_data = submission_ref.get().to_dict()
    if submission_data and submission_data.get('status') == 'pending':
        submission_ref.update({'status': 'rejected', 'processed_at': firestore.SERVER_TIMESTAMP})
        db.collection('notifications').add({'user_id': submission_data['user_id'], 'message': f"দুঃখিত, আপনার '{submission_data.get('task_title')}' টাস্কটি বাতিল করা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।", 'is_read': False, 'timestamp': firestore.SERVER_TIMESTAMP, 'type': 'error'})
        flash("টাস্কটি বাতিল করা হয়েছে।", "info")
    else:
        flash("টাস্কটি খুঁজে পাওয়া যায়নি অথবা এটি ইতিমধ্যে প্রসেস করা হয়ে গেছে।", "error")
    return redirect(url_for('admin_dashboard'))

@app.route(f'/{SECRET_ADMIN_PATH}/manage-tasks')
def manage_tasks():
    tasks_query = db.collection('tasks').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    all_tasks = [dict(task.to_dict(), **{'id': task.id}) for task in tasks_query]
    return render_template('manage_tasks.html', all_tasks=all_tasks, admin_path=SECRET_ADMIN_PATH)

@app.route(f'/{SECRET_ADMIN_PATH}/create-task', methods=['GET', 'POST'])
def create_task():
    if request.method == 'POST':
        task_data = {
            'title': request.form['title'],
            'description': request.form['description'],
            'reward': float(request.form['reward']),
            'task_type': request.form['task_type'],
            'status': 'active',
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        task_type = task_data['task_type']
        
        if task_type == 'fb_post_screenshot':
            task_data['caption'] = request.form.get('caption', '')
            task_data['image_url'] = request.form.get('image_url', '')
        
        elif task_type == 'yt_watch_screenshot':
            task_data['target_url'] = request.form.get('yt_target_url', '')

        elif task_type == 'ad_watch_timer':
            task_data['target_url'] = request.form.get('ad_target_url', '')
            task_data['timer_duration'] = int(request.form.get('timer_duration', 30))
        
        # নতুন টাস্কের ডেটা গ্রহণ
        elif task_type == 'fb_page_like_screenshot':
            task_data['target_url'] = request.form.get('fb_page_url', '')
            
        elif task_type == 'website_visit_timer':
            task_data['target_url'] = request.form.get('website_url', '')
            task_data['timer_duration'] = int(request.form.get('website_timer_duration', 60))

        db.collection('tasks').add(task_data)
        flash('নতুন টাস্ক সফলভাবে তৈরি করা হয়েছে।', 'success')
        return redirect(url_for('manage_tasks'))
        
    return render_template('create_task.html', admin_path=SECRET_ADMIN_PATH)

@app.route(f'/{SECRET_ADMIN_PATH}/edit-task/<task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    task_ref = db.collection('tasks').document(task_id)
    if request.method == 'POST':
        task_ref.update({'title': request.form['title'], 'description': request.form['description'], 'category': request.form['category'], 'task_type': request.form['task_type'], 'reward': float(request.form['reward']), 'target_url': request.form['target_url'], 'icon_class': request.form['icon_class']})
        flash('টাস্ক সফলভাবে আপডেট করা হয়েছে।', 'success')
        return redirect(url_for('manage_tasks'))
    return render_template('edit_task.html', task=task_ref.get().to_dict(), task_id=task_id, admin_path=SECRET_ADMIN_PATH)

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
