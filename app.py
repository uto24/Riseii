# ==============================================================================
#           ULTIMATE & COMPLETE APPLICATION FILE (with Notifications): app.py
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
from google.cloud.firestore_v1.base_query import FieldFilter
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
# app.py -> signup ফাংশনটি আপডেট করুন

# app.py ফাইলের ভেতরে এই ফাংশনটি রাখুন বা প্রতিস্থাপন করুন

# app.py ফাইলের ভেতরে এই ফাংশনটি রাখুন বা প্রতিস্থাপন করুন

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    ব্যবহারকারী নিবন্ধনের জন্য GET এবং POST রিকোয়েস্ট হ্যান্ডেল করে।
    নতুন ব্যবহারকারীর স্ট্যাটাস 'inactive' সেট করে এবং রেফারেল কোড রেকর্ড করে।
    সাইনআপের সময় কোনো বোনাস দেওয়া হয় না।
    """
    # যদি ইউজার ইতিমধ্যে লগইন করা থাকে, তাকে ড্যাশবোর্ডে পাঠানো হবে
    if 'user_id' in session: 
        return redirect(url_for('dashboard'))

    # যখন ইউজার ফর্ম সাবমিট করবে
    if request.method == 'POST':
        # ফর্ম থেকে সমস্ত তথ্য সংগ্রহ এবং পরিষ্কার করা হচ্ছে
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')
        facebook_profile = request.form.get('facebook_profile', '').strip()
        referrer_code = request.form.get('referrer_code', '').strip().upper()

        # প্রাথমিক ভ্যালিডেশন
        if not all([name, email, password]):
            flash("অনুগ্রহ করে নাম, ইমেইল এবং পাসওয়ার্ড পূরণ করুন।", "error")
            return redirect(url_for('signup'))
        
        try:
            # Firebase Authentication ব্যবহার করে নতুন ইউজার তৈরি
            user_record = auth.create_user(
                email=email,
                password=password,
                display_name=name
            )
            
            # Firestore-এ সেভ করার জন্য ইউজার ডেটা প্রস্তুত করা
            user_data = {
                'name': name, 
                'email': email, 
                'balance': 0.0,
                'facebook_profile': facebook_profile,
                'referred_by': referrer_code, # <-- রেফারেল কোড সেভ করা হচ্ছে
                'my_referral_code': generate_referral_code(),
                'account_status': 'inactive', # <-- অ্যাকাউন্টের ডিফল্ট স্ট্যাটাস
                'created_at': firestore.SERVER_TIMESTAMP
            }
            
            # প্রজেক্ট ১ (db_auth) -এ ইউজার ডেটা সেভ করা হচ্ছে
            db.collection('users').document(user_record.uid).set(user_data) # আপনার DB client অনুযায়ী (db/db_auth)
            
            # --- গুরুত্বপূর্ণ: সাইনআপের সময় আর কোনো রেফারেল বোনাস দেওয়া হবে না ---
            # বোনাস শুধুমাত্র অ্যাকাউন্ট অ্যাক্টিভেশনের পরেই দেওয়া হবে।

            flash('আপনার রেজিস্ট্রেশন সফল হয়েছে! একাউন্টটি ব্যবহার করার জন্য অনুগ্রহ করে লগইন করে অ্যাক্টিভেট করুন।', 'success')
            return redirect(url_for('login'))
            
        except auth.EmailAlreadyExistsError:
            flash("এই ইমেইল দিয়ে ইতিমধ্যে একটি একাউন্ট খোলা আছে।", "error")
            return redirect(url_for('signup'))
        except Exception as e:
            print(f"ERROR during signup for email {email}: {e}")
            flash("নিবন্ধনের সময় একটি অপ্রত্যাশিত সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।", "error")
            return redirect(url_for('signup'))

    # GET রিকোয়েস্টের জন্য (যখন পেইজটি প্রথম লোড হয়)
    is_logged_in = 'user_id' in session
    config_data = {
        'firebase_api_key': os.getenv('FIREBASE_API_KEY'),
        'firebase_auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN'),
        'firebase_project_id': os.getenv('FIREBASE_PROJECT_ID')
    }
    return render_template(
        'signup.html', 
        ref_code=request.args.get('ref', ''), 
        config=config_data, 
        is_logged_in=is_logged_in
    )
    # GET রিকোয়েস্টের জন্য (যখন পেইজটি প্রথম লোড হয়)
    is_logged_in = 'user_id' in session
    config_data = {
        'firebase_api_key': os.getenv('FIREBASE_API_KEY'),
        'firebase_auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN'),
        'firebase_project_id': os.getenv('FIREBASE_PROJECT_ID')
    }
    return render_template(
        'signup.html', 
        ref_code=request.args.get('ref', ''), 
        config=config_data, 
        is_logged_in=is_logged_in
    )

# app.py ফাইলের অ্যাডমিন প্যানেল সেকশনে যোগ করুন



# app.py -> অ্যাডমিন প্যানেল সেকশনে যোগ করুন

@app.route(f'/{SECRET_ADMIN_PATH}/users/delete/<user_id>', methods=['POST'])
def delete_user(user_id):
    """
    একজন ব্যবহারকারীকে Firebase Authentication এবং Firestore উভয় জায়গা থেকে ডিলিট করে।
    """
    try:
        # Firebase Authentication থেকে ইউজার ডিলিট
        auth.delete_user(user_id)
        
        # Firestore থেকে ইউজারের ডকুমেন্ট ডিলিট
        db.collection('users').document(user_id).delete()
        
        # (ঐচ্ছিক) ইউজারের সম্পর্কিত অন্যান্য ডেটাও ডিলিট করা যেতে পারে, যেমন task_submissions
        
        flash(f"ব্যবহারকারী (ID: {user_id}) সফলভাবে ডিলিট করা হয়েছে।", "success")
    except Exception as e:
        flash(f"ব্যবহারকারী ডিলিট করার সময় একটি সমস্যা হয়েছে: {e}", "error")
    
    return redirect(url_for('manage_users'))

    # app.py -> অ্যাডমিন প্যানেল সেকশনে যোগ করুন

@app.route(f'/{SECRET_ADMIN_PATH}/activations/reject/<req_id>')
def reject_activation(req_id):
    """
    একটি একাউন্ট অ্যাক্টিভেশন রিকোয়েস্ট বাতিল করে।
    """
    try:
        req_ref = db.collection('activation_requests').document(req_id)
        req_doc = req_ref.get()
        
        if req_doc.exists and req_doc.to_dict().get('status') == 'pending':
            # স্ট্যাটাস 'rejected' এ পরিবর্তন করা হচ্ছে
            req_ref.update({
                'status': 'rejected',
                'processed_at': firestore.SERVER_TIMESTAMP
            })
            
            # (ঐচ্ছিক) ইউজারকে নোটিফিকেশন পাঠানো
            req_data = req_doc.to_dict()
            db.collection('notifications').add({
                'user_id': req_data['user_id'],
                'message': "দুঃখিত, আপনার একাউন্ট অ্যাক্টিভেশন রিকোয়েস্টটি বাতিল করা হয়েছে। পেমেন্টের তথ্যে কোনো সমস্যা থাকতে পারে। অনুগ্রহ করে সাপোর্টে যোগাযোগ করুন।",
                'is_read': False,
                'type': 'error',
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            
            flash("অ্যাক্টিভেশন রিকোয়েস্টটি সফলভাবে বাতিল করা হয়েছে।", "success")
        else:
            flash("এই রিকোয়েস্টটি খুঁজে পাওয়া যায়নি অথবা এটি ইতিমধ্যে প্রসেস করা হয়ে গেছে।", "warning")
            
    except Exception as e:
        flash(f"রিকোয়েস্ট বাতিল করার সময় একটি সমস্যা হয়েছে: {e}", "error")

    return redirect(url_for('manage_activations'))

@app.route(f'/{SECRET_ADMIN_PATH}/users/update-balance/<user_id>', methods=['POST'])
def update_user_balance(user_id):
    """
    AJAX রিকোয়েস্টের মাধ্যমে একজন ইউজারের ব্যালেন্স আপডেট করে।
    """
    try:
        data = request.get_json()
        new_balance = float(data.get('balance', 0))
        
        user_ref = db.collection('users').document(user_id)
        user_ref.update({'balance': new_balance})
        
        # (ঐচ্ছিক) ব্যালেন্স হিস্টোরিতে একটি অ্যাডমিন অ্যাডজাস্টমেন্ট এন্ট্রি যোগ করা যেতে পারে
        db.collection('balance_history').add({
            'user_id': user_id,
            'amount': new_balance,
            'type': 'admin_adjustment',
            'description': 'Balance updated by admin.',
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({"status": "success", "message": "ব্যালেন্স সফলভাবে আপডেট হয়েছে।"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": "ব্যালেন্স আপডেট করার সময় সমস্যা হয়েছে।"}), 500
# app.py -> manage_users ফাংশনটি প্রতিস্থাপন করুন

@app.route(f'/{SECRET_ADMIN_PATH}/users', methods=['GET'])
def manage_users():
    """
    সমস্ত ব্যবহারকারীর তালিকা দেখায় এবং ইমেইল দিয়ে সার্চ করার সুবিধা দেয়।
    """
    try:
        search_email = request.args.get('search_email', '').strip()
        
        users_ref = db.collection('users')
        
        # যদি সার্চ করা হয়
        if search_email:
            users_query = users_ref.where('email', '==', search_email).stream()
        else:
            # যদি সার্চ করা না হয়, তাহলে সব ইউজারকে আনা হচ্ছে
            users_query = users_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(25).stream() # পারফরম্যান্সের জন্য লিমিট যোগ করা হলো
        
        all_users = []
        for user_doc in users_query:
            user_data = user_doc.to_dict()
            user_data['id'] = user_doc.id
            
            # --- প্রতিটি ইউজারের রেফারেল সংখ্যা গণনা ---
            referrals_query = db.collection('referrals').where('referrer_id', '==', user_doc.id)
            # .stream() ব্যবহার না করে সরাসরি .get() ব্যবহার করে size প্রপার্টি নেওয়া যায় (ছোট ডেটাসেটের জন্য)
            # কিন্তু বড় ডেটাসেটের জন্য এটি খরচসাপেক্ষ হতে পারে।
            # একটি বিকল্প হলো 'users' ডকুমেন্টে একটি 'referral_count' ফিল্ড রাখা এবং রেফারেলের সময় সেটি আপডেট করা।
            # எளிமையের জন্য আমরা এখন সরাসরি গণনা করছি।
            referral_count = len(list(referrals_query.stream()))
            user_data['referral_count'] = referral_count
            
            all_users.append(user_data)
        
        # মোট ব্যবহারকারীর সংখ্যা গণনা
        total_users = len(list(db.collection('users').stream()))

        return render_template('users_list.html', 
                               all_users=all_users, 
                               total_users=total_users,
                               search_email=search_email,
                               admin_path=SECRET_ADMIN_PATH)
        
    except Exception as e:
        print(f"Error fetching users: {e}")
        flash(f"ব্যবহারকারীদের তথ্য আনতে একটি সমস্যা হয়েছে।", "error")
        return redirect(url_for('admin_dashboard'))
        
@app.route('/login')
def login():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    config_data = {'firebase_api_key': os.getenv('FIREBASE_API_KEY'), 'firebase_auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN'), 'firebase_project_id': os.getenv('FIREBASE_PROJECT_ID')}
    return render_template('login.html', config=config_data)

# app.py -> অ্যাডমিন প্যানেল সেকশনে যোগ করুন

@app.route(f'/{SECRET_ADMIN_PATH}/users/update-note/<user_id>', methods=['POST'])
def update_admin_note(user_id):
  
    try:
        data = request.get_json()
        note_text = data.get('note', '')
        
        user_ref = db.collection('users').document(user_id)
        user_ref.update({'admin_note': note_text})
        
        return jsonify({"status": "success", "message": "নোট সফলভাবে সেভ হয়েছে।"}), 200
    except Exception as e:
        print(f"Error updating note for user {user_id}: {e}")
        return jsonify({"status": "error", "message": "নোট সেভ করার সময় সমস্যা হয়েছে।"}), 500
@app.route(f'/{SECRET_ADMIN_PATH}/users/toggle-ban/<user_id>')
def toggle_user_ban(user_id):
    """
    একজন ব্যবহারকারীকে ব্যান বা আন-ব্যান করে।
    """
    try:
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if user_doc.exists:
            current_status = user_doc.to_dict().get('status', 'active')
            new_status = 'banned' if current_status == 'active' else 'active'
            
            user_ref.update({'status': new_status})
            
            flash(f"ব্যবহারকারীর স্ট্যাটাস সফলভাবে '{new_status}'-এ পরিবর্তন করা হয়েছে।", "success")
        else:
            flash("ব্যবহারকারীকে খুঁজে পাওয়া যায়নি।", "error")
    except Exception as e:
        flash(f"স্ট্যাটাস পরিবর্তন করার সময় একটি সমস্যা হয়েছে: {e}", "error")

    return redirect(url_for('manage_users'))
# app.py ফাইলের শেষে যোগ করুন

# --- Custom Error Handler for 404 Not Found ---
@app.errorhandler(404)
def not_found_error(error):
  
    return render_template('404.html'), 404
    
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

# app.py -> withdraw_page ফাংশনটি সম্পূর্ণ প্রতিস্থাপন করুন

# app.py ফাইলের ভেতরে এই ফাংশনটি রাখুন বা প্রতিস্থাপন করুন
# ফাইলের উপরে from datetime import datetime, timedelta এবং FieldFilter ইম্পোর্ট করা আছে কিনা নিশ্চিত করুন

@app.route('/withdraw', methods=['GET', 'POST'])
@login_required
def withdraw_page():
    """
    ব্যবহারকারীর উইথড্র পেইজ পরিচালনা করে। যোগ্যতা যাচাই করে,
    ফর্ম সাবমিশন গ্রহণ করে এবং উইথড্রর ইতিহাস দেখায়।
    """
    try:
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

        # শর্ত ২: সর্বনিম্ন রেফারেল (রিয়েল-টাইম গণনা)
        referrals_query = db.collection('referrals').where(filter=FieldFilter('referrer_id', '==', user_id))
        referral_count = len(list(referrals_query.stream()))
        # আপনার শর্ত অনুযায়ী রেফারেল সংখ্যা পরিবর্তন করুন (যেমন: >= 5)
        are_referrals_eligible = referral_count >= 0

        # শর্ত ৩: অ্যাকাউন্টের বয়স
        account_created_at = user_data.get('created_at')
        is_account_old_enough = False
        if account_created_at:
            if hasattr(account_created_at, 'tzinfo') and account_created_at.tzinfo:
                account_created_at = account_created_at.replace(tzinfo=None)
            # আপনার শর্ত অনুযায়ী দিন পরিবর্তন করুন (যেমন: days=3)
            is_account_old_enough = (datetime.now() - account_created_at) > timedelta(days=1)

        all_conditions_met = is_balance_eligible and are_referrals_eligible and is_account_old_enough

        # যখন ইউজার ফর্ম সাবমিট করবে
        if request.method == 'POST':
            if not all_conditions_met:
                flash("দুঃখিত, আপনি এখনো উইথড্র করার জন্য যোগ্য হননি।", "error")
                return redirect(url_for('withdraw_page'))
                
            amount_to_withdraw = float(request.form.get('amount'))
            account_number = request.form.get('accountNumber')
            payment_method = request.form.get('method')
            
            if amount_to_withdraw > current_balance:
                flash("আপনার ব্যালেন্সের চেয়ে বেশি টাকা উইথড্র করা সম্ভব নয়।", "error")
                return redirect(url_for('withdraw_page'))
                
            if amount_to_withdraw < 150:
                flash("সর্বনিম্ন ১৫০ টাকা উইথড্র করতে হবে।", "error")
                return redirect(url_for('withdraw_page'))

            # --- Transaction ব্যবহার করে ব্যালেন্স কাটা এবং রিকোয়েস্ট তৈরি ---
            @firestore.transactional
            def withdraw_request_transaction(transaction, user_ref_txn, amount):
                snapshot = user_ref_txn.get(transaction=transaction)
                current_balance_in_txn = snapshot.to_dict().get('balance', 0)

                if current_balance_in_txn < amount:
                    raise ValueError("Insufficient balance to complete the transaction.")
                
                # ইউজারের মূল ব্যালেন্স থেকে টাকা কেটে নেওয়া
                transaction.update(user_ref_txn, {'balance': firestore.Increment(-amount)})
                
                # withdraw_requests কালেকশনে নতুন রিকোয়েস্ট তৈরি করা
                new_request_ref = db.collection('withdraw_requests').document()
                transaction.set(new_request_ref, {
                    'user_id': user_id,
                    'status': 'pending',
                    'amount': amount,
                    'method': payment_method,
                    'number': account_number,
                    'requested_at': firestore.SERVER_TIMESTAMP
                })

            transaction = db.transaction()
            withdraw_request_transaction(transaction, user_ref, amount_to_withdraw)
            
            flash(f"আপনার ৳{amount_to_withdraw} উইথড্র রিকোয়েস্ট সফলভাবে জমা দেওয়া হয়েছে।", "success")
            return redirect(url_for('withdraw_page'))

        # GET রিকোয়েস্টের জন্য ডেটা প্রস্তুত করা
        eligibility_data = {
            'current_balance': current_balance, 'is_balance_eligible': is_balance_eligible,
            'referral_count': referral_count, 'are_referrals_eligible': are_referrals_eligible,
            'account_created_at': account_created_at.strftime('%d %b, %Y') if account_created_at else "N/A",
            'is_account_old_enough': is_account_old_enough, 'all_conditions_met': all_conditions_met
        }

        # উইথড্র হিস্টোরি আনা
        withdraw_history_query = db.collection('withdraw_requests').where(filter=FieldFilter('user_id', '==', user_id)).order_by('requested_at', direction=firestore.Query.DESCENDING).limit(10)
        withdraw_history = [doc.to_dict() for doc in withdraw_history_query.stream()]

        return render_template('withdraw.html', eligibility=eligibility_data, user=user_data, withdraw_history=withdraw_history)

    except Exception as e:
        print(f"--- ERROR in /withdraw route for user {session.get('user_id')} ---")
        print(f"Error details: {e}")
        flash("উইথড্র পেইজ লোড করার সময় একটি অপ্রত্যাশিত সমস্যা হয়েছে।", "error")
        return redirect(url_for('dashboard'))
# app.py -> অ্যাডমিন প্যানেল সেকশনে যোগ করুন

@app.route(f'/{SECRET_ADMIN_PATH}/withdrawals')
def manage_withdrawals():
    """
    পেন্ডিং উইথড্র রিকোয়েস্টগুলোর তালিকা দেখায়।
    """
    try:
        # স্ট্যাটাস অনুযায়ী ফিল্টার করার অপশন (ভবিষ্যতের জন্য)
        status_filter = request.args.get('status', 'pending')
        
        reqs_query = db.collection('withdraw_requests').where('status', '==', status_filter).order_by('requested_at').stream()
        
        pending_requests = []
        for req_doc in reqs_query:
            req_data = req_doc.to_dict()
            req_data['id'] = req_doc.id
            
            # রিকোয়েস্টের সাথে সম্পর্কিত ইউজারের তথ্য আনা হচ্ছে
            user_id = req_data.get('user_id')
            if user_id:
                user_doc = db.collection('users').document(user_id).get()
                req_data['user_info'] = user_doc.to_dict() if user_doc.exists else {'name': 'Unknown User'}
            
            pending_requests.append(req_data)
            
        return render_template('manage_withdrawals.html', 
                               requests=pending_requests, 
                               current_status=status_filter,
                               admin_path=SECRET_ADMIN_PATH)
    except Exception as e:
        flash(f"উইথড্র রিকোয়েস্ট আনতে সমস্যা হয়েছে: {e}", "error")
        return redirect(url_for('admin_dashboard'))


@app.route(f'/{SECRET_ADMIN_PATH}/withdrawals/approve/<req_id>')
def approve_withdrawal(req_id):
    """
    একটি উইথড্র রিকোয়েস্ট অ্যাপ্রুভ করে।
    """
    req_ref = db.collection('withdraw_requests').document(req_id)
    try:
        req_ref.update({'status': 'completed', 'processed_at': firestore.SERVER_TIMESTAMP})
        
        # (ঐচ্ছিক) ইউজারকে নোটিফিকেশন পাঠানো
        req_data = req_ref.get().to_dict()
        db.collection('notifications').add({
            'user_id': req_data['user_id'],
            'message': f"আপনার ৳{req_data['amount']} উইথড্র রিকোয়েস্টটি সফল হয়েছে।",
            'is_read': False, 'type': 'success', 'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        flash("উইথড্র রিকোয়েস্টটি সফলভাবে অ্যাপ্রুভ করা হয়েছে।", "success")
    except Exception as e:
        flash(f"অ্যাপ্রুভ করার সময় সমস্যা হয়েছে: {e}", "error")
        
    return redirect(url_for('manage_withdrawals'))


@app.route(f'/{SECRET_ADMIN_PATH}/withdrawals/reject/<req_id>')
def reject_withdrawal(req_id):
    """
    একটি উইথড্র রিকোয়েস্ট বাতিল করে এবং টাকা ইউজারের একাউন্টে ফেরত দেয়।
    """
    req_ref = db.collection('withdraw_requests').document(req_id)
    try:
        req_data = req_ref.get().to_dict()
        if not req_data or req_data.get('status') != 'pending':
            flash("এই রিকোয়েস্টটি আর পেন্ডিং নেই।", "warning")
            return redirect(url_for('manage_withdrawals'))

        user_id = req_data['user_id']
        amount_to_refund = req_data['amount']
        
        # --- Transaction ব্যবহার করে টাকা ফেরত দেওয়া এবং স্ট্যাটাস পরিবর্তন ---
        @firestore.transactional
        def reject_and_refund(transaction, user_ref, req_ref, amount):
            # ১. ইউজারের ব্যালেন্সে টাকা ফেরত দেওয়া
            transaction.update(user_ref, {'balance': firestore.Increment(amount)})
            # ২. রিকোয়েস্টের স্ট্যাটাস 'rejected' করা
            transaction.update(req_ref, {'status': 'rejected', 'processed_at': firestore.SERVER_TIMESTAMP})

        user_ref = db.collection('users').document(user_id)
        transaction = db.transaction()
        reject_and_refund(transaction, user_ref, req_ref, amount_to_refund)

        # ইউজারকে নোটিফিকেশন পাঠানো
        db.collection('notifications').add({
            'user_id': user_id,
            'message': f"দুঃখিত, আপনার ৳{amount_to_refund} উইথড্র রিকোয়েস্টটি বাতিল করা হয়েছে এবং টাকা আপনার একাউন্টে ফেরত দেওয়া হয়েছে।",
            'is_read': False, 'type': 'error', 'timestamp': firestore.SERVER_TIMESTAMP
        })

        flash("উইথড্র রিকোয়েস্টটি বাতিল করা হয়েছে এবং টাকা ফেরত দেওয়া হয়েছে।", "success")
    except Exception as e:
        flash(f"বাতিল করার সময় সমস্যা হয়েছে: {e}", "error")

    return redirect(url_for('manage_withdrawals'))
    
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




# app.py ফাইলের ভেতরে এই ফাংশনটি রাখুন বা প্রতিস্থাপন করুন
# ফাইলের উপরে from google.cloud.firestore_v1.base_query import FieldFilter ইম্পোর্ট করা ভালো

@app.route('/dashboard')
@login_required
def dashboard():
    """
    ব্যবহারকারীর ড্যাশবোর্ড দেখায়। এটি ব্যবহারকারীর তথ্য, নোটিফিকেশন,
    এবং বিভিন্ন কাজের ইতিহাস Firestore থেকে এনে টেমপ্লেটে পাস করে।
    """
    try:
        user_id = session['user_id']
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        # যদি কোনো কারণে ডাটাবেসে ইউজার না থাকে
        if not user_doc.exists:
            session.clear() # সেশন পরিষ্কার করে দেওয়া হচ্ছে
            flash("আপনার একাউন্ট খুঁজে পাওয়া যায়নি। অনুগ্রহ করে আবার লগইন করুন।", "error")
            return redirect(url_for('login'))
            
        user = user_doc.to_dict()
        account_status = user.get('account_status', 'inactive')
        # --- ব্যান স্ট্যাটাস চেক করা ---
        is_banned = user.get('status') == 'banned'

        # রেফারেল লিঙ্ক তৈরি করা
        referral_link = url_for('signup', ref=user.get('my_referral_code'), _external=True)

        # --- বিভিন্ন কালেকশন থেকে ডেটা আনা হচ্ছে ---
        
        # ১. অপঠিত নোটিফিকেশন আনা (is_read == False)
        # এর জন্য Firestore Composite Index প্রয়োজন হবে
        notifications_query = db.collection('notifications') \
                                .where('user_id', '==', user_id) \
                                .where('is_read', '==', False) \
                                .order_by('timestamp', direction=firestore.Query.DESCENDING)
        notifications = [dict(doc.to_dict(), **{'id': doc.id}) for doc in notifications_query.stream()]
        
        # ২. টাস্ক সাবমিশনের ইতিহাস আনা (সাম্প্রতিক ১০টি)
        submissions_query = db.collection('task_submissions') \
                                .where('user_id', '==', user_id) \
                                .order_by('submitted_at', direction=firestore.Query.DESCENDING) \
                                .limit(10)
        task_history = [doc.to_dict() for doc in submissions_query.stream()]

        # ৩. রেফারেল হিস্টোরি আনা (সাম্প্রতিক ১০টি)
        referrals_query = db.collection('referrals') \
                              .where('referrer_id', '==', user_id) \
                              .order_by('timestamp', direction=firestore.Query.DESCENDING) \
                              .limit(10)
        my_referrals = [doc.to_dict() for doc in referrals_query.stream()]

        # ৪. ব্যালেন্স হিস্টোরি আনা (সাম্প্রতিক ১০টি)
        balance_query = db.collection('balance_history') \
                            .where('user_id', '==', user_id) \
                            .order_by('timestamp', direction=firestore.Query.DESCENDING) \
                            .limit(10)
        balance_history = [doc.to_dict() for doc in balance_query.stream()]
        
        # --- সমস্ত ডেটা টেমপ্লেটে পাঠানো হচ্ছে ---
        return render_template(
            'dashboard.html', 
            user=user, 
            account_status=account_status, # <-- স্ট্যাটাস পাঠানো হচ্ছে
            is_banned=is_banned,
            referral_link=referral_link, 
            notifications=notifications, 
            task_history=task_history,
            my_referrals=my_referrals,
            balance_history=balance_history
        )

    except Exception as e:
        # যদি কোনো অপ্রত্যাশিত এরর হয় (যেমন, Firestore কানেকশন সমস্যা)
        print(f"--- ERROR in /dashboard route ---")
        print(f"Error for user_id: {session.get('user_id')}")
        print(f"Error details: {e}")
        print(f"---------------------------------")
        flash("ড্যাশবোর্ড লোড করার সময় একটি সমস্যা হয়েছে। অনুগ্রহ করে কিছুক্ষণ পর আবার চেষ্টা করুন।", "error")
        # এরর হলে লগআউট করে দেওয়া যেতে পারে অথবা একটি এরর পেইজে পাঠানো যেতে পারে
        return redirect(url_for('login'))

# app.py -> activate_account ফাংশনটি আপডেট করুন
# app.py -> activate_account ফাংশনটি আপডেট করুন

@app.route('/activate', methods=['GET', 'POST'])
@login_required
def activate_account():
    if request.method == 'POST':
        # --- নতুন: payment_method গ্রহণ করা হচ্ছে ---
        payment_method = request.form.get('payment_method')
        sender_number = request.form.get('sender_number')
        trx_id = request.form.get('trx_id')
        
        if not all([payment_method, sender_number, trx_id]):
            flash("অনুগ্রহ করে সব তথ্য সঠিকভাবে পূরণ করুন।", "error")
            return redirect(url_for('activate_account'))

        # activation_requests কালেকশনে রিকোয়েস্ট সেভ করা
        db.collection('activation_requests').add({
            'user_id': session['user_id'],
            'payment_method': payment_method, # <-- নতুন ফিল্ড সেভ করা হচ্ছে
            'sender_number': sender_number,
            'trx_id': trx_id,
            'status': 'pending',
            'requested_at': firestore.SERVER_TIMESTAMP
        })
        flash("আপনার অ্যাক্টিভেশন রিকোয়েস্ট সফলভাবে জমা দেওয়া হয়েছে। পর্যালোচনার জন্য অপেক্ষা করুন।", "info")
        return redirect(url_for('dashboard'))

    return render_template('activate.html')
# app.py -> Admin Panel সেকশনে যোগ করুন
@app.route(f'/{SECRET_ADMIN_PATH}/activations')
def manage_activations():
    reqs_query = db.collection('activation_requests').where('status', '==', 'pending').stream()
    pending_requests = [dict(req.to_dict(), **{'id': req.id}) for req in reqs_query]
    return render_template('activations.html', pending_requests=pending_requests, admin_path=SECRET_ADMIN_PATH)

# app.py -> approve_activation ফাংশনটি প্রতিস্থাপন করুন
# app.py -> approve_activation ফাংশনটি প্রতিস্থাপন করুন
# app.py ফাইলের অ্যাডমিন প্যানেল সেকশনে এই ফাংশনটি রাখুন বা প্রতিস্থাপন করুন

@app.route(f'/{SECRET_ADMIN_PATH}/activations/approve/<req_id>')
def approve_activation(req_id):
    """
    একজন ব্যবহারকারীর একাউন্ট অ্যাক্টিভেশন রিকোয়েস্ট অ্যাপ্রুভ করে।
    এটি ট্রানজেকশনের বাইরে সমস্ত রিড অপারেশন সম্পন্ন করে এবং ট্রানজেকশনের
    ভেতরে শুধুমাত্র রাইট অপারেশনগুলো সম্পাদন করে।
    """
    req_ref = db.collection('activation_requests').document(req_id)
    
    try:
        # --- ধাপ ১: ট্রানজেকশনের বাইরে সমস্ত পড়ার কাজ সম্পন্ন করা ---

        # ক. অ্যাক্টিভেশন রিকোয়েস্টের ডেটা পড়া
        req_doc = req_ref.get()
        if not req_doc.exists or req_doc.to_dict().get('status') != 'pending':
            flash("এই রিকোয়েস্টটি আর পেন্ডিং নেই অথবা খুঁজে পাওয়া যায়নি।", "warning")
            return redirect(url_for('manage_activations'))
        
        req_data = req_doc.to_dict()
        user_id = req_data.get('user_id')
        
        if not user_id:
            flash("রিকোয়েস্টে ইউজার আইডি পাওয়া যায়নি।", "error")
            return redirect(url_for('manage_activations'))

        # খ. অ্যাক্টিভেট করা হবে এমন ইউজারের ডেটা পড়া
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            # যদি ইউজার না থাকে, রিকোয়েস্টটি ডিলিট করে দেওয়া যেতে পারে
            req_ref.update({'status': 'failed', 'failure_reason': 'User not found'})
            flash("অ্যাক্টিভেট করার জন্য ইউজারকে খুঁজে পাওয়া যায়নি। রিকোয়েস্ট বাতিল করা হয়েছে।", "error")
            return redirect(url_for('manage_activations'))
            
        user_data = user_doc.to_dict()
        
        # গ. রেফারারকে খুঁজে বের করা (যদি থাকে)
        referrer_doc = None
        referrer_code = user_data.get('referred_by')
        if referrer_code:
            query = db.collection('users').where(filter=FieldFilter('my_referral_code', '==', referrer_code)).limit(1)
            referrer_list = list(query.stream())
            if referrer_list:
                referrer_doc = referrer_list[0]

        # --- ধাপ ২: ট্রানজেকশন শুরু করা ---
        
        @firestore.transactional
        def activate_user_in_transaction(transaction, user_ref, req_ref, referrer_doc_param):
            """
            এই ফাংশনের ভেতরে শুধুমাত্র লেখার কাজ করা হবে।
            """
            # --- লেখার কাজ (Writes) ---
            
            # ১. ইউজারের স্ট্যাটাস 'active' করা
            transaction.update(user_ref, {'account_status': 'active'})
            # ২. রিকোয়েস্টের স্ট্যাটাস 'completed' করা
            transaction.update(req_ref, {'status': 'completed', 'processed_at': firestore.SERVER_TIMESTAMP})

            # ৩. যদি রেফারার পাওয়া যায়, তাহলে বোনাস এবং হিস্টোরি তৈরি
            if referrer_doc_param:
                referrer_ref = db.collection('users').document(referrer_doc_param.id)
                reward_amount = 10.0
                
                # ক. ব্যালেন্স আপডেট
                transaction.update(referrer_ref, {'balance': firestore.Increment(reward_amount)})
                transaction.update(user_ref, {'balance': firestore.Increment(reward_amount)})
                
                # খ. `referrals` কালেকশনে এন্ট্রি তৈরি
                referral_history_ref = db.collection('referrals').document()
                transaction.set(referral_history_ref, {
                    'referrer_id': referrer_doc_param.id, 
                    'referred_id': user_id,
                    'referred_user_email': user_data.get('email', 'N/A'),
                    'reward_amount': reward_amount, 
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
                
                # গ. রেফারারের জন্য `balance_history` তৈরি
                referrer_balance_ref = db.collection('balance_history').document()
                transaction.set(referrer_balance_ref, {
                    'user_id': referrer_doc_param.id, 'amount': reward_amount,
                    'type': 'referral_bonus', 'description': f"Bonus for referring {user_data.get('email')}",
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
                
                # ঘ. নতুন ইউজারের জন্য `balance_history` তৈরি
                new_user_balance_ref = db.collection('balance_history').document()
                transaction.set(new_user_balance_ref, {
                    'user_id': user_id, 'amount': reward_amount,
                    'type': 'signup_referral_bonus', 'description': f"Bonus for joining with code {referrer_code}",
                    'timestamp': firestore.SERVER_TIMESTAMP
                })
        
        # --- ধাপ ৩: ট্রানজেকশনটি চালানো ---
        
        transaction = db.transaction()
        activate_user_in_transaction(transaction, user_ref, req_ref, referrer_doc)
        
        flash("একাউন্ট সফলভাবে অ্যাক্টিভেট করা হয়েছে এবং বোনাস (যদি প্রযোজ্য হয়) যোগ করা হয়েছে!", "success")

    except Exception as e:
        print(f"--- ERROR in approve_activation for req_id: {req_id} ---")
        print(f"Error details: {e}")
        print(f"-------------------------------------------------------")
        flash(f"একটি অপ্রত্যাশিত সমস্যা হয়েছে: {e}", "error")

    return redirect(url_for('manage_activations'))

@app.route('/tasks')
@login_required
def tasks_page():
    user_id = session['user_id']
    user_status = db.collection('users').document(user_id).get().to_dict().get('account_status', 'inactive')
    
    if user_status != 'active':
        flash("কাজ করার জন্য অনুগ্রহ করে প্রথমে আপনার একাউন্টটি অ্যাক্টিভেট করুন।", "warning")
        return redirect(url_for('dashboard'))
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
# app.py -> admin_dashboard ফাংশনটি প্যাজিনেশন সহ আপডেট করুন

@app.route(f'/{SECRET_ADMIN_PATH}')
def admin_dashboard():
    try:
        # প্যাজিনেশনের জন্য পৃষ্ঠা টোকেন URL থেকে নেওয়া হচ্ছে
        page_token = request.args.get('page')
        
        # ডিফল্ট কোয়েরি (পেন্ডিং টাস্ক, পুরনো গুলো আগে)
        query = db.collection('task_submissions').where('status', '==', 'pending').order_by('submitted_at', direction=firestore.Query.ASCENDING)
        
        # যদি এটি প্রথম পৃষ্ঠা না হয়, তাহলে আগের পৃষ্ঠার শেষ ডকুমেন্ট থেকে শুরু করা হবে
        if page_token:
            last_doc_snapshot = db.collection('task_submissions').document(page_token).get()
            if last_doc_snapshot.exists:
                query = query.start_after(last_doc_snapshot)
        
        # প্রতি পৃষ্ঠায় কতগুলো টাস্ক দেখানো হবে
        tasks_per_page = 25
        query = query.limit(tasks_per_page)

        # কোয়েরি এক্সিকিউট করে ডকুমেন্টগুলো আনা হচ্ছে
        docs = list(query.stream())
        
        tasks_with_user_info = []
        for task_doc in docs:
            task_data = task_doc.to_dict()
            task_data['id'] = task_doc.id
            
            user_id = task_data.get('user_id')
            if user_id:
                user_info_doc = db.collection('users').document(user_id).get()
                task_data['user_info'] = user_info_doc.to_dict() if user_info_doc.exists else {'name': 'Unknown User', 'email': 'N/A'}
            else:
                task_data['user_info'] = {'name': 'No User ID', 'email': 'N/A'}
                
            tasks_with_user_info.append(task_data)
            
        # পরবর্তী পৃষ্ঠার জন্য টোকেন তৈরি করা (যদি আরও ডেটা থাকে)
        next_page_token = None
        if len(docs) == tasks_per_page:
            next_page_token = docs[-1].id # বর্তমান পৃষ্ঠার শেষ টাস্কের আইডি

        return render_template(
            'admin_dashboard.html', 
            pending_tasks=tasks_with_user_info, 
            next_page_token=next_page_token,
            admin_path=SECRET_ADMIN_PATH
        )
        
    except Exception as e:
        print(f"Error in admin_dashboard: {e}")
        flash("অ্যাডমিন ড্যাশবোর্ড লোড করতে একটি সমস্যা হয়েছে।", "error")
        # কোনো এরর হলে একটি খালি তালিকা পাঠানো হচ্ছে
        return render_template('admin_dashboard.html', pending_tasks=[], admin_path=SECRET_ADMIN_PATH)
    
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
