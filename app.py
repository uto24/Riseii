# ==============================================================================
#                      MAIN APPLICATION FILE: app.py
#               (Firebase Firestore + Post-images for Storage)
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
# .env ফাইল থেকে ভেরিয়েবল লোড করবে (লোকাল টেস্টিং এর জন্য)
load_dotenv()

# Flask অ্যাপ ইনিশিয়ালাইজেশন
app = Flask(__name__)

# সেশনের জন্য একটি গোপন কী সেট করা।
# প্রোডাকশনে এটি অবশ্যই Vercel এর Environment Variable থেকে লোড করতে হবে।
app.secret_key = os.getenv("FLASK_SECRET_KEY", "default-secret-key-for-local-dev-12345")

# --- Firebase ইনিশিয়ালাইজেশন ---
# এই অংশটি Firebase এর সাথে আপনার অ্যাপের সংযোগ স্থাপন করে।
# এখানে Firebase Storage এর প্রয়োজন নেই, তাই `storageBucket` বাদ দেওয়া হয়েছে।
try:
    # Vercel এ হোস্ট করার সময় Environment Variable থেকে JSON key লোড করবে।
    firebase_creds_json_str = os.getenv('FIREBASE_CREDENTIALS_JSON')

    if not firebase_creds_json_str:
        # যদি এনভায়রনমেন্ট ভেরিয়েবল না পায়, তাহলে লোকাল ফাইল থেকে লোড করার চেষ্টা করবে।
        print("INFO: Loading Firebase credentials from local file 'firebase_credentials.json'.")
        cred = credentials.Certificate("firebase_credentials.json")
    else:
        # যদি এনভায়রনমেন্ট ভেরিয়েबल পায়, তাহলে সেখান থেকে লোড করবে।
        print("INFO: Loading Firebase credentials from environment variable.")
        firebase_creds_dict = json.loads(firebase_creds_json_str)
        cred = credentials.Certificate(firebase_creds_dict)

    # Firebase অ্যাপ ইনিশিয়ালাইজ করা (শুধুমাত্র Firestore ও Auth এর জন্য)
    firebase_admin.initialize_app(cred)

    # Firestore Database এর ক্লায়েন্ট তৈরি করা
    db = firestore.client()
    print("SUCCESS: Firebase (Firestore & Auth) initialized successfully!")

except Exception as e:
    # যদি কোনো কারণে Firebase সংযোগ স্থাপন না হয়, তাহলে একটি মারাত্মক ত্রুটি প্রিন্ট হবে।
    print(f"FATAL ERROR: Could not initialize Firebase. App may not work correctly. Error: {e}")
    db = None

# --- Helper ফাংশন ---
def generate_referral_code():
    """ একটি ৮ অক্ষরের ইউনিক রেফারেল কোড তৈরি করে। """
    return str(uuid.uuid4()).split('-')[0].upper()

# --- রুট (Routes) বা পেইজ ---

