document.addEventListener('DOMContentLoaded', function () {
  var nav = document.querySelector('.main-nav');
  var toggle = document.querySelector('.mobile-menu-toggle');
  var navLinks = document.querySelector('.nav-links');
  var scrollPosition = 0;

  function lockBodyScroll() {
    scrollPosition = window.scrollY;
    document.body.style.position = 'fixed';
    document.body.style.top = '-' + scrollPosition + 'px';
    document.body.style.left = '0';
    document.body.style.right = '0';
    document.body.style.width = '100%';
  }

  function unlockBodyScroll() {
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.left = '';
    document.body.style.right = '';
    document.body.style.width = '';
    window.scrollTo(0, scrollPosition);
  }

  function closeAllDropdowns() {
    var dds = document.querySelectorAll('.dropdown.dropdown-open');
    for (var i = 0; i < dds.length; i++) {
      dds[i].classList.remove('dropdown-open');
    }
  }

  function closeMenu() {
    nav.classList.remove('menu-open');
    unlockBodyScroll();
    closeAllDropdowns();
  }

  function isMobile() {
    return window.innerWidth <= 768;
  }

  function toggleDropdown(el) {
    var dd = el.parentNode.querySelector('.dropdown');
    if (!dd) return;
    var openDds = document.querySelectorAll('.dropdown.dropdown-open');
    for (var j = 0; j < openDds.length; j++) {
      if (openDds[j] !== dd) openDds[j].classList.remove('dropdown-open');
    }
    dd.classList.toggle('dropdown-open');
  }

  // ── Hamburger toggle ──
  if (toggle && nav) {
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      nav.classList.toggle('menu-open');
      if (nav.classList.contains('menu-open')) {
        lockBodyScroll();
      } else {
        unlockBodyScroll();
      }
    });
  }

  // ── Dropdown toggle (touchstart for mobile, click fallback) ──
  var dropdownParents = document.querySelectorAll('.has-dropdown > a');
  for (var i = 0; i < dropdownParents.length; i++) {
    (function (el) {
      el.addEventListener('touchstart', function (e) {
        if (!isMobile()) return;
        el._touchFired = true;
        e.preventDefault();
        toggleDropdown(el);
      }, { passive: false });

      el.addEventListener('click', function (e) {
        if (!isMobile()) return;
        if (el._touchFired) {
          el._touchFired = false;
          return;
        }
        e.preventDefault();
        toggleDropdown(el);
      });
    })(dropdownParents[i]);
  }

  // ── Close menu after submenu link click (delegated) ──
  if (navLinks) {
    navLinks.addEventListener('click', function (e) {
      var link = e.target.closest('a');
      if (!link) return;
      if (!isMobile()) return;
      if (link.closest('.dropdown-content')) {
        closeMenu();
      }
    });
  }

  // ── Close menu when tapping outside ──
  document.addEventListener('click', function (e) {
    if (nav && nav.classList.contains('menu-open') && !nav.contains(e.target)) {
      closeMenu();
    }
  });
});
