/**
 * Settings Page (.env Editor)
 * All button handlers use addEventListener (no inline onclick) for CSP compatibility.
 */
const SettingsPage = {
  currentEnv: {},

  render() {
    return `
      <div class="settings-grid">
        <!-- Section 1: Server Connection -->
        <div class="card-section">
          <div class="card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-purple)" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="2" y1="12" x2="22" y2="12"/>
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
            <span>Laravel Server Connection</span>
          </div>

          <div class="form-group">
            <label class="form-label">Laravel API URL</label>
            <input type="text" class="form-input" id="setting-laravel-url" placeholder="https://your-domain.com/api">
          </div>

          <div class="form-group">
            <label class="form-label">API Token (Optional)</label>
            <div class="input-wrapper">
              <input type="password" class="form-input" id="setting-laravel-token" placeholder="Bearer Token">
              <button class="input-btn" id="btn-toggle-laravel-token">👁</button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">SaaS Device Key</label>
            <input type="text" class="form-input" id="setting-device-key" placeholder="dev_key_...">
          </div>

          <button class="btn btn-ghost" style="width: 100%; justify-content: center;" id="btn-test-connection">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <span>Test Laravel Connection</span>
          </button>
        </div>

        <!-- Section 2: Ngrok Public Tunnel -->
        <div class="card-section">
          <div class="card-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" stroke-width="2">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
            <span>Ngrok Tunnel Settings</span>
          </div>

          <div class="form-group">
            <label class="form-label">Ngrok Auth Token</label>
            <div class="input-wrapper">
              <input type="password" class="form-input" id="setting-ngrok-token" placeholder="Paste from dashboard.ngrok.com">
              <button class="input-btn" id="btn-toggle-ngrok-token">👁</button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Static Ngrok Domain</label>
            <input type="text" class="form-input" id="setting-ngrok-domain" placeholder="https://your-domain.ngrok-free.dev">
          </div>

          <!-- Section 3: Engine Config -->
          <div class="card-title" style="margin-top: 24px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-amber)" stroke-width="2">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
              <line x1="6" y1="6" x2="6.01" y2="6"/>
              <line x1="6" y1="18" x2="6.01" y2="18"/>
            </svg>
            <span>Engine & Hardware Settings</span>
          </div>

          <div class="form-group">
            <label class="form-label">Local Port</label>
            <input type="number" class="form-input" id="setting-port" value="8000">
          </div>

          <div class="toggle-wrapper">
            <div>
              <div style="font-weight: 600; font-size: 13px;">Debug Mode</div>
              <div style="font-size: 11px; color: var(--text-muted);">Enable detailed verbose logging</div>
            </div>
            <label class="switch">
              <input type="checkbox" id="setting-debug">
              <span class="slider"></span>
            </label>
          </div>

          <div class="toggle-wrapper">
            <div>
              <div style="font-weight: 600; font-size: 13px;">Auto-Start on Boot</div>
              <div style="font-size: 11px; color: var(--text-muted);">Launch silently when PC turns on</div>
            </div>
            <label class="switch">
              <input type="checkbox" id="setting-autostart">
              <span class="slider"></span>
            </label>
          </div>
        </div>
      </div>

      <!-- Section 4: Software Updates -->
      <div class="card-section">
        <div class="card-title">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-green, #22c55e)" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span>Software Updates</span>
        </div>

        <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.06);">
          <div>
            <div style="font-weight: 600; font-size: 13px;">Current Version</div>
            <div style="font-size: 12px; color: var(--text-muted);" id="update-current-version">v1.1.0</div>
          </div>
          <button class="btn btn-ghost" id="btn-check-updates">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
            </svg>
            <span>Check for Updates</span>
          </button>
        </div>

        <div id="update-status" style="display: none; padding: 12px; margin-top: 8px; border-radius: 8px; background: rgba(34,197,94,0.08); border: 1px solid rgba(34,197,94,0.2);">
          <div id="update-status-text" style="font-size: 13px; font-weight: 500;"></div>
          <div id="update-progress-wrap" style="display: none; margin-top: 8px;">
            <div style="background: rgba(255,255,255,0.08); border-radius: 4px; height: 6px; overflow: hidden;">
              <div id="update-progress-bar" style="width: 0%; height: 100%; background: var(--accent-green, #22c55e); border-radius: 4px; transition: width 0.3s ease;"></div>
            </div>
          </div>
          <div id="update-actions" style="display: none; margin-top: 10px;">
            <button class="btn btn-primary" id="btn-install-update">
              <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              <span>Download & Install</span>
            </button>
          </div>
        </div>

        <div class="toggle-wrapper" style="margin-top: 8px;">
          <div>
            <div style="font-weight: 600; font-size: 13px;">Auto-Update</div>
            <div style="font-size: 11px; color: var(--text-muted);">Automatically download and install updates</div>
          </div>
          <label class="switch">
            <input type="checkbox" id="setting-auto-update">
            <span class="slider"></span>
          </label>
        </div>
      </div>

      <!-- Action Bar -->
      <div style="display: flex; justify-content: flex-end; gap: 14px; margin-top: 10px;">
        <button class="btn btn-ghost" id="btn-reset-defaults">
          <span>Reset Defaults</span>
        </button>
        <button class="btn btn-primary" id="btn-save-settings">
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          <span>Save & Apply Settings</span>
        </button>
      </div>
    `;
  },

  async init() {
    // Wire up ALL button handlers via addEventListener (CSP-safe)
    const bind = (id, handler) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('click', handler);
    };

    bind('btn-toggle-laravel-token', () => this.togglePassword('setting-laravel-token'));
    bind('btn-toggle-ngrok-token', () => this.togglePassword('setting-ngrok-token'));
    bind('btn-test-connection', () => this.testConnection());
    bind('btn-check-updates', () => this.checkForUpdates());
    bind('btn-install-update', () => this.installUpdate());
    bind('btn-reset-defaults', () => this.resetDefaults());
    bind('btn-save-settings', () => this.saveSettings());

    await this.loadEnv();
  },

  destroy() {},

  togglePassword(id) {
    const input = document.getElementById(id);
    if (input) {
      input.type = input.type === 'password' ? 'text' : 'password';
    }
  },

  async loadEnv() {
    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        this.currentEnv = (await window.__TAURI__.core.invoke('read_env')) || {};
      } else {
        // Fallback for browser preview
        this.currentEnv = this.currentEnv && Object.keys(this.currentEnv).length > 0 ? this.currentEnv : {
          LARAVEL_API_URL: 'http://youtube.test/api',
          LARAVEL_API_TOKEN: '',
          SAAS_DEVICE_KEY: '',
          NGROK_AUTHTOKEN: '',
          NGROK_DOMAIN: '',
          PORT: '8008',
          DEBUG: 'True'
        };
      }

      console.log('[SettingsPage] Loaded env:', this.currentEnv);

      const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = val || '';
      };

      setVal('setting-laravel-url', this.currentEnv.LARAVEL_API_URL);
      setVal('setting-laravel-token', this.currentEnv.LARAVEL_API_TOKEN);
      setVal('setting-device-key', this.currentEnv.SAAS_DEVICE_KEY);
      setVal('setting-ngrok-token', this.currentEnv.NGROK_AUTHTOKEN);
      setVal('setting-ngrok-domain', this.currentEnv.NGROK_DOMAIN);
      setVal('setting-port', this.currentEnv.PORT || '8008');

      const debugEl = document.getElementById('setting-debug');
      if (debugEl) {
        debugEl.checked = (this.currentEnv.DEBUG || '').toLowerCase() === 'true';
      }

      const autoUpdateEl = document.getElementById('setting-auto-update');
      if (autoUpdateEl) {
        autoUpdateEl.checked = (this.currentEnv.AUTO_UPDATE || '').toLowerCase() !== 'false';
      }
    } catch (e) {
      console.error('[SettingsPage] Failed to load .env:', e);
      Toast.error(`Failed to load .env settings: ${e}`);
    }
  },

  async saveSettings() {
    const btn = document.getElementById('btn-save-settings');
    const originalBtnHTML = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <svg class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>Saving...</span>
      `;
    }

    try {
      const laravelUrl = document.getElementById('setting-laravel-url')?.value.trim() || '';
      const laravelToken = document.getElementById('setting-laravel-token')?.value.trim() || '';
      const deviceKey = document.getElementById('setting-device-key')?.value.trim() || '';
      const ngrokToken = document.getElementById('setting-ngrok-token')?.value.trim() || '';
      const ngrokDomain = document.getElementById('setting-ngrok-domain')?.value.trim() || '';
      const port = document.getElementById('setting-port')?.value.trim() || '8008';
      const debug = document.getElementById('setting-debug')?.checked ? 'True' : 'False';
      const autoUpdate = document.getElementById('setting-auto-update')?.checked ? 'True' : 'False';

      const updated = {
        ...(this.currentEnv || {}),
        LARAVEL_API_URL: laravelUrl,
        LARAVEL_API_TOKEN: laravelToken,
        SAAS_DEVICE_KEY: deviceKey,
        NGROK_AUTHTOKEN: ngrokToken,
        NGROK_DOMAIN: ngrokDomain,
        PORT: port,
        DEBUG: debug,
        AUTO_UPDATE: autoUpdate,
      };

      console.log('[SettingsPage] Saving settings:', updated);

      if (window.__TAURI__ && window.__TAURI__.core) {
        await window.__TAURI__.core.invoke('write_env', { settings: updated });
        App.port = parseInt(updated.PORT, 10) || 8008;
        this.currentEnv = updated;
        Toast.success('Settings saved successfully!');
      } else {
        this.currentEnv = updated;
        Toast.success('Settings saved (Preview Mode)');
      }
    } catch (e) {
      console.error('[SettingsPage] Save failed:', e);
      Toast.error(`Failed to save settings: ${e}`);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalBtnHTML;
      }
    }
  },

  async testConnection() {
    const btn = document.getElementById('btn-test-connection');
    const originalHTML = btn ? btn.innerHTML : '';
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <svg class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>Testing...</span>
      `;
    }

    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        const res = await window.__TAURI__.core.invoke('test_connection');
        if (res.success) {
          Toast.success(res.message || 'Connection successful!');
        } else {
          Toast.error(`Connection failed: ${res.error || 'HTTP ' + res.status_code}`);
        }
      } else {
        Toast.success('Laravel API reachability verified (Preview)!');
      }
    } catch (e) {
      Toast.error(`Connection test failed: ${e}`);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
      }
    }
  },

  resetDefaults() {
    document.getElementById('setting-laravel-url').value = 'http://youtube.test/api';
    document.getElementById('setting-port').value = '8000';
    document.getElementById('setting-debug').checked = true;
    Toast.info('Reset form to default values.');
  },

  async checkForUpdates() {
    const btn = document.getElementById('btn-check-updates');
    const statusDiv = document.getElementById('update-status');
    const statusText = document.getElementById('update-status-text');
    const actionsDiv = document.getElementById('update-actions');
    const originalHTML = btn ? btn.innerHTML : '';

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <svg class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>Checking...</span>
      `;
    }

    try {
      if (!window.__TAURI__ || !window.__TAURI__.core) {
        statusDiv.style.display = 'block';
        statusText.textContent = 'Update check is only available in the installed app.';
        actionsDiv.style.display = 'none';
        return;
      }

      const result = await window.__TAURI__.core.invoke('check_for_updates');
      console.log('[Updates] Check result:', result);

      statusDiv.style.display = 'block';

      if (result.available) {
        statusDiv.style.background = 'rgba(34,197,94,0.08)';
        statusDiv.style.borderColor = 'rgba(34,197,94,0.2)';
        statusText.innerHTML = `<strong>Update Available!</strong> Version ${result.version} is ready to download.`;
        if (result.body) {
          statusText.innerHTML += `<div style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">${result.body}</div>`;
        }
        actionsDiv.style.display = 'flex';
      } else {
        statusDiv.style.background = 'rgba(99,102,241,0.08)';
        statusDiv.style.borderColor = 'rgba(99,102,241,0.2)';
        statusText.textContent = result.error ? `Update check failed: ${result.error}` : '\u2713 You are running the latest version!';
        actionsDiv.style.display = 'none';
      }
    } catch (e) {
      console.error('[Updates] Check failed:', e);
      if (statusDiv) {
        statusDiv.style.display = 'block';
        statusDiv.style.background = 'rgba(239,68,68,0.08)';
        statusDiv.style.borderColor = 'rgba(239,68,68,0.2)';
        statusText.textContent = `Update check error: ${e}`;
        actionsDiv.style.display = 'none';
      }
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
      }
    }
  },

  async installUpdate() {
    const btn = document.getElementById('btn-install-update');
    const statusText = document.getElementById('update-status-text');
    const progressWrap = document.getElementById('update-progress-wrap');
    const originalHTML = btn ? btn.innerHTML : '';

    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `
        <svg class="btn-icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        <span>Downloading...</span>
      `;
    }

    if (statusText) statusText.textContent = 'Downloading update...';
    if (progressWrap) progressWrap.style.display = 'block';

    try {
      const result = await window.__TAURI__.core.invoke('download_and_install_update');
      if (statusText) statusText.innerHTML = '<strong>\u2713 Update installed!</strong> Restart the app to apply the update.';
      if (btn) {
        btn.innerHTML = `
          <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          <span>Restart Now</span>
        `;
        btn.disabled = false;
        btn.addEventListener('click', async () => {
          if (window.__TAURI__ && window.__TAURI__.core) {
            await window.__TAURI__.core.invoke('plugin:process|restart');
          }
        });
      }
      if (progressWrap) progressWrap.style.display = 'none';
      Toast.success('Update downloaded and installed! Restart to apply.');
    } catch (e) {
      console.error('[Updates] Install failed:', e);
      Toast.error(`Update failed: ${e}`);
      if (statusText) statusText.textContent = `Update failed: ${e}`;
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalHTML;
      }
    }
  }
};
