(function () {
  const dialog = document.getElementById('club-map');
  if (!dialog) return;
  document.querySelectorAll('[data-club-map]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      if (typeof dialog.showModal !== 'function') return;
      event.preventDefault();
      dialog.showModal();
    });
  });
  dialog.querySelector('.club-map-close').addEventListener('click', function () { dialog.close(); });
  dialog.querySelector('form').addEventListener('submit', function (event) {
    event.preventDefault();
    const address = dialog.querySelector('input').value.trim();
    if (!address) return;
    const frame = dialog.querySelector('iframe');
    const link = dialog.querySelector('.club-map-link');
    frame.src = 'https://maps.google.com/maps?q=' + encodeURIComponent(address) + '&output=embed';
    frame.hidden = false;
    link.href = 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(address);
    link.hidden = false;
  });
})();
