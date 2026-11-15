(function () {
    'use strict';
    const buttons = document.querySelectorAll('[data-social-url]');
    buttons.forEach(function (button) {
        button.addEventListener('click', function () {
            if (button.disabled) return;
            button.disabled = true;
            button.setAttribute('aria-busy', 'true');
            window.location.assign(button.dataset.socialUrl);
        });
    });
    window.addEventListener('pageshow', function () {
        buttons.forEach(function (button) {
            button.disabled = false;
            button.removeAttribute('aria-busy');
        });
    });
})();
