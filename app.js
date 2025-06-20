document.getElementById('signupForm').addEventListener('submit', async function (event) {
    event.preventDefault();

    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const messageDiv = document.getElementById('message');

    const apiUrl = 'https://uthost.wuaze.com/signup.php'; // এখানে আপনার PHP API-এর সঠিক URL দিন

    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, email, password }),
        });

        const result = await response.json();

        if (response.status === 201) {
            messageDiv.style.color = 'green';
            messageDiv.innerText = result.message + " You can now login.";
            document.getElementById('signupForm').reset();
        } else {
            messageDiv.style.color = 'red';
            messageDiv.innerText = "Error: " + result.message;
        }
    } catch (error) {
        messageDiv.style.color = 'red';
        messageDiv.innerText = 'A network error occurred. Please try again.';
        console.error('Fetch error:', error);
    }
});
