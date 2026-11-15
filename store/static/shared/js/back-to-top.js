(function () {
  // This shared script adds the same button to every page.
  const button = document.createElement('button');
  button.id = 'back-to-top';
  button.className = 'back-to-top';
  button.type = 'button';
  button.textContent = '↑';
  button.title = 'Back to top';
  button.setAttribute('aria-label', 'Back to top');
  document.body.appendChild(button);

  function showButton() {
    button.classList.toggle('is-visible', window.scrollY > 300);
  }

  window.addEventListener('scroll', showButton, { passive: true });
  showButton();

  button.addEventListener('click', function () {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
  });
})();
