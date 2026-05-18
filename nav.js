document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.main-nav');
  const toggle = document.querySelector('.mobile-menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  const isMobile = () => window.innerWidth <= 768;
  let scrollPosition = 0;
  let touchHandled = false;

  function lockBodyScroll() {
    scrollPosition = window.scrollY;
    document.body.style.position = 'fixed';
    document.body.style.top = `-${scrollPosition}px`;
    document.body.style.left = '0';
    document.body.style.right = '0';
  }

  function unlockBodyScroll() {
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.left = '';
    document.body.style.right = '';
    window.scrollTo(0, scrollPosition);
  }

  function closeAllDropdowns() {
    document.querySelectorAll('.dropdown.dropdown-open').forEach(dd => {
      dd.classList.remove('dropdown-open');
    });
  }

  function closeMenu() {
    nav.classList.remove('menu-open');
    unlockBodyScroll();
    closeAllDropdowns();
  }

  function toggleDropdown(link) {
    const li = link.closest('li');
    if (li && li.classList.contains('has-dropdown') && !link.closest('.dropdown')) {
      const dropdown = li.querySelector('.dropdown');
      if (dropdown) {
        dropdown.classList.toggle('dropdown-open');
      }
      return true;
    }
    return false;
  }

  if (navLinks) {
    navLinks.addEventListener('touchstart', (e) => {
      if (!isMobile()) return;
      const link = e.target.closest('a');
      if (!link) return;
      if (toggleDropdown(link)) {
        e.preventDefault();
        touchHandled = true;
      }
    }, { passive: false });

    navLinks.addEventListener('click', (e) => {
      if (touchHandled) {
        touchHandled = false;
        return;
      }

      const link = e.target.closest('a');
      if (!link) return;

      if (isMobile() && toggleDropdown(link)) {
        e.preventDefault();
        return;
      }

      if (nav && nav.classList.contains('menu-open') &&
          (!link.closest('.has-dropdown') || link.closest('.dropdown-content'))) {
        closeMenu();
      }
    });
  }

  if (toggle && nav) {
    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      nav.classList.toggle('menu-open');
      if (nav.classList.contains('menu-open')) {
        lockBodyScroll();
      } else {
        unlockBodyScroll();
      }
    });
  }

  document.addEventListener('click', (e) => {
    if (nav && nav.classList.contains('menu-open') && !nav.contains(e.target)) {
      closeMenu();
    }
  });
});
