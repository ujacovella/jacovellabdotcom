document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.main-nav');
  const toggle = document.querySelector('.mobile-menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  let scrollPosition = 0;

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

  if (navLinks) {
    navLinks.addEventListener('click', (e) => {
      const link = e.target.closest('a');
      if (!link) return;

      if (window.innerWidth <= 768) {
        const li = link.closest('li');
        if (li && li.classList.contains('has-dropdown') && !link.closest('.dropdown')) {
          e.preventDefault();
          const dropdown = li.querySelector('.dropdown');
          if (dropdown) {
            dropdown.classList.toggle('dropdown-open');
          }
          return;
        }
      }

      if (nav && nav.classList.contains('menu-open') &&
          (!link.closest('.has-dropdown') || link.closest('.dropdown-content'))) {
        closeMenu();
      }
    });
  }

  document.addEventListener('click', (e) => {
    if (nav && nav.classList.contains('menu-open') && !nav.contains(e.target)) {
      closeMenu();
    }
  });
});
