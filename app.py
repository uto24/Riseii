# ==============================================================================
#                      MAIN APPLICATION FILE: app.py
#               (Firebase Firestore + ImgBB for Storage)
# ==============================================================================

# --- প্রয়োজনীয় লাইব্রেরি ইম্পোর্ট ---
import os
import uuid
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, auth

# --- অ্যাপ্লিকেশন এবং এনভায়রনমেন্ট ভেরিয়েবল লোড ---
load_dotenv()

# Flask অ্যাপ ইনিশিয়ালাইজেশন
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default-secret-key-for-local-dev-12345")

# --- Firebase ইনিশিয়ালাইজেশন ---
try:
    firebase_creds_json_str = os.getenv('FIREBASE_CREDENTIALS_JSON')
    if not firebase_creds_json_str:
        print("INFO: Loading Firebase credentials from local file 'firebase_credentials.json'.")
        cred = credentials.Certificate("firebase_credentials.json")
    else:
        print("INFO: Loading Firebase credentials from environment variable.")
        firebase_creds_dict = json.loads(firebase_creds_json_str)
        cred = credentials.Certificate(firebase_creds_dict)
    
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("SUCCESS: Firebase (Firestore & Auth) initialized successfully!")
except Exception as e:
    print(f"FATAL ERROR: Could not initialize Firebase. Error: {e}")
    db = None

# --- Helper ফাংশন ---
def generate_referral_code():
    return str(uuid.uuid4()).split('-')[0].upper()

# --- রুট (Routes) বা পেইজ ---

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        referrer_code = request.form.get('referrer_code', '').strip().upper()
        try:
            user_record = auth.create_user(email=email, password=password, display_name=name)
            my_referral_code = generate_referral_code()
            user_data = {
                'name': name,
                'email': email,
                'balance': 0.0,
                'referred_by': referrer_code,
                'my_referral_code': my_referral_code,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            user_doc_ref = db.collection('users').document(user_record.uid)
            user_doc_ref.set(user_data)
            
            if referrer_code:
                query = db.collection('users').where('my_referral_code', '==', referrer_code).limit(1).stream()
                referrer_list = list(query)
                if referrer_list:
                    referrer_doc = referrer_list[0]
                    referrer_ref = db.collection('users').document(referrer_doc.id)
                    referrer_ref.update({'balance': firestore.Increment(5.0)})
                    user_doc_ref.update({'balance': firestore.Increment(5.0)})
                    flash('রেফারেলের জন্য আপনি এবং আপনার বন্ধু উভয়েই বোনাস পেয়েছেন!', 'info')

            flash('রেজিস্ট্রেশন সফল হয়েছে! এখন লগইন করুন।', 'success')
            return redirect(url_for('login'))
        except auth.EmailAlreadyExistsError:
            flash('এই ইমেইল দিয়ে ஏற்கனவே একাউন্ট খোলা আছে।', 'error')
            return redirect(url_for('signup'))
        except Exception as e:
            flash(f"একটি অপ্রত্যাশিত সমস্যা হয়েছে: {e}", "error")
            return redirect(url_for('signup'))

    # GET রিকোয়েস্টের জন্য প্রয়োজনীয় সব ভেরিয়েবল পাঠানো হচ্ছে
    ref_code = request.args.get('ref', '')
    config_data = {
        'firebase_api_key': os.getenv('FIREBASE_API_KEY'),
        'firebase_auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN'),
        'firebase_project_id': os.getenv('FIREBASE_PROJECT_ID'),
        'firebase_messaging_sender_id': os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
        'firebase_app_id': os.getenv('FIREBASE_APP_ID')
    }
    return render_template('signup.html', ref_code=ref_code, config=config_data)


