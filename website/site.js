(() => {
  'use strict';
  const config = JSON.parse(document.querySelector('#page-config').textContent);
  const feedback = document.querySelector('#feedback');
  const scenes = ['ask', 'review', 'receive'];
  const images = ['chat-result.png', 'review-approval.png', 'make-file.png'];
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  let scene = 0, platform = 0, feedbackTimer;
  function announce(message, persistent = false) {
    clearTimeout(feedbackTimer); feedback.textContent = message; feedback.hidden = false;
    if (!persistent) feedbackTimer = setTimeout(() => { feedback.hidden = true; }, 4500);
  }
  async function copy(value, success, failure) {
    try { await navigator.clipboard.writeText(value); announce(success); }
    catch { announce(`${failure} ${value}`, true); }
  }
  function selectScene(index, updateURL = true) {
    scene = index;
    document.querySelectorAll('[data-scene]').forEach((button, i) => {
      button.setAttribute('aria-selected', String(i === scene)); button.tabIndex = i === scene ? 0 : -1;
    });
    const image = document.querySelector('#tour-image');
    image.src = `/assets/${images[scene]}`; image.alt = config.screenalts[scene];
    document.querySelector('#tour-panel').setAttribute('aria-labelledby', `scene-${scene}`);
    document.querySelector('#tour-caption').textContent = `${config.captions[scene]} · ${config.sample}`;
    document.querySelector('#example-request').textContent = config.requests[scene];
    if (!reduce.matches) image.animate([{opacity: .5, transform: 'translateY(6px)'}, {opacity: 1, transform: 'translateY(0)'}], {duration: 230});
    if (updateURL) { const url = new URL(location.href); url.searchParams.set('workflow', scenes[scene]); history.replaceState(null, '', url); }
  }
  function selectPlatform(index) {
    platform = index;
    document.querySelectorAll('[data-platform]').forEach((button, i) => {
      button.setAttribute('aria-selected', String(i === platform)); button.tabIndex = i === platform ? 0 : -1;
    });
    document.querySelector('#install-content').setAttribute('aria-labelledby', `platform-${platform}`);
    document.querySelector('#install-command').textContent = config.commands[platform];
    document.querySelector('#install-note').textContent = platform ? config.servernote : config.macnote;
    const guide = document.querySelector('#install-guide'); guide.href = config.guideLinks[platform];
    guide.replaceChildren(document.createTextNode(`${config.guides[platform]} `));
  }
  document.querySelectorAll('[data-scene]').forEach(button => button.addEventListener('click', () => selectScene(Number(button.dataset.scene))));
  document.querySelectorAll('[data-platform]').forEach(button => button.addEventListener('click', () => selectPlatform(Number(button.dataset.platform))));
  for (const [selector, choose, size] of [['[data-scene]', selectScene, 3], ['[data-platform]', selectPlatform, 2]]) {
    const tabs = [...document.querySelectorAll(selector)];
    tabs.forEach((tab, i) => tab.addEventListener('keydown', event => {
      const next = event.key === 'ArrowRight' ? (i + 1) % size : event.key === 'ArrowLeft' ? (i + size - 1) % size : event.key === 'Home' ? 0 : event.key === 'End' ? size - 1 : null;
      if (next === null) return; event.preventDefault(); choose(next); tabs[next].focus();
    }));
  }
  document.querySelector('#copy-request').addEventListener('click', () => copy(config.requests[scene], config.copied, config.copyfailed));
  document.querySelector('#copy-install').addEventListener('click', () => copy(config.commands[platform], config.copied, config.copyfailed));
  document.querySelector('#share-workflow').addEventListener('click', async () => {
    const url = new URL(config.lang === 'it' ? '/it/' : '/', location.origin);
    url.searchParams.set('workflow', scenes[scene]); url.searchParams.set('utm_source', 'workflow_share'); url.searchParams.set('utm_medium', 'share'); url.searchParams.set('utm_campaign', 'launch'); url.hash = 'tour';
    if (navigator.share) {
      try { await navigator.share({title: 'OpenDuet', text: config.requests[scene], url: url.href}); }
      catch (error) { if (error.name !== 'AbortError') await copy(url.href, config.shared, config.sharefailed); }
    } else await copy(url.href, config.shared, config.sharefailed);
  });
  const dialog = document.querySelector('#image-dialog');
  document.querySelectorAll('[data-enlarge]').forEach(button => button.addEventListener('click', () => {
    const source = button.querySelector('img'), target = document.querySelector('#expanded-image');
    target.src = source.src; target.alt = source.alt; dialog.showModal();
  }));
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  if ('IntersectionObserver' in window && !reduce.matches) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.animate([{opacity: .35, transform: 'translateY(18px)'}, {opacity: 1, transform: 'translateY(0)'}], {duration: 420, easing: 'cubic-bezier(.2,.6,.2,1)'});
      observer.unobserve(entry.target);
    }), {threshold: .08});
    document.querySelectorAll('.reveal').forEach(element => observer.observe(element));
  }
  const requested = scenes.indexOf(new URLSearchParams(location.search).get('workflow'));
  selectScene(requested < 0 ? 0 : requested, false); selectPlatform(0);
})();
