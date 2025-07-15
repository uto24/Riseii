# ==============================================================================
#                      MAIN APPLICATION FILE: app.py
# ==============================================================================

# --- প্রয়োজনীয় লাইব্রেরি ইম্পোর্ট ---
import os
import uuid
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore, storage, auth

# --- অ্যাপ্লিকেশন এবং এনভায়রনমেন্ট ভেরিয়েবল লোড ---
# .env ফাইল থেকে ভেরিয়েবল লোড করবে (লোকাল টেস্টিং এর জন্য)
load_dotenv()

# Flask অ্যাপ ইনিশিয়ালাইজেশন
app = Flask(__name__)

# সেশনের জন্য একটি গোপন কী সেট করা। এটি প্রোডাকশনে অবশ্যই Environment Variable থেকে লোড করতে হবে।
app.secret_key = os.getenv("FLASK_SECRET_KEY", "a_very_secure_and_random_default_secret_key_for_testing")

# --- Firebase ইনিশিয়ালাইজেশন ---
# এই অংশটি Firebase এর সাথে আপনার অ্যাপের সংযোগ স্থাপন করে।
try:
    # Vercel এ হোস্ট করার সময় Environment Variable থেকে JSON key লোড করবে।
    firebase_creds_json_str = os.getenv('FIREBASE_CREDENTIALS_JSON')

    if not firebase_creds_json_str:
        # যদি এনভায়রনমেন্ট ভেরিয়েবল না পায়, তাহলে লোকাল ফাইল থেকে লোড করার চেষ্টা করবে।
        print("INFO: Loading Firebase credentials from local file 'firebase_credentials.json'.")
        cred = credentials.Certificate("firebase_credentials.json")
    else:
        # যদি এনভায়রনমেন্ট ভেরিয়েবল পায়, তাহলে সেখান থেকে লোড করবে।
        print("INFO: Loading Firebase credentials from environment variable.")
        firebase_creds_dict = json.loads(firebase_creds_json_str)
        cred = credentials.Certificate(firebase_creds_dict)

    # Firebase অ্যাপ ইনিশিয়ালাইজ করা
    # FIREBASE_STORAGE_BUCKET ভেরিয়েবলটি আপনার Firebase Storage এর ঠিকানা ধারণ করবে।
    firebase_admin.initialize_app(cred, {
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
    })

    # Firestore Database এবং Storage Bucket এর ক্লায়েন্ট তৈরি করা
    db = firestore.client()
    bucket = storage.bucket()
    print("SUCCESS: Firebase initialized successfully!")

except Exception as e:
    # যদি কোনো কারণে Firebase সংযোগ স্থাপন না হয়, তাহলে একটি মারাত্মক ত্রুটি প্রিন্ট হবে।
    print(f"FATAL ERROR: Could not initialize Firebase. App may not work correctly. Error: {e}")
    db = None
    bucket = None

# --- Helper ফাংশন ---
def generate_referral_code():
    """ একটি ৮ অক্ষরের ইউনিক রেফারেল কোড তৈরি করে। """
    return str(uuid.uuid4()).split('-')[0].upper()

# --- রুট (Routes) বা পেইজ ---

