document.addEventListener('DOMContentLoaded', () => {
  const nav = document.querySelector('.main-nav');
  const toggle = document.querySelector('.mobile-menu-toggle');
  const navLinks = document.querySelector('.nav-links');
  let scrollPosition = 0;

  function lockBodyScroll() {
    scrollPosition = window.scrollY;
    document.body.style.position = 'fixed';
    document.body.style.top = '-' + scrollPosition + 'px';
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

  // Hamburger toggle
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

  // Direct click handlers on dropdown parent links for mobile
  var dropdownParents = document.querySelectorAll('.has-dropdown > a');
  for (var i = 0; i < dropdownParents.length; i++) {
    dropdownParents[i].addEventListener('click', function (e) {
      if (window.innerWidth <= 768) {
        e.preventDefault();
        var dd = this.parentNode.querySelector('.dropdown');
        if (dd) {
          // Close other open dropdowns
          var openDds = document.querySelectorAll('.dropdown.dropdown-open');
          for (var j = 0; j < openDds.length; j++) {
            if (openDds[j] !== dd) {
              openDds[j].classList.remove('dropdown-open');
            }
          }
          dd.classList.toggle('dropdown-open');
        }
      }
    });
  }

  // Close menu after submenu link click
  if (navLinks) {
    navLinks.addEventListener('click', function (e) {
      var link = e.target.closest('a');
      if (!link) return;
      if (window.innerWidth > 768) return;

      // Only close if clicking a link inside a dropdown (submenu item)
      if (link.closest('.dropdown-content')) {
        closeMenu();
      }
    });
  }

  // Close menu when clicking outside
  document.addEventListener('click', function (e) {
    if (nav && nav.classList.contains('menu-open') && !nav.contains(e.target)) {
      closeMenu();
    }
  });
});
