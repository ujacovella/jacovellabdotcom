document.addEventListener('DOMContentLoaded', function () {
  var nav = document.querySelector('.main-nav');
  var toggle = document.querySelector('.mobile-menu-toggle');
  var navLinks = document.querySelector('.nav-links');
  var scrollPosition = 0;
  var touchFired = false;

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

  // ── Dropdown toggle (touchstart for iOS reliability, click for desktop) ──
  function setupDropdownToggle(el) {
    // Touchstart: fires reliably on iOS inside position:fixed containers
    el.addEventListener('touchstart', function (e) {
      if (!isMobile()) return;
      var dd = this.parentNode.querySelector('.dropdown');
      if (dd) {
        touchFired = true;
        e.preventDefault();
        var openDds = document.querySelectorAll('.dropdown.dropdown-open');
        for (var j = 0; j < openDds.length; j++) {
          if (openDds[j] !== dd) openDds[j].classList.remove('dropdown-open');
        }
        dd.classList.toggle('dropdown-open');
      }
    }, { passive: false });

    // Click: for desktop / non-touch devices
    el.addEventListener('click', function (e) {
      if (touchFired) {
        touchFired = false;
        return;
      }
      if (!isMobile()) return;
      var dd = this.parentNode.querySelector('.dropdown');
      if (dd) {
        e.preventDefault();
        var openDds = document.querySelectorAll('.dropdown.dropdown-open');
        for (var j = 0; j < openDds.length; j++) {
          if (openDds[j] !== dd) openDds[j].classList.remove('dropdown-open');
        }
        dd.classList.toggle('dropdown-open');
      }
    });
  }

  var dropdownParents = document.querySelectorAll('.has-dropdown > a');
  for (var i = 0; i < dropdownParents.length; i++) {
    setupDropdownToggle(dropdownParents[i]);
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