# হোমপেইজ
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# সাইনআপ পেইজ
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # ইউজার লগইন করা থাকলে তাকে ড্যাশবোর্ডে পাঠানো হবে।
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # ফর্ম থেকে তথ্য সংগ্রহ
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        # অন্যান্য ফিল্ডগুলো ঐচ্ছিক হিসেবে রাখা হলো
        number = request.form.get('number', '')
        age = request.form.get('age', '')
        referrer_code = request.form.get('referrer_code', '').strip().upper()

        try:
            # Firebase Authentication ব্যবহার করে নতুন ইউজার তৈরি
            user_record = auth.create_user(
                email=email,
                password=password,
                display_name=name
            )
            
            # Firestore Database-এ ইউজারের জন্য তথ্য সংরক্ষণ
            my_referral_code = generate_referral_code()
            user_data = {
                'name': name,
                'email': email,
                'number': number,
                'age': age,
                'balance': 0.0,
                'referred_by': referrer_code,
                'my_referral_code': my_referral_code,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            user_doc_ref = db.collection('users').document(user_record.uid)
            user_doc_ref.set(user_data)
            
            # রেফারেল বোনাস লজিক
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

    # GET রিকোয়েস্টের জন্য
    ref_code = request.args.get('ref', '')
    firebase_api_key = os.getenv('FIREBASE_API_KEY')
    return render_template('signup.html', ref_code=ref_code, firebase_api_key=firebase_api_key)


# লগইন পেইজ
@app.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    # টেমপ্লেটে Firebase Web API Key পাঠানো হচ্ছে, যা JavaScript কোড ব্যবহার করবে।
    firebase_api_key = os.getenv('FIREBASE_API_KEY')
    return render_template('login.html', firebase_api_key=firebase_api_key)

# লগআউট
@app.route('/logout')
def logout():
    session.clear()
    flash('আপনি সফলভাবে লগ আউট করেছেন।', 'info')
    return redirect(url_for('login'))


# --- API রুট (JavaScript থেকে কল করার জন্য) ---

# সেশন সেট করার জন্য API
@app.route('/api/set_session', methods=['POST'])
def set_session():
    """ ক্লায়েন্ট সাইড থেকে লগইন সফল হলে এই API কল করে সার্ভারে সেশন তৈরি করা হয়। """
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

# Google সাইন-ইন হ্যান্ডেল করার API
@app.route('/api/auth/google', methods=['POST'])
def auth_google():
    """ Google সাইন-ইন এর পর ক্লায়েন্ট থেকে পাওয়া টোকেন হ্যান্ডেল করে। """
    id_token = request.json.get('idToken')
    referrer_code = request.json.get('referrerCode', '').strip().upper()
    
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        user_info = auth.get_user(uid)
        
        user_doc_ref = db.collection('users').document(uid)
        if not user_doc_ref.get().exists:
            # নতুন ইউজার, Firestore এ তার ডাটা তৈরি করা
            my_referral_code = generate_referral_code()
            user_data = {
                'name': user_info.display_name or 'Google User',
                'email': user_info.email,
                'balance': 0.0, 'referred_by': referrer_code,
                'my_referral_code': my_referral_code,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            user_doc_ref.set(user_data)
            # এখানেও রেফারেল বোনাস লজিক যোগ করা যায়

        session['user_id'] = uid
        session['user_name'] = user_info.display_name
        return jsonify({"status": "success", "redirect_url": url_for('dashboard')})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Google login failed: {e}"}), 401


# --- ইউজার ড্যাশবোর্ড এবং টাস্ক ---

# ড্যাশবোর্ড পেইজ
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


# ফেসবুক পোস্ট টাস্ক পেইজ
@app.route('/task/fb-post', methods=['GET', 'POST'])
def task_fb_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Post-images থেকে পাওয়া URL টি ফর্ম থেকে গ্রহণ করা হচ্ছে
        screenshot_url = request.form.get('screenshot_url')

        if not screenshot_url:
            flash('স্ক্রিনশট আপলোড হয়নি অথবা আপলোড ব্যর্থ হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।', 'error')
            return redirect(request.url)

        # টাস্ক সাবমিশনের তথ্য Firestore এ সেভ করা
        submission_data = {
            'user_id': session['user_id'],
            'task_type': 'fb_post',
            'screenshot_url': screenshot_url,  # এখানে সরাসরি URL সেভ হচ্ছে
            'status': 'pending',
            'reward': 10.0,
            'submitted_at': firestore.SERVER_TIMESTAMP,
            'process_after': datetime.utcnow() + timedelta(minutes=30)
        }
        db.collection('task_submissions').add(submission_data)
        
        flash('আপনার স্ক্রিনশট সফলভাবে জমা দেওয়া হয়েছে!', 'success')
        return redirect(url_for('dashboard'))

    # GET রিকোয়েস্টের জন্য টাস্কের তথ্য দেখানো
    task_info = {
        'title': 'ফেসবুক পোস্ট টাস্ক',
        'caption': 'আমাদের এই অসাধারণ অ্যাপটি ব্যবহার করে আয় করুন!',
        'image_url': 'https://via.placeholder.com/400x250.png?text=Post+This+Image'
    }
    return render_template('task_fb_post.html', task=task_info)


# --- লোকাল টেস্টিং এর জন্য ---
if __name__ == '__main__':
    # এই অংশটি শুধুমাত্র লোকাল মেশিনে সরাসরি `python app.py` চালিয়ে টেস্ট করার জন্য।
    # Vercel এই অংশটি ব্যবহার করে না।
    app.run(host='0.0.0.0', port=8080, debug=True)
