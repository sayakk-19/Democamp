(function () {
  'use strict';
  var mode = 'day';
  try {
    if (window.localStorage.getItem('democamp_display_mode') === 'night') mode = 'night';
  } catch (error) {
    // Display still works when browser storage is unavailable.
  }
  document.documentElement.dataset.display = mode;
})();
