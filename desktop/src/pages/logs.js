/**
 * Live Logs Terminal Page
 */
const LogsPage = {
  autoScroll: true,

  render() {
    return `
      <div class="card-section" style="height: calc(100vh - 130px); display: flex; flex-direction: column; padding: 0; overflow: hidden;">
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); background: rgba(255,255,255,0.02);">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div class="card-title" style="margin-bottom: 0;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green)" stroke-width="2">
                <polyline points="4 17 10 11 4 5"/>
                <line x1="12" y1="19" x2="20" y2="19"/>
              </svg>
              <span>Engine Console Logs</span>
            </div>
            <span class="badge badge-info" id="logs-count">0 Lines</span>
          </div>

          <div style="display: flex; align-items: center; gap: 10px;">
            <button class="btn btn-ghost" style="padding: 6px 12px; font-size: 12px;" onclick="LogsPage.toggleAutoScroll()">
              <span id="autoscroll-label">Auto-Scroll: ON</span>
            </button>
            <button class="btn btn-ghost" style="padding: 6px 12px; font-size: 12px;" onclick="LogsPage.clearLogs()">
              <span>Clear Console</span>
            </button>
          </div>
        </div>

        <div class="terminal-body" id="full-terminal-body" style="flex: 1; padding: 18px 20px; background: var(--bg-terminal);">
          <!-- Streaming logs injected here -->
        </div>
      </div>
    `;
  },

  init() {
    this.renderExistingLogs();
  },

  destroy() {},

  renderExistingLogs() {
    const container = document.getElementById('full-terminal-body');
    if (!container) return;

    container.innerHTML = App.logs.map(log => `
      <div class="log-line">
        <span class="log-time">[${log.timestamp || '00:00:00'}]</span>
        <span class="log-level-${log.level}">${log.level.toUpperCase()}</span>
        <span class="log-msg">${this.escapeHtml(log.message)}</span>
      </div>
    `).join('');

    document.getElementById('logs-count').innerText = `${App.logs.length} Lines`;

    if (this.autoScroll) {
      container.scrollTop = container.scrollHeight;
    }
  },

  appendLog(log) {
    const container = document.getElementById('full-terminal-body');
    if (!container) return;

    const div = document.createElement('div');
    div.className = 'log-line';
    div.innerHTML = `
      <span class="log-time">[${log.timestamp || '00:00:00'}]</span>
      <span class="log-level-${log.level}">${log.level.toUpperCase()}</span>
      <span class="log-msg">${this.escapeHtml(log.message)}</span>
    `;

    container.appendChild(div);
    const count = document.getElementById('logs-count');
    if (count) count.innerText = `${App.logs.length} Lines`;

    if (this.autoScroll) {
      container.scrollTop = container.scrollHeight;
    }
  },

  toggleAutoScroll() {
    this.autoScroll = !this.autoScroll;
    const label = document.getElementById('autoscroll-label');
    if (label) {
      label.innerText = `Auto-Scroll: ${this.autoScroll ? 'ON' : 'OFF'}`;
    }
  },

  clearLogs() {
    App.logs = [];
    const container = document.getElementById('full-terminal-body');
    if (container) container.innerHTML = '';
    const badge = document.getElementById('logs-badge');
    if (badge) badge.innerText = '0';
    const count = document.getElementById('logs-count');
    if (count) count.innerText = '0 Lines';
    Toast.info('Console logs cleared.');
  },

  escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
};
