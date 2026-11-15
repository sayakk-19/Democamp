(function () {
  'use strict';
  var storageKey = 'democamp_display_mode';
  var returnFocus = null;

  function syncDisplayControls() {
    var night = document.documentElement.dataset.display === 'night';
    document.querySelectorAll('[data-store-night-switch]').forEach(function (input) {
      input.checked = night;
    });
    document.querySelectorAll('[data-store-theme-status]').forEach(function (status) {
      status.textContent = night ? 'Night mode is on.' : 'Day mode is on.';
    });
  }

  function changeDisplay(mode, remember) {
    document.documentElement.dataset.display = mode === 'night' ? 'night' : 'day';
    if (remember) {
      try { window.localStorage.setItem(storageKey, document.documentElement.dataset.display); }
      catch (error) { /* Keep the selected display for this page. */ }
    }
    syncDisplayControls();
  }

  function openDialog(id, trigger) {
    var dialog = document.getElementById(id);
    if (!dialog) return;
    if (!trigger.closest('dialog')) returnFocus = trigger;
    document.querySelectorAll('.store-account-dialog[open]').forEach(function (other) {
      other.close();
    });
    dialog.showModal();
  }

  document.addEventListener('click', function (event) {
    var dismiss = event.target.closest('[data-store-dismiss]');
    if (dismiss) { dismiss.closest('.store-notice').remove(); return; }
    var opener = event.target.closest('[data-store-open]');
    if (opener) { openDialog(opener.dataset.storeOpen, opener); return; }
    var closer = event.target.closest('[data-store-close]');
    if (closer) closer.closest('dialog').close();
  });

  document.querySelectorAll('.store-account-dialog').forEach(function (dialog) {
    dialog.addEventListener('click', function (event) {
      if (event.target !== dialog) return;
      var rect = dialog.getBoundingClientRect();
      if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
    });
    dialog.addEventListener('close', function () {
      if (!document.querySelector('.store-account-dialog[open]') && returnFocus) returnFocus.focus();
    });
  });
  document.querySelectorAll('[data-store-night-switch]').forEach(function (input) {
    input.addEventListener('change', function () { changeDisplay(input.checked ? 'night' : 'day', true); });
  });
  window.addEventListener('storage', function (event) {
    if (event.key === storageKey || event.key === null) changeDisplay(event.newValue === 'night' ? 'night' : 'day', false);
  });
  // Forms already show their own Django alerts; avoid duplicate notifications.
  var notices = document.querySelector('.store-notices');
  if (notices && document.querySelector('[role="alert"]')) notices.remove();
  syncDisplayControls();
})();
