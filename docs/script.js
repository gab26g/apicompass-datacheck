const menu = document.querySelector('.menu');
const nav = document.querySelector('#chapter-nav');
const mobile = window.matchMedia('(max-width: 730px)');
function syncMenu() {
  nav.hidden = mobile.matches;
  menu.setAttribute('aria-expanded', String(!nav.hidden));
}
menu.addEventListener('click', () => {
  nav.hidden = !nav.hidden;
  menu.setAttribute('aria-expanded', String(!nav.hidden));
});
mobile.addEventListener('change', syncMenu);
syncMenu();
nav.addEventListener('click', event => {
  if (event.target.closest('a') && mobile.matches) {
    nav.hidden = true;
    menu.setAttribute('aria-expanded', 'false');
  }
});
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (entry.isIntersecting) {
        nav.querySelectorAll('a').forEach(link => {
          if (link.hash === '#' + entry.target.id) link.setAttribute('aria-current', 'true');
          else link.removeAttribute('aria-current');
        });
      }
    }
  }, {rootMargin: '-8% 0px -65% 0px'});
  document.querySelectorAll('main section[id]').forEach(section => observer.observe(section));
}