# হোমপেইজ
@app.route('/')
def index():
    # যদি ইউজার লগইন করা থাকে, তাকে ড্যাশবোর্ডে পাঠিয়ে দেওয়া হবে।
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# সাইনআপ পেইজ
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # ফর্ম থেকে তথ্য সংগ্রহ
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
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
            # ইউজার আইডি (uid) দিয়ে Firestore এ ডকুমেন্ট তৈরি
            user_doc_ref = db.collection('users').document(user_record.uid)
            user_doc_ref.set(user_data)
            
            # যদি রেফারেল কোড ব্যবহার করা হয়, তাহলে বোনাস প্রদান
            if referrer_code:
                query = db.collection('users').where('my_referral_code', '==', referrer_code).limit(1).stream()
                referrer_list = list(query)
                if referrer_list:
                    referrer_doc = referrer_list[0]
                    referrer_ref = db.collection('users').document(referrer_doc.id)
                    
                    # রেফারার এবং নতুন ইউজার উভয়কে ৫ টাকা বোনাস প্রদান
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

    # GET রিকোয়েস্টের জন্য রেফারেল কোড URL থেকে নেওয়া
    ref_code = request.args.get('ref', '')
    return render_template('signup.html', ref_code=ref_code)


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
    if not id_token:
        return jsonify({"status": "error", "message": "ID token not provided"}), 400

    try:
        # Firebase থেকে টোকেন ভেরিফাই করা
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        user_info = auth.get_user(uid)
        
        # সার্ভার সাইড সেশন তৈরি
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
        
        users_ref = db.collection('users')
        user_doc_ref = users_ref.document(uid)
        user_doc = user_doc_ref.get()

        # যদি ইউজার নতুন হয়, তাহলে Firestore এ তার ডাটা তৈরি করা
        if not user_doc.exists:
            my_referral_code = generate_referral_code()
            user_data = {
                'name': user_info.display_name or 'Google User',
                'email': user_info.email,
                'number': user_info.phone_number or '',
                'age': '',
                'balance': 0.0,
                'referred_by': referrer_code,
                'my_referral_code': my_referral_code,
                'created_at': firestore.SERVER_TIMESTAMP
            }
            user_doc_ref.set(user_data)
            
            # রেফারেল বোনাস লজিক (এখানেও প্রযোজ্য)
            if referrer_code:
                #... (বোনাস কোড এখানেও যুক্ত করা যায়)
                pass

        # সার্ভার সাইড সেশন তৈরি
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
    user_ref = db.collection('users').document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        session.clear() # যদি কোনো কারণে ডাটাবেসে ইউজার না থাকে
        flash("আপনার একাউন্ট খুঁজে পাওয়া যায়নি। আবার লগইন করুন।", "error")
        return redirect(url_for('login'))
        
    user = user_doc.to_dict()
    # ইউজারের রেফারেল লিঙ্ক তৈরি
    referral_link = url_for('signup', ref=user.get('my_referral_code'), _external=True)

    # ইউজারের টাস্ক হিস্টোরি আনা
    tasks_ref = db.collection('task_submissions').where('user_id', '==', user_id).order_by('submitted_at', direction=firestore.Query.DESCENDING).stream()
    task_history = [task.to_dict() for task in tasks_ref]
    
    return render_template('dashboard.html', user=user, task_history=task_history, referral_link=referral_link)


# ফেসবুক পোস্ট টাস্ক পেইজ
@app.route('/task/fb-post', methods=['GET', 'POST'])
def task_fb_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'screenshot' not in request.files or not bucket:
            flash('স্ক্রিনশট ফাইল সিলেক্ট করুন।', 'error')
            return redirect(request.url)
        
        file = request.files['screenshot']
        if file.filename == '':
            flash('কোনো ফাইল সিলেক্ট করা হয়নি।', 'error')
            return redirect(request.url)
        
        # ইউনিক ফাইলনেইম তৈরি এবং Firebase Storage এ আপলোড
        filename = f"screenshots/{session['user_id']}_{uuid.uuid4()}"
        blob = bucket.blob(filename)
        blob.upload_from_file(file, content_type=file.content_type)
        blob.make_public() # ফাইলটি পাবলিক করা হচ্ছে যাতে URL দিয়ে দেখা যায়
        
        # টাস্ক সাবমিশনের তথ্য Firestore এ সেভ করা
        submission_data = {
            'user_id': session['user_id'],
            'task_type': 'fb_post',
            'screenshot_url': blob.public_url,
            'status': 'pending', # স্ট্যাটাস: pending, completed, rejected
            'reward': 10.0,
            'submitted_at': firestore.SERVER_TIMESTAMP,
            'process_after': datetime.utcnow() + timedelta(minutes=30) # ৩০ মিনিট পর অটো অ্যাপ্রুভালের জন্য
        }
        db.collection('task_submissions').add(submission_data)
        
        flash('আপনার স্ক্রিনশট জমা দেওয়া হয়েছে! ৩০ মিনিটের মধ্যে ব্যালেন্স যোগ হবে।', 'success')
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
