/**
 * Profiles Management Page
 */
const ProfilesPage = {
  render() {
    return `
      <div class="card-section">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <div class="card-title" style="margin-bottom: 0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-purple)" stroke-width="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
            </svg>
            <span>Managed Chrome Profiles</span>
          </div>
          <button class="btn btn-ghost" onclick="ProfilesPage.fetchProfiles()">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"/>
              <polyline points="1 20 1 14 7 14"/>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
            </svg>
            <span>Refresh</span>
          </button>
        </div>

        <div class="table-wrapper">
          <table class="custom-table">
            <thead>
              <tr>
                <th>Profile Directory</th>
                <th>Google Account</th>
                <th>Status</th>
                <th>CDP Port</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="profiles-table-body">
              <tr>
                <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">
                  Loading profiles from Python node...
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  },

  async init() {
    await this.fetchProfiles();
  },

  destroy() {},

  async fetchProfiles() {
    const tbody = document.getElementById('profiles-table-body');
    if (!tbody) return;

    try {
      const res = await fetch(App.apiUrl('/api/profiles'));
      if (res.ok) {
        const json = await res.json();
        const profiles = json.data || [];

        if (profiles.length === 0) {
          tbody.innerHTML = `
            <tr>
              <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">
                No profiles created yet. Profiles are synced automatically when campaign jobs run.
              </td>
            </tr>
          `;
          return;
        }

        tbody.innerHTML = profiles.map(p => {
          const profilePath = p.profile_path || p.path || p.name;
          const isRunning = !!p.is_running;
          const port = p.port || p.debug_port || '—';
          const hasAccount = p.has_google_account || !!p.google_account;

          return `
            <tr>
              <td style="font-weight: 600;">${p.name}</td>
              <td>${hasAccount ? '<span class="badge badge-success">Logged In</span>' : '<span class="badge badge-secondary">Manual Profile</span>'}</td>
              <td>${isRunning ? '<span class="badge badge-success">Active / Open</span>' : '<span class="badge badge-secondary">Idle</span>'}</td>
              <td style="font-family: var(--font-mono); color: var(--text-muted);">${port}</td>
              <td>
                ${isRunning ? `
                  <button class="btn btn-danger" style="padding: 4px 10px; font-size: 11px;" onclick="ProfilesPage.closeBrowser('${p.name}')">Close</button>
                ` : `
                  <button class="btn btn-ghost" style="padding: 4px 10px; font-size: 11px;" onclick="ProfilesPage.openBrowser('${profilePath}')">Launch</button>
                `}
              </td>
            </tr>
          `;
        }).join('');
      } else {
        tbody.innerHTML = `
          <tr>
            <td colspan="5" style="text-align: center; color: var(--accent-amber); padding: 24px;">
              Python engine is initializing or offline.
            </td>
          </tr>
        `;
      }
    } catch (e) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">
            Unable to connect to local API on port ${App.port}.
          </td>
        </tr>
      `;
    }
  },

  async openBrowser(profilePath) {
    Toast.info(`Launching Chrome for ${profilePath}...`);
    try {
      const res = await fetch(App.apiUrl('/api/profiles/launch'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_path: profilePath, url: 'https://www.youtube.com' })
      });
      if (res.ok) {
        Toast.success(`Launched ${profilePath}`);
        setTimeout(() => this.fetchProfiles(), 1500);
      } else {
        const err = await res.json();
        Toast.error(`Launch failed: ${err.detail || 'Unknown error'}`);
      }
    } catch (e) {
      Toast.error(`Failed to launch browser: ${e}`);
    }
  },

  async closeBrowser(profileName) {
    Toast.info(`Closing Chrome for ${profileName}...`);
    try {
      const res = await fetch(App.apiUrl('/api/profiles/close'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_name: profileName })
      });
      if (res.ok) {
        Toast.success(`Closed ${profileName}`);
        setTimeout(() => this.fetchProfiles(), 1000);
      } else {
        const err = await res.json();
        Toast.error(`Close failed: ${err.detail || 'Unknown error'}`);
      }
    } catch (e) {
      Toast.error(`Failed to close browser: ${e}`);
    }
  }
};