@app.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    # টেমপ্লেটে Firebase Web API Key এবং অন্যান্য কনফিগারেশন পাঠানো হচ্ছে
    config_data = {
        'firebase_api_key': os.getenv('FIREBASE_API_KEY'),
        'firebase_auth_domain': os.getenv('FIREBASE_AUTH_DOMAIN'),
        'firebase_project_id': os.getenv('FIREBASE_PROJECT_ID'),
        'firebase_messaging_sender_id': os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
        'firebase_app_id': os.getenv('FIREBASE_APP_ID')
    }
    return render_template('login.html', config=config_data)

@app.route('/logout')
def logout():
    session.clear()
    flash('আপনি সফলভাবে লগ আউট করেছেন।', 'info')
    return redirect(url_for('login'))


# --- API রুট (JavaScript থেকে কল করার জন্য) ---

@app.route('/api/set_session', methods=['POST'])
def set_session():
    id_token = request.json.get('idToken')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        user_info = auth.get_user(uid)
        session['user_id'] = uid
        session['user_name'] = user_info.display_name
        return jsonify({"status": "success", "redirect_url": url_for('dashboard')})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 401

@app.route('/api/auth/google', methods=['POST'])
def auth_google():
    id_token = request.json.get('idToken')
    referrer_code = request.json.get('referrerCode', '').strip().upper()
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        user_info = auth.get_user(uid)
        user_doc_ref = db.collection('users').document(uid)
        if not user_doc_ref.get().exists:
            my_referral_code = generate_referral_code()
            user_data = {
                'name': user_info.display_name or 'Google User',
                'email': user_info.email,
                'balance': 0.0,
                'referred_by': referrer_code,
                'my_referral_code': my_referral_code,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            user_doc_ref.set(user_data)
        session['user_id'] = uid
        session['user_name'] = user_info.display_name
        return jsonify({"status": "success", "redirect_url": url_for('dashboard')})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Google login failed: {e}"}), 401


# --- ইউজার ড্যাশবোর্ড এবং টাস্ক ---

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("এই পেইজটি দেখার জন্য অনুগ্রহ করে লগইন করুন।", "info")
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_doc = db.collection('users').document(user_id).get()
    if not user_doc.exists:
        session.clear()
        flash("আপনার একাউন্ট খুঁজে পাওয়া যায়নি। আবার লগইন করুন।", "error")
        return redirect(url_for('login'))
        
    user = user_doc.to_dict()
    referral_link = url_for('signup', ref=user.get('my_referral_code'), _external=True)
    tasks_ref = db.collection('task_submissions').where('user_id', '==', user_id).order_by('submitted_at', direction=firestore.Query.DESCENDING).stream()
    task_history = [task.to_dict() for task in tasks_ref]
    
    return render_template('dashboard.html', user=user, task_history=task_history, referral_link=referral_link)

@app.route('/task/fb-post', methods=['GET', 'POST'])
def task_fb_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        screenshot_url = request.form.get('screenshot_url')
        if not screenshot_url:
            flash('স্ক্রিনশট আপলোড হয়নি অথবা আপলোড ব্যর্থ হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।', 'error')
            return redirect(request.url)

        submission_data = {
            'user_id': session['user_id'],
            'task_type': 'fb_post',
            'screenshot_url': screenshot_url,
            'status': 'pending',
            'reward': 10.0,
            'submitted_at': firestore.SERVER_TIMESTAMP,
            'process_after': datetime.utcnow() + timedelta(minutes=30)
        }
        db.collection('task_submissions').add(submission_data)
        
        flash('আপনার স্ক্রিনশট সফলভাবে জমা দেওয়া হয়েছে!', 'success')
        return redirect(url_for('dashboard'))

    task_info = {
        'title': 'ফেসবুক পোস্ট টাস্ক',
        'caption': 'আমাদের এই অসাধারণ অ্যাপটি ব্যবহার করে আয় করুন!',
        'image_url': 'https://via.placeholder.com/400x250.png?text=Post+This+Image'
    }
    return render_template('task_fb_post.html', task=task_info)


# --- লোকাল টেস্টিং এর জন্য ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
