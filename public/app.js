const api = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};

const state = {
  teams: [],
  users: [],
  items: [],
};

const teamForm = document.getElementById('team-form');
const userForm = document.getElementById('user-form');
const quickForm = document.getElementById('quick-form');

const teamName = document.getElementById('team-name');
const userTeam = document.getElementById('user-team');
const userName = document.getElementById('user-name');
const userEmail = document.getElementById('user-email');
const userRole = document.getElementById('user-role');

const quickTeam = document.getElementById('quick-team');
const quickUser = document.getElementById('quick-user');
const shiftName = document.getElementById('shift-name');
const reportSummary = document.getElementById('report-summary');
const itemTitle = document.getElementById('item-title');
const itemPriority = document.getElementById('item-priority');

const teamsList = document.getElementById('teams-list');
const usersList = document.getElementById('users-list');
const itemsList = document.getElementById('items-list');
const stats = document.getElementById('stats');
const statsEmpty = document.getElementById('stats-empty');
const statOpen = document.getElementById('stat-open');
const statOverdue = document.getElementById('stat-overdue');
const statCritical = document.getElementById('stat-critical');
const toast = document.getElementById('toast');

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 1800);
}

function renderSelectOptions() {
  const teamOptions = state.teams.map((t) => `<option value="${t.id}">${t.name}</option>`).join('');
  userTeam.innerHTML = `<option value="">Select team</option>${teamOptions}`;
  quickTeam.innerHTML = `<option value="">Select team</option>${teamOptions}`;

  const userOptions = state.users.map((u) => `<option value="${u.id}">${u.full_name} (${u.role})</option>`).join('');
  quickUser.innerHTML = `<option value="">Select user</option>${userOptions}`;
}

function renderLists() {
  teamsList.innerHTML = state.teams.map((t) => `<li>${t.name}</li>`).join('') || '<li>No teams</li>';
  usersList.innerHTML =
    state.users.map((u) => `<li>${u.full_name} - ${u.role} (${u.email})</li>`).join('') || '<li>No users</li>';
  itemsList.innerHTML =
    state.items
      .map(
        (i) => `<li><strong>${i.title}</strong> | priority=${i.priority} | status=${i.status} | due=${i.due_at || 'n/a'}</li>`
      )
      .join('') || '<li>No handover items</li>';
}

async function refreshTeamsUsers() {
  state.teams = await api.get('/api/teams');
  state.users = await api.get('/api/users');
  renderSelectOptions();
  renderLists();
}

async function refreshItemsAndStats(teamId) {
  state.items = teamId ? await api.get(`/api/handover-items?teamId=${teamId}`) : [];
  renderLists();

  if (!teamId) {
    stats.classList.add('hidden');
    statsEmpty.classList.remove('hidden');
    return;
  }

  const d = await api.get(`/api/dashboard?teamId=${teamId}`);
  statOpen.textContent = d.open_items;
  statOverdue.textContent = d.overdue_items;
  statCritical.textContent = d.critical_open_items;
  statsEmpty.classList.add('hidden');
  stats.classList.remove('hidden');
}

teamForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  await api.post('/api/teams', { name: teamName.value.trim() });
  teamName.value = '';
  await refreshTeamsUsers();
  showToast('Team created');
});

userForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  await api.post('/api/users', {
    team_id: userTeam.value,
    full_name: userName.value.trim(),
    email: userEmail.value.trim(),
    role: userRole.value,
  });
  userName.value = '';
  userEmail.value = '';
  await refreshTeamsUsers();
  await refreshItemsAndStats(quickTeam.value || state.teams[0]?.id);
  showToast('User created');
});

quickForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const now = new Date();
  const end = new Date(now.getTime() + 8 * 60 * 60 * 1000);

  const shift = await api.post('/api/shifts', {
    team_id: quickTeam.value,
    shift_name: shiftName.value,
    starts_at: now.toISOString(),
    ends_at: end.toISOString(),
    created_by: quickUser.value,
  });

  const report = await api.post('/api/shift-reports', {
    team_id: quickTeam.value,
    shift_id: shift.id,
    author_id: quickUser.value,
    summary: reportSummary.value,
    incidents: null,
    blockers: null,
    metrics: { created_from: 'mvp_ui' },
    status: 'submitted',
  });

  await api.post(`/api/shift-reports/${report.id}/handover-items`, {
    team_id: quickTeam.value,
    title: itemTitle.value,
    details: 'Created from quick flow',
    priority: itemPriority.value,
    created_by: quickUser.value,
  });

  shiftName.value = '';
  reportSummary.value = '';
  itemTitle.value = '';

  await refreshItemsAndStats(quickTeam.value);
  showToast('Shift, report, and handover item created');
});

quickTeam.addEventListener('change', async () => {
  await refreshItemsAndStats(quickTeam.value);
});

(async function init() {
  try {
    await refreshTeamsUsers();
    if (state.teams[0]) {
      quickTeam.value = state.teams[0].id;
      await refreshItemsAndStats(state.teams[0].id);
    }
  } catch (err) {
    showToast(`Init error: ${err.message}`);
    console.error(err);
  }
})();
