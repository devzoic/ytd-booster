/**
 * App Main Controller & Router
 */
const App = {
  currentPage: 'dashboard',
  isEngineRunning: false,
  port: 8008,
  logs: [],
  maxLogs: 500,

  apiUrl(path) {
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    return `http://127.0.0.1:${this.port}${cleanPath}`;
  },

  pages: {
    dashboard: DashboardPage,
    settings: SettingsPage,
    profiles: ProfilesPage,
    logs: LogsPage
  },

  async init() {
    await this.loadPortConfig();
    this.setupNavigation();
    this.setupEngineToggle();
    this.setupTauriEvents();
    this.navigate('dashboard');
    this.checkInitialStatus();
  },

  async loadPortConfig() {
    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        const env = await window.__TAURI__.core.invoke('read_env');
        if (env && env.PORT) {
          this.port = parseInt(env.PORT, 10) || 8008;
        }
      }
    } catch (e) {}
  },

  setupNavigation() {
    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = btn.getAttribute('data-page');
        if (page) this.navigate(page);
      });
    });
  },

  navigate(pageId) {
    if (!this.pages[pageId]) return;

    // Teardown previous page
    if (this.pages[this.currentPage] && this.pages[this.currentPage].destroy) {
      this.pages[this.currentPage].destroy();
    }

    this.currentPage = pageId;

    // Update Sidebar Active state
    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-page') === pageId);
    });

    // Update Header Title
    const titles = {
      dashboard: 'Node Dashboard',
      settings: 'Environment & Configuration',
      profiles: 'Chrome Profiles',
      logs: 'Console Logs'
    };
    document.getElementById('current-page-title').innerText = titles[pageId] || 'YT Booster';

    // Render Page
    const container = document.getElementById('page-container');
    container.innerHTML = this.pages[pageId].render();

    // Initialize Page
    if (this.pages[pageId].init) {
      this.pages[pageId].init();
    }
  },

  setupEngineToggle() {
    const btn = document.getElementById('btn-engine-toggle');
    btn.addEventListener('click', async () => {
      if (this.isEngineRunning) {
        await this.stopEngine();
      } else {
        await this.startEngine();
      }
    });
  },

  async startEngine() {
    this.updateEngineUI('starting');
    Toast.info('Starting YT Booster Python Engine...');
    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        await window.__TAURI__.core.invoke('start_engine');
        
        // Poll for server readiness
        let attempts = 0;
        let ready = false;
        while (attempts < 20 && !ready) {
          await new Promise(r => setTimeout(r, 500));
          attempts++;
          try {
            const res = await fetch(this.apiUrl('/dashboard/api/stats'), { signal: AbortSignal.timeout(1000) });
            if (res.ok) {
              ready = true;
              break;
            }
          } catch (e) {}
        }

        this.updateEngineUI(true);
        Toast.success('Engine started successfully!');
      } else {
        setTimeout(() => {
          this.updateEngineUI(true);
          Toast.success('Engine started (Preview Mode)');
        }, 1000);
      }
    } catch (e) {
      this.updateEngineUI(false);
      Toast.error(`Failed to start engine: ${e}`);
    }
  },

  async stopEngine() {
    this.updateEngineUI('stopping');
    Toast.info('Stopping YT Booster Engine...');
    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        const res = await window.__TAURI__.core.invoke('stop_engine');
        this.updateEngineUI(false);
        Toast.success(res || 'Engine stopped');
      } else {
        this.updateEngineUI(false);
        Toast.success('Engine stopped (Preview Mode)');
      }
    } catch (e) {
      this.updateEngineUI(false);
      Toast.error(`Failed to stop engine: ${e}`);
    }
  },

  updateEngineUI(state) {
    const badge = document.getElementById('engine-badge');
    const btn = document.getElementById('btn-engine-toggle');
    const statusDot = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    if (!badge || !btn || !statusDot || !statusText) return;

    if (state === 'starting') {
      this.isEngineRunning = false;
      badge.className = 'engine-badge starting';
      badge.innerHTML = '<span class="engine-status-dot"></span><span>Starting...</span>';

      btn.className = 'btn btn-primary';
      btn.disabled = true;
      btn.innerHTML = `
        <svg class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>Starting Engine...</span>
      `;

      statusDot.className = 'status-dot starting';
      statusText.innerText = 'Starting Engine...';
    } else if (state === 'stopping') {
      this.isEngineRunning = false;
      badge.className = 'engine-badge starting';
      badge.innerHTML = '<span class="engine-status-dot"></span><span>Stopping...</span>';

      btn.className = 'btn btn-danger';
      btn.disabled = true;
      btn.innerHTML = `
        <svg class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>Stopping Engine...</span>
      `;

      statusDot.className = 'status-dot starting';
      statusText.innerText = 'Stopping Engine...';
    } else if (state === true || state === 'running') {
      this.isEngineRunning = true;
      badge.className = 'engine-badge';
      badge.innerHTML = '<span class="engine-status-dot"></span><span>Running</span>';
      
      btn.className = 'btn btn-danger';
      btn.disabled = false;
      btn.innerHTML = `
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="6" y="6" width="12" height="12"/>
        </svg>
        <span>Stop Engine</span>
      `;

      statusDot.className = 'status-dot pulsing';
      statusText.innerText = 'Engine Running';
    } else {
      this.isEngineRunning = false;
      badge.className = 'engine-badge stopped';
      badge.innerHTML = '<span class="engine-status-dot"></span><span>Stopped</span>';

      btn.className = 'btn btn-primary';
      btn.disabled = false;
      btn.innerHTML = `
        <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        <span>Start Engine</span>
      `;

      statusDot.className = 'status-dot stopped';
      statusText.innerText = 'Engine Offline';
    }
  },

  setupTauriEvents() {
    if (window.__TAURI__ && window.__TAURI__.event) {
      // Listen for stdout/stderr logs from the sidecar
      window.__TAURI__.event.listen('engine-log', (event) => {
        const log = event.payload;
        this.logs.push(log);
        if (this.logs.length > this.maxLogs) this.logs.shift();

        const badge = document.getElementById('logs-badge');
        if (badge) badge.innerText = `${this.logs.length}`;

        // Stream to dashboard mini terminal
        const dashTerm = document.getElementById('dashboard-terminal');
        if (dashTerm) {
          const div = document.createElement('div');
          div.className = 'log-line';
          div.innerHTML = `
            <span class="log-time">[${log.timestamp}]</span>
            <span class="log-level-${log.level}">${log.level.toUpperCase()}</span>
            <span class="log-msg">${log.message}</span>
          `;
          dashTerm.appendChild(div);
          dashTerm.scrollTop = dashTerm.scrollHeight;
        }

        // If logs page is active, append to full terminal
        if (this.currentPage === 'logs' && LogsPage.appendLog) {
          LogsPage.appendLog(log);
        }
      });

      // Listen for process status changes
      window.__TAURI__.event.listen('engine-status', (event) => {
        const status = event.payload;
        this.updateEngineUI(status.running);
      });

      // Listen for tray navigation events
      window.__TAURI__.event.listen('navigate', (event) => {
        this.navigate(event.payload);
      });
    }
  },

  async checkInitialStatus() {
    let isRunning = false;
    if (window.__TAURI__ && window.__TAURI__.core) {
      try {
        const status = await window.__TAURI__.core.invoke('get_engine_status');
        isRunning = !!status.running;
      } catch (e) {
        console.warn('Tauri get_engine_status failed:', e);
      }
    }

    if (!isRunning) {
      // Dynamic fallback check if Python server is already responding on configured port
      try {
        const res = await fetch(this.apiUrl('/dashboard/api/stats'), { signal: AbortSignal.timeout(1500) });
        if (res.ok) isRunning = true;
      } catch (e) {}
    }

    this.updateEngineUI(isRunning);
  }
};

// Boot application
window.addEventListener('DOMContentLoaded', () => {
  App.init();
});
