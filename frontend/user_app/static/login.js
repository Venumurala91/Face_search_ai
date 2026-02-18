document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('guest-login-form');
    const errorMessageDiv = document.getElementById('error-message');
    const loginButton = document.querySelector('.login-button');

    function showError(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.classList.remove('hidden');
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault(); // Stop default form submission

        // NEW: Add loading state to the button
        loginButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-2"></i>Logging in...';
        loginButton.disabled = true;

        const formData = new FormData(form);
        try {
            // This is the functional part that talks to your backend
            const response = await fetch('/login', {
                method: 'POST',
                body: formData,
            });

            // If login is successful, the server will redirect
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }

            // If we are here, there was an error
            const errorData = await response.json();
            showError(errorData.detail || 'An unknown error occurred.');

        } catch (error) {
            showError('Could not connect to the server. Please try again.');
        } finally {
            // NEW: Reset button state after the attempt
            loginButton.innerHTML = 'Login <i class="fa-solid fa-arrow-right ml-2"></i>';
            loginButton.disabled = false;
        }
    });

    // Add floating animation to inputs on focus
    document.querySelectorAll('input').forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.style.transform = 'translateY(-2px)';
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.style.transform = 'translateY(0)';
        });
    });
});