// main.js

const SUPABASE_URL = 'https://gsfgrycmlngptzirwicl.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdzZmdyeWNtbG5ncHR6aXJ3aWNsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA1NjgwNTksImV4cCI6MjA2NjE0NDA1OX0.uWGXs8dd1TNpdGpd6P8oyr2udzXPIrghcp667zOKdv4';

const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

/**
 * ব্যবহারকারী লগইন করা আছে কি না তা চেক করে এবং প্রয়োজনে পেজ পরিবর্তন করে।
 * এই ফাংশনটি এখন async হবে কারণ getSession() একটি অ্যাসিঙ্ক্রোনাস ফাংশন।
 */
async function checkUser() {
    const { data: { session } } = await supabaseClient.auth.getSession();
    
    if (session) {
        // ব্যবহারকারী লগইন করা আছে
        const onAuthPage = window.location.pathname.includes('index.html') || window.location.pathname.includes('signup.html');
        if (onAuthPage) {
            window.location.href = 'dashboard.html';
        }
    } else {
        // ব্যবহারকারী লগইন করা নেই
        if (window.location.pathname.includes('dashboard.html')) {
            window.location.href = 'index.html';
        }
    }
}

// checkUser() ফাংশনটি এখন async, তাই body.onload এ সরাসরি ব্যবহার করলে সমস্যা হতে পারে।
// তাই আমরা পেজ লোড হওয়ার সাথে সাথে এটি কল করব।
document.addEventListener('DOMContentLoaded', () => {
    checkUser();
});


/**
 * ব্যবহারকারীকে লগআউট করে এবং লগইন পেজে পাঠিয়ে দেয়।
 */
async function logout() {
    const { error } = await supabaseClient.auth.signOut();
    if (error) {
        console.error('Error logging out:', error.message);
    } else {
        window.location.href = 'index.html';
    }
}
