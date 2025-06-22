// main.js

const SUPABASE_URL = 'https://gsfgrycmlngptzirwicl.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdzZmdyeWNtbG5ncHR6aXJ3aWNsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTA1NjgwNTksImV4cCI6MjA2NjE0NDA1OX0.uWGXs8dd1TNpdGpd6P8oyr2udzXPIrghcp667zOKdv4';

// Supabase ক্লায়েন্ট তৈরি (সঠিক পদ্ধতি)
const supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_KEY);

/**
 * ব্যবহারকারী লগইন করা আছে কি না তা চেক করে এবং প্রয়োজনে পেজ পরিবর্তন করে।
 */
function checkUser() {
    const user = supabaseClient.auth.user();
    if (user) {
        // যদি ব্যবহারকারী লগইন করা থাকে এবং লগইন/সাইনআপ পেজে থাকে,
        // তাহলে তাকে ড্যাশবোর্ডে পাঠিয়ে দিন।
        const onAuthPage = window.location.pathname.includes('index.html') || window.location.pathname.includes('signup.html');
        if (onAuthPage) {
            window.location.href = 'dashboard.html';
        }
    } else {
        // যদি ব্যবহারকারী লগইন করা না থাকে এবং ড্যাশবোর্ড পেজে যাওয়ার চেষ্টা করে,
        // তাহলে তাকে লগইন পেজে পাঠিয়ে দিন।
        if (window.location.pathname.includes('dashboard.html')) {
            window.location.href = 'index.html';
        }
    }
}

/**
 * ব্যবহারকারীকে লগআউট করে এবং লগইন পেজে পাঠিয়ে দেয়।
 */
async function logout() {
    const { error } = await supabaseClient.auth.signOut();
    if (error) {
        console.error('Error logging out:', error.message);
    } else {
        // লগআউট সফল হলে লগইন পেজে পাঠিয়ে দিন
        window.location.href = 'index.html';
    }
}
