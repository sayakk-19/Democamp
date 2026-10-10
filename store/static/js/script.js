// Neumorphism Login Form JavaScript
class NeumorphismLoginForm {
    constructor() {
        this.form = document.getElementById('loginForm');
        this.nameInput = document.getElementById('name');
        this.emailInput = document.getElementById('email');
        this.phnoInput = document.getElementById('phno');
        this.passwordInput = document.getElementById('password');
        this.reenter_passwordInput = document.getElementById('reenter_password');
        this.ageInput = document.getElementById('age');
        this.positionInput = document.getElementById('pos');
        this.passwordToggle = document.getElementById('passwordToggle');
        this.submitButton = this.form.querySelector('.login-btn');
        this.successMessage = document.getElementById('successMessage');
        this.socialButtons = document.querySelectorAll('.neu-social');

        this.init();
    }

    init() {
        this.bindEvents();
        // this.setupPasswordToggle();
        this.setupSocialButtons();
        this.setupNeumorphicEffects();
    }

    bindEvents() {
        // this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        this.nameInput.addEventListener('blur', () => this.validateName());
        this.emailInput.addEventListener('blur', () => this.validateEmail());
        this.phnoInput.addEventListener('blur', () => this.validatePhno());
        this.passwordInput.addEventListener('blur', () => this.validatePassword());
        this.reenter_passwordInput.addEventListener('blur', () => this.validateReenter_Password());
        this.ageInput.addEventListener('blur', () => this.validateAge());
        this.positionInput.addEventListener('blur', () => this.validatePosition());

        // Add soft press effects to inputs
        [this.nameInput, this.emailInput, this.phnoInput, this.passwordInput, this.reenter_passwordInput, this.ageInput, this.positionInput].forEach(input => {
            input.addEventListener('focus', (e) => this.addSoftPress(e));
            input.addEventListener('blur', (e) => this.removeSoftPress(e));
        });
    }

    setupPasswordToggle() {
        this.passwordToggle.addEventListener('click', () => {
            const type = this.passwordInput.type === 'password' ? 'text' : 'password';
            this.passwordInput.type = type;

            this.passwordToggle.classList.toggle('show-password', type === 'text');

            // Add soft click animation
            this.animateSoftPress(this.passwordToggle);
        });
    }

