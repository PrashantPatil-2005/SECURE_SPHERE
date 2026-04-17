/**
 * SecuriSphere Browser Agent (ShopSphere)
 *
 * Lightweight client-side collector that hooks into fetch / XHR / form
 * submissions / DOM mutations, runs lightweight regex detection for
 * SQLi / path traversal / XSS payloads, and batches security events
 * to the SecuriSphere browser-monitor ingest endpoint every 2 seconds.
 *
 * site_id is read from window.__SECURISPHERE_SITE_ID__ (injected by
 * the backend snippet returned from POST /api/register-site).
 */
(function () {
  'use strict';

  var CONFIG = {
    INGEST_URL: window.__SECURISPHERE_INGEST__ || 'http://localhost:5090/api/ingest',
    BATCH_INTERVAL_MS: 2000,
    MAX_BATCH_SIZE: 50,
    SITE_ID: window.__SECURISPHERE_SITE_ID__ || 'unregistered',
    MAX_BODY_SAMPLE: 1024
  };

  // ── Detection regexes ────────────────────────────────────────────────
  // Kept deliberately small — real correlation happens server-side; the
  // agent's job is just to tag obvious payloads so the backend can raise
  // severity early.
  var PATTERNS = {
    sqli:           /('|%27|--|\bunion\s+select\b|\bdrop\s+table\b|\bor\s+1=1\b|sleep\(|benchmark\()/i,
    path_traversal: /(\.\.\/|\.\.\\|%2e%2e%2f|%2e%2e\/)/i,
    xss:            /(<script[^>]*>|javascript:|onerror\s*=|onload\s*=|<iframe[^>]*>)/i
  };

  var queue = [];

  /**
   * Run the detection regexes over a URL and request body.
   * Returns a {severity, tags} object suitable for dropping into an event.
   */
  function classify(url, body) {
    var target = (url || '') + ' ' + (body || '');
    var tags = [];
    var severity = 'INFO';
    if (PATTERNS.sqli.test(target))           { tags.push('sql-injection');  severity = 'HIGH'; }
    if (PATTERNS.path_traversal.test(target)) { tags.push('path-traversal'); severity = 'HIGH'; }
    if (PATTERNS.xss.test(target))            { tags.push('xss-attempt');    severity = 'HIGH'; }
    // fallback MEDIUM for non-same-origin POSTs to auth paths
    if (severity === 'INFO' && /\/(auth|login|signin)/i.test(url || '')) {
      severity = 'MEDIUM';
      tags.push('auth-surface');
    }
    return { severity: severity, tags: tags };
  }

  /**
   * Build a normalized SecuriSphere event from a captured browser action.
   * All fields required by the browser-monitor ingest validator are set here.
   */
  function buildEvent(type, url, method, body) {
    var c = classify(url, body);
    var pathname;
    try { pathname = new URL(url, location.href).pathname; }
    catch (_) { pathname = url || ''; }
    return {
      event_type:       type,
      source_layer:     'browser-agent',
      site_id:          CONFIG.SITE_ID,
      target_entity:    pathname,
      target_url:       url,
      severity:         c.severity,
      correlation_tags: c.tags,
      timestamp:        new Date().toISOString(),
      method:           method || 'GET',
      page_url:         location.href,
      user_agent:       navigator.userAgent
    };
  }

  /**
   * Append an event to the flush queue. Wrapped in try/catch so a failure
   * inside the agent can never break the host ShopSphere page.
   */
  function enqueue(ev) {
    try {
      queue.push(ev);
      if (queue.length >= CONFIG.MAX_BATCH_SIZE) { flush(); }
    } catch (_) { /* never crash host */ }
  }

  /**
   * Drain the queue and POST it to the ingest endpoint. Failures are
   * swallowed on purpose — the agent must not surface network errors
   * to the host page.
   */
  function flush() {
    if (queue.length === 0) { return; }
    var batch = queue.splice(0, queue.length);
    try {
      // Use the ORIGINAL fetch reference to avoid feeding our own
      // instrumentation calls back into the queue.
      origFetch.call(window, CONFIG.INGEST_URL, {
        method:  'POST',
        mode:    'cors',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ events: batch }),
        keepalive: true
      }).catch(function () { /* ignore */ });
    } catch (_) { /* ignore */ }
  }

  // ── fetch() monkey-patch ─────────────────────────────────────────────
  var origFetch = window.fetch ? window.fetch.bind(window) : null;
  if (origFetch) {
    window.fetch = function (input, init) {
      try {
        var url    = typeof input === 'string' ? input : (input && input.url) || '';
        var method = (init && init.method) || (typeof input === 'object' && input.method) || 'GET';
        var body   = init && init.body ? String(init.body).slice(0, CONFIG.MAX_BODY_SAMPLE) : '';
        // Don't record our own ingest calls.
        if (url.indexOf(CONFIG.INGEST_URL) !== 0) {
          enqueue(buildEvent('fetch_request', url, method, body));
        }
      } catch (_) { /* ignore */ }
      return origFetch.apply(window, arguments);
    };
  }

  // ── XMLHttpRequest monkey-patch ──────────────────────────────────────
  try {
    var origOpen = XMLHttpRequest.prototype.open;
    var origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (method, url) {
      try { this.__ss_method = method; this.__ss_url = url; } catch (_) {}
      return origOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function (body) {
      try {
        var sample = body ? String(body).slice(0, CONFIG.MAX_BODY_SAMPLE) : '';
        enqueue(buildEvent('xhr_request', this.__ss_url || '', this.__ss_method || 'GET', sample));
      } catch (_) {}
      return origSend.apply(this, arguments);
    };
  } catch (_) { /* ignore */ }

  // ── PerformanceObserver: catches resources loaded outside fetch/XHR ──
  try {
    var obs = new PerformanceObserver(function (list) {
      list.getEntries().forEach(function (entry) {
        if (entry.initiatorType === 'fetch' || entry.initiatorType === 'xmlhttprequest') { return; }
        enqueue(buildEvent('resource_load', entry.name, 'GET', ''));
      });
    });
    obs.observe({ type: 'resource', buffered: true });
  } catch (_) { /* ignore */ }

  // ── Form submission capture ──────────────────────────────────────────
  document.addEventListener('submit', function (e) {
    try {
      var form = e.target;
      if (!form || !form.action) { return; }
      var data = new FormData(form);
      var parts = [];
      data.forEach(function (v, k) { parts.push(k + '=' + String(v).slice(0, 128)); });
      var body = parts.join('&').slice(0, CONFIG.MAX_BODY_SAMPLE);
      enqueue(buildEvent('form_submit', form.action, (form.method || 'POST').toUpperCase(), body));
    } catch (_) {}
  }, true);

  // ── DOM mutation: watch for suspicious <script> / <iframe> injection ──
  try {
    var mo = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        (m.addedNodes || []).forEach(function (node) {
          if (!node || !node.tagName) { return; }
          var tag = node.tagName.toLowerCase();
          if (tag === 'script' || tag === 'iframe') {
            var src = node.src || (node.innerHTML || '').slice(0, 256);
            enqueue(buildEvent('dom_mutation', src, 'DOM', tag));
          }
        });
      });
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });
  } catch (_) { /* ignore */ }

  // ── Periodic flush + final flush on unload ───────────────────────────
  setInterval(flush, CONFIG.BATCH_INTERVAL_MS);
  window.addEventListener('beforeunload', flush);
})();
