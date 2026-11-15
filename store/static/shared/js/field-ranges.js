(function () {
    'use strict';

    const form = document.querySelector('.store-signup-page #loginForm');
    const limitsElement = document.getElementById('registration-field-limits');
    if (!form || !limitsElement) return;

    const limits = JSON.parse(limitsElement.textContent);
    const message = 'You exceeded the input field range';
    const fields = Array.from(form.querySelectorAll('[data-range-field]'));

    function outsideRange(input) {
        const bounds = limits[input.dataset.rangeField] || {};
        const value = input.value;
        // Required-field and format checks keep their existing messages.
        if (value === '') return false;

        const length = Array.from(value).length;
        if (bounds.max_length !== undefined && length > bounds.max_length) return true;
        if (bounds.min_length !== undefined && length < bounds.min_length) return true;

        if (/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value.trim())) {
            const number = Number(value.trim());
            if (bounds.min_value !== undefined && number < bounds.min_value) return true;
            if (bounds.max_value !== undefined && number > bounds.max_value) return true;
        }
        return false;
    }

    function validateField(input) {
        const error = document.getElementById(input.id + 'Error');
        if (!error) return true;
        const group = input.closest('.form-group');

        if (outsideRange(input)) {
            error.textContent = message;
            error.classList.add('show');
            group.classList.add('error');
            input.setAttribute('aria-invalid', 'true');
            return false;
        }

        if (error.textContent === message) {
            error.textContent = '';
            error.classList.remove('show');
            group.classList.remove('error');
            input.removeAttribute('aria-invalid');
        }
        return true;
    }

    function validateAll() {
        let firstInvalid = null;
        fields.forEach(function (input) {
            if (!validateField(input) && !firstInvalid) firstInvalid = input;
        });
        if (firstInvalid) firstInvalid.focus();
        return firstInvalid === null;
    }

    fields.forEach(function (input) {
        input.addEventListener('input', function () { validateField(input); });
    });

    window.RegistrationFieldRanges = { validateField: validateField, validateAll: validateAll };
})();