    setupSocialButtons() {
        this.socialButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.animateSoftPress(button);

                // Determine which social platform based on SVG content
                const svgPath = button.querySelector('svg path').getAttribute('d');
                let provider = 'Social';
                if (svgPath.includes('22.56')) provider = 'Google';
                else if (svgPath.includes('github')) provider = 'GitHub';
                else if (svgPath.includes('23.953')) provider = 'Twitter';

                this.handleSocialLogin(provider, button);
            });
        });
    }

    setupNeumorphicEffects() {
        // Add hover effects to all neumorphic elements
        const neuElements = document.querySelectorAll('.neu-icon, .neu-checkbox, .neu-social');
        neuElements.forEach(element => {
            element.addEventListener('mouseenter', () => {
                element.style.transform = 'scale(1.05)';
            });

            element.addEventListener('mouseleave', () => {
                element.style.transform = 'scale(1)';
            });
        });

        // Add ambient light effect on mouse move
        document.addEventListener('mousemove', (e) => {
            this.updateAmbientLight(e);
        });
    }

    updateAmbientLight(e) {
        const card = document.querySelector('.login-card');
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const angleX = (x - centerX) / centerX;
        const angleY = (y - centerY) / centerY;

        const shadowX = angleX * 30;
        const shadowY = angleY * 30;

        card.style.boxShadow = `
            ${shadowX}px ${shadowY}px 60px #bec3cf,
            ${-shadowX}px ${-shadowY}px 60px #ffffff
        `;
    }

    addSoftPress(e) {
        const inputGroup = e.target.closest('.neu-input');
        inputGroup.style.transform = 'scale(0.98)';
    }

    removeSoftPress(e) {
        const inputGroup = e.target.closest('.neu-input');
        inputGroup.style.transform = 'scale(1)';
    }

    animateSoftPress(element) {
        element.style.transform = 'scale(0.95)';
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 150);
    }

    validateName() {
        const name = this.nameInput.value

        if (!name) {
            this.showError('name', 'Username is required');
            return false;
        }

        this.clearError('name')
        return true;
    }

    validateEmail() {
        const email = this.emailInput.value.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!email) {
            this.showError('email', 'Email is required');
            return false;
        }

        if (!emailRegex.test(email)) {
            this.showError('email', 'Please enter a valid email');
            return false;
        }

        this.clearError('email');
        return true;
    }

    validatePhno() {
        const phno = this.phnoInput.value

        if (!phno) {
            this.showError('phno', 'Phone number is required');
            return false;
        }

        if (!/^\d{10}$/.test(phno)) {
            this.showError('phno', 'Please provide a valid mobile number');
            return false;
        }

        this.clearError('phno');
        return true;
    }

    validatePassword() {
        const password = this.passwordInput.value;

        if (!password) {
            this.showError('password', 'Password is required');
            return false;
        }

        if (password.length < 8) {
            this.showError('password', 'Password must be at least 8 characters');
            return false;
        }

        this.clearError('password');
        return true;
    }

    validateReenter_Password() {
        const reenter_password = this.reenter_passwordInput.value;

        if (!reenter_password) {
            this.showError('reenter_password', 'Password is required to be entered one more time');
            return false;
        }

        this.clearError('reenter_password');
        return true;
    }

    validateAge() {
        const age = this.ageInput.value;

        if (!age) {
            this.showError('age', 'Age is required');
            return false;
        }

        this.clearError('age');
        return true;
    }

    validatePosition() {
        const pos = this.positionInput.value;

        if (!pos) {
            this.showError('pos', 'Position is required');
            return false;
        }

        this.clearError('pos');
        return true;
    }

    showError(field, message) {
        const formGroup = document.getElementById(field).closest('.form-group');
        const errorElement = document.getElementById(`${field}Error`);

        formGroup.classList.add('error');
        errorElement.textContent = message;
        errorElement.classList.add('show');

        // Add gentle shake animation
        const input = document.getElementById(field);
        input.style.animation = 'gentleShake 0.5s ease-in-out';
        setTimeout(() => {
            input.style.animation = '';
        }, 500);
    }

    clearError(field) {
        const formGroup = document.getElementById(field).closest('.form-group');
        const errorElement = document.getElementById(`${field}Error`);

        formGroup.classList.remove('error');
        errorElement.classList.remove('show');
        setTimeout(() => {
            errorElement.textContent = '';
        }, 300);
    }

    async handleSubmit(e) {
        e.preventDefault();

        // const isNameValid = this.validateName();
        const isEmailValid = this.validateEmail();
        const isPasswordValid = this.validatePassword();

        if (!isEmailValid || !isPasswordValid) {
            this.animateSoftPress(this.submitButton);
            return;
        }

        this.setLoading(true);
        // this.form.submit();

        try {
            // Simulate soft authentication
            await new Promise(resolve => setTimeout(resolve, 2000));

            // Show neumorphic success
            this.showNeumorphicSuccess();
        } catch (error) {
            this.showError('password', 'Login failed. Please try again.');
        } finally {
            this.setLoading(false);
        }
    }

    async handleSocialLogin(provider, button) {
        console.log(`Initiating ${provider} login...`);

        // Add loading state to button
        button.style.pointerEvents = 'none';
        button.style.opacity = '0.7';

        try {
            await new Promise(resolve => setTimeout(resolve, 1500));
            console.log(`Redirecting to ${provider} authentication...`);
            // window.location.href = `/auth/${provider.toLowerCase()}`;
        } catch (error) {
            console.error(`${provider} authentication failed: ${error.message}`);
        } finally {
            button.style.pointerEvents = 'auto';
            button.style.opacity = '1';
        }
    }

    setLoading(loading) {
        this.submitButton.classList.toggle('loading', loading);
        this.submitButton.disabled = loading;

        // Disable social buttons during login
        this.socialButtons.forEach(button => {
            button.style.pointerEvents = loading ? 'none' : 'auto';
            button.style.opacity = loading ? '0.6' : '1';
        });
    }

    showNeumorphicSuccess() {
        // Soft fade out form
        this.form.style.transform = 'scale(0.95)';
        this.form.style.opacity = '0';

        setTimeout(() => {
            this.form.style.display = 'none';
            document.querySelector('.social-login').style.display = 'none';
            document.querySelector('.signup-link').style.display = 'none';

            // Show success with soft animation
            this.successMessage.classList.add('show');

            // Animate success icon
            const successIcon = this.successMessage.querySelector('.neu-icon');
            successIcon.style.animation = 'successPulse 0.6s ease-out';

        }, 300);

        // Simulate redirect
        setTimeout(() => {
            console.log('Redirecting to dashboard...');
            // window.location.href = '/dashboard';
        }, 2500);
    }
}

// Add custom animations
if (!document.querySelector('#neu-keyframes')) {
    const style = document.createElement('style');
    style.id = 'neu-keyframes';
    style.textContent = `
        @keyframes gentleShake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-3px); }
            75% { transform: translateX(3px); }
        }
        
        @keyframes successPulse {
            0% { transform: scale(0.8); opacity: 0; }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
}

// Initialize the form when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new NeumorphismLoginForm();
});