/* Panoptiqa — frontend */

// Register service worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/static/sw.js')
      .catch(err => console.warn('[SW] Registration failed:', err));
  });
}

// Format dates: local timezone, locale-appropriate 12/24h, · separator
document.querySelectorAll('.article-date[data-datetime]').forEach(function (el) {
  var iso = el.getAttribute('data-datetime');
  if (!iso) return;
  try {
    var d = new Date(iso);
    var date = d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    var time = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
    el.textContent = date + ' · ' + time;
  } catch (e) {}
});

// Hamburger menu
(function () {
  const hamburger = document.getElementById('hamburger');
  const mobileNav = document.getElementById('mobile-nav');
  if (!hamburger || !mobileNav) return;

  function closeNav() {
    mobileNav.classList.remove('open');
    mobileNav.setAttribute('aria-hidden', 'true');
    hamburger.classList.remove('open');
    hamburger.setAttribute('aria-expanded', 'false');
  }

  hamburger.addEventListener('click', function (e) {
    e.stopPropagation();
    var opening = !mobileNav.classList.contains('open');
    if (opening) {
      mobileNav.classList.add('open');
      mobileNav.setAttribute('aria-hidden', 'false');
      hamburger.classList.add('open');
      hamburger.setAttribute('aria-expanded', 'true');
    } else {
      closeNav();
    }
  });

  mobileNav.querySelectorAll('a').forEach(function (link) {
    link.addEventListener('click', closeNav);
  });

  document.addEventListener('click', function (e) {
    if (!hamburger.contains(e.target) && !mobileNav.contains(e.target)) closeNav();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeNav();
  });
}());

// User menu dropdown
(function () {
  var trigger = document.getElementById('user-menu-trigger');
  var dropdown = document.getElementById('user-menu-dropdown');
  if (!trigger || !dropdown) return;

  function close() {
    dropdown.classList.remove('open');
    trigger.setAttribute('aria-expanded', 'false');
  }

  trigger.addEventListener('click', function (e) {
    e.stopPropagation();
    var opening = !dropdown.classList.contains('open');
    dropdown.classList.toggle('open', opening);
    trigger.setAttribute('aria-expanded', String(opening));
  });

  document.addEventListener('click', function (e) {
    if (!trigger.contains(e.target) && !dropdown.contains(e.target)) close();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') close();
  });
}());

// Theme toggle
(function () {
  var btn = document.getElementById('theme-toggle');
  if (!btn) return;
  btn.addEventListener('click', function () {
    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var next = isDark ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
  });
}());

// Show a toast after 5 minutes suggesting a refresh
setTimeout(() => {
  const toast = document.createElement('div');
  toast.className = 'refresh-toast';
  toast.innerHTML = 'New articles may be available <button onclick="location.reload()">Refresh</button>';
  document.body.appendChild(toast);
}, 5 * 60 * 1000);
