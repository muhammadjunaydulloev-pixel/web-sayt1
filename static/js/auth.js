/* Cinematic login / register entrance */
(function () {
  'use strict';

  var stage = document.querySelector('.auth-stage');
  if (!stage) return;

  requestAnimationFrame(function () {
    document.body.classList.add('auth-ready');
  });

  document.querySelectorAll('[data-toggle-password]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var id = btn.getAttribute('data-toggle-password');
      var input = id && document.getElementById(id);
      if (!input) return;
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.classList.toggle('is-on', show);
      btn.setAttribute('aria-label', show ? 'Пинҳон кардани парол' : 'Нишон додани парол');
    });
  });

  var form = stage.querySelector('form');
  if (form) {
    form.addEventListener('submit', function () {
      var submit = form.querySelector('button[type="submit"]');
      if (submit) {
        submit.classList.add('is-loading');
        submit.disabled = true;
      }
    });
  }
})();
