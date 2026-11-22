/* Theme preference is optional; content never depends on JavaScript. */
const root = document.documentElement;
try {
  root.dataset.theme = localStorage.getItem('knotrel-performance-theme') || 'dark';
} catch (_) {
  root.dataset.theme = 'dark';
}
const button = document.getElementById('theme');
function updateLabel() {
  const label = `Switch to ${root.dataset.theme === 'light' ? 'dark' : 'light'} mode`;
  button.setAttribute('aria-label', label);
  button.title = label;
}
updateLabel();
button.addEventListener('click', () => {
  root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
  updateLabel();
  try { localStorage.setItem('knotrel-performance-theme', root.dataset.theme); } catch (_) {}
});
