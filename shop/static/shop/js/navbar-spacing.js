(function () {
  const navbar = document.querySelector('.navbar.fixed-top');
  if (!navbar) return;

  // A fixed navbar needs its own space above the page content.
  function updateNavbarSpace() {
    document.body.style.paddingTop = navbar.offsetHeight + 'px';
  }

  updateNavbarSpace();
  window.addEventListener('resize', updateNavbarSpace);

  // Also update the space when the mobile menu opens or closes.
  if ('ResizeObserver' in window) {
    new ResizeObserver(updateNavbarSpace).observe(navbar);
  }
})();
