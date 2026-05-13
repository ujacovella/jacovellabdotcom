document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.main-nav');
  const toggle = document.querySelector('.mobile-menu-toggle');
  const links = document.querySelectorAll('.nav-links a');
  const hasDropdown = document.querySelectorAll('.has-dropdown');

  if (toggle && nav) {
    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      nav.classList.toggle('menu-open');
      // Prevent scrolling when menu is open
      document.body.style.overflow = nav.classList.contains('menu-open') ? 'hidden' : '';
    });
  }

  // Handle dropdowns on mobile
  hasDropdown.forEach(item => {
    const link = item.querySelector('a');
    link.addEventListener('click', (e) => {
      if (window.innerWidth <= 768) {
        e.preventDefault();
        e.stopPropagation();
        item.classList.toggle('menu-item-open');
      }
    });
  });

  // Close menu when a link is clicked (retract after click)
  links.forEach(link => {
    link.addEventListener('click', () => {
      if (nav.classList.contains('menu-open') && !link.closest('.has-dropdown')) {
        nav.classList.remove('menu-open');
        document.body.style.overflow = '';
      }
      
      // If it's a dropdown link, close the whole menu
      if (link.closest('.dropdown-content')) {
        nav.classList.remove('menu-open');
        document.body.style.overflow = '';
      }
    });
  });

  // Close menu when clicking outside
  document.addEventListener('click', (e) => {
    if (nav.classList.contains('menu-open') && !nav.contains(e.target)) {
      nav.classList.remove('menu-open');
      document.body.style.overflow = '';
    }
  });
});
