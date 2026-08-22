/**
 * Software Updates Page
 * Dedicated page for checking, downloading, and managing app updates.
 */
const UpdatesPage = {

  render() {
    return `
      <div class="updates-page">
        <!-- Current Version Card -->
        <div class="card-section">
          <div class="card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green, #22c55e)" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            <span>App Information</span>
          </div>

          <div class="updates-info-grid">
            <div class="updates-info-item">
              <div class="updates-info-label">Application</div>
              <div class="updates-info-value">YT Booster Node</div>
            </div>
            <div class="updates-info-item">
              <div class="updates-info-label">Installed Version</div>
              <div class="updates-info-value" id="updates-current-version">v1.1.0</div>
            </div>
            <div class="updates-info-item">
              <div class="updates-info-label">Platform</div>
              <div class="updates-info-value" id="updates-platform">Desktop</div>
            </div>
            <div class="updates-info-item">
              <div class="updates-info-label">Update Channel</div>
              <div class="updates-info-value">Stable</div>
            </div>
          </div>
        </div>

        <!-- Check for Updates Card -->
        <div class="card-section">
          <div class="card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            <span>Check for Updates</span>
          </div>

          <div class="updates-check-area">
            <div class="updates-check-content">
              <div id="updates-idle-msg">
                <p style="color: var(--text-secondary); font-size: 13px; margin: 0;">
                  Click the button to check for new versions from the release server.
                </p>
              </div>

              <div id="updates-status-box" class="updates-status-box" style="display: none;">
                <div id="updates-status-icon" class="updates-status-icon"></div>
                <div>
                  <div id="updates-status-title" style="font-weight: 600; font-size: 14px;"></div>
                  <div id="updates-status-detail" style="font-size: 12px; color: var(--text-muted); margin-top: 2px;"></div>
                </div>
              </div>

              <div id="updates-progress-area" style="display: none; margin-top: 16px;">
                <div class="updates-progress-track">
                  <div id="updates-progress-fill" class="updates-progress-fill"></div>
                </div>
                <div id="updates-progress-text" style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">Downloading...</div>
              </div>
            </div>

            <div class="updates-check-actions">
              <button class="btn btn-primary" id="btn-check-updates">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="23 4 23 10 17 10"/>
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                </svg>
                <span>Check for Updates</span>
              </button>
              <button class="btn btn-primary" id="btn-install-update" style="display: none;">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                <span>Download & Install</span>
              </button>
              <button class="btn btn-primary" id="btn-restart-app" style="display: none;">
                <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="23 4 23 10 17 10"/>
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                </svg>
                <span>Restart to Apply</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Preferences Card -->
        <div class="card-section">
          <div class="card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-amber)" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            <span>Update Preferences</span>
          </div>

          <div class="toggle-wrapper">
            <div>
              <div style="font-weight: 600; font-size: 13px;">Auto-Update</div>
              <div style="font-size: 11px; color: var(--text-muted);">Automatically download and install updates when available</div>
            </div>
            <label class="switch">
              <input type="checkbox" id="setting-auto-update">
              <span class="slider"></span>
            </label>
          </div>

          <div class="toggle-wrapper">
            <div>
              <div style="font-weight: 600; font-size: 13px;">Check on Startup</div>
              <div style="font-size: 11px; color: var(--text-muted);">Check for updates every time the app launches</div>
            </div>
            <label class="switch">
              <input type="checkbox" id="setting-check-on-startup" checked>
              <span class="slider"></span>
            </label>
          </div>
        </div>
      </div>
    `;
  },

  async init() {
    // Wire button handlers
    const bind = (id, handler) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('click', handler);
    };

    bind('btn-check-updates', () => this.checkForUpdates());
    bind('btn-install-update', () => this.installUpdate());
    bind('btn-restart-app', () => this.restartApp());

    // Load version dynamically
    this.loadVersion();

    // Load auto-update preference from env
    this.loadPreferences();
  },

  destroy() {},

  async loadVersion() {
    try {
      if (window.__TAURI__ && window.__TAURI__.app) {
        const version = await window.__TAURI__.app.getVersion();
        const el = document.getElementById('updates-current-version');
        if (el) el.textContent = `v${version}`;
      }
      // Detect platform
      const platformEl = document.getElementById('updates-platform');
      if (platformEl) {
        const ua = navigator.userAgent.toLowerCase();
        if (ua.includes('windows')) platformEl.textContent = 'Windows x64';
        else if (ua.includes('mac')) platformEl.textContent = 'macOS (Apple Silicon)';
        else platformEl.textContent = 'Desktop';
      }
    } catch (e) {}
  },

  async loadPreferences() {
    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        const env = await window.__TAURI__.core.invoke('read_env');
        const autoUpdateEl = document.getElementById('setting-auto-update');
        if (autoUpdateEl) {
          autoUpdateEl.checked = (env.AUTO_UPDATE || '').toLowerCase() !== 'false';
        }
      }
    } catch (e) {}
  },

  setStatus(type, title, detail) {
    const idleMsg = document.getElementById('updates-idle-msg');
    const statusBox = document.getElementById('updates-status-box');
    const statusIcon = document.getElementById('updates-status-icon');
    const statusTitle = document.getElementById('updates-status-title');
    const statusDetail = document.getElementById('updates-status-detail');

    if (idleMsg) idleMsg.style.display = 'none';
    if (statusBox) statusBox.style.display = 'flex';

    const icons = {
      checking: '<svg class="spin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>',
      available: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green, #22c55e)" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
      uptodate: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green, #22c55e)" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
      error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-red, #ef4444)" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
      downloading: '<svg class="spin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" stroke-width="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>',
      installed: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green, #22c55e)" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    };

    if (statusIcon) statusIcon.innerHTML = icons[type] || '';
    if (statusTitle) statusTitle.textContent = title;
    if (statusDetail) statusDetail.textContent = detail || '';
  },

  async checkForUpdates() {
    const btnCheck = document.getElementById('btn-check-updates');
    const btnInstall = document.getElementById('btn-install-update');
    const originalHTML = btnCheck ? btnCheck.innerHTML : '';

    if (btnCheck) {
      btnCheck.disabled = true;
      btnCheck.innerHTML = `
        <svg class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>Checking...</span>
      `;
    }

    this.setStatus('checking', 'Checking for updates...', 'Contacting release server...');

    try {
      if (!window.__TAURI__ || !window.__TAURI__.core) {
        this.setStatus('error', 'Not Available', 'Update checking is only available in the installed app.');
        return;
      }

      const result = await window.__TAURI__.core.invoke('check_for_updates');
      console.log('[Updates] Check result:', result);

      if (result.available) {
        this.setStatus('available', `Update Available — v${result.version}`, result.body || 'A new version is ready to download.');
        if (btnInstall) btnInstall.style.display = 'inline-flex';
        if (btnCheck) btnCheck.style.display = 'none';
      } else if (result.error) {
        this.setStatus('error', 'Check Failed', result.error);
      } else {
        this.setStatus('uptodate', 'You\'re up to date!', 'No new updates available. You are running the latest version.');
      }
    } catch (e) {
      console.error('[Updates] Check failed:', e);
      this.setStatus('error', 'Check Failed', `${e}`);
    } finally {
      if (btnCheck) {
        btnCheck.disabled = false;
        btnCheck.innerHTML = originalHTML;
      }
    }
  },

  async installUpdate() {
    const btnInstall = document.getElementById('btn-install-update');
    const btnRestart = document.getElementById('btn-restart-app');
    const progressArea = document.getElementById('updates-progress-area');

    if (btnInstall) {
      btnInstall.disabled = true;
      btnInstall.innerHTML = `
        <svg class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>Downloading...</span>
      `;
    }

    this.setStatus('downloading', 'Downloading Update...', 'Please wait while the update is downloaded and installed.');
    if (progressArea) progressArea.style.display = 'block';

    try {
      await window.__TAURI__.core.invoke('download_and_install_update');

      this.setStatus('installed', 'Update Installed!', 'Restart the application to apply the update.');
      if (progressArea) progressArea.style.display = 'none';
      if (btnInstall) btnInstall.style.display = 'none';
      if (btnRestart) btnRestart.style.display = 'inline-flex';

      Toast.success('Update installed! Restart to apply.');
    } catch (e) {
      console.error('[Updates] Install failed:', e);
      this.setStatus('error', 'Installation Failed', `${e}`);
      if (progressArea) progressArea.style.display = 'none';
      if (btnInstall) {
        btnInstall.disabled = false;
        btnInstall.innerHTML = `
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span>Retry Download</span>
        `;
      }
      Toast.error(`Update failed: ${e}`);
    }
  },

  async restartApp() {
    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        await window.__TAURI__.core.invoke('plugin:process|restart');
      }
    } catch (e) {
      Toast.error(`Restart failed: ${e}`);
    }
  }
};
