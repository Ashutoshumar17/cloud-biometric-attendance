/**
 * Dashboard Module  
 * Displays attendance statistics, records, and reports.
 */

let currentSessionId = null;

document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    
    const sessionFilter = document.getElementById('sessionFilter');
    const dateFilter = document.getElementById('dateFilter');
    const btnExport = document.getElementById('btnExport');
    
    if (sessionFilter) sessionFilter.addEventListener('change', onSessionChange);
    if (dateFilter) dateFilter.addEventListener('change', applyFilters);
    if (btnExport) btnExport.addEventListener('click', exportCSV);
    
    // Auto-refresh every 30 seconds
    setInterval(loadDashboard, 30000);
});

async function loadDashboard() {
    try {
        // Fetch dashboard summary
        const summaryResponse = await fetch(`${CONFIG.API_BASE_URL}/dashboard/summary`);
        if (summaryResponse.ok) {
            const summary = await summaryResponse.json();
            
            // Build stat card data from summary
            const activeSession = summary.active_session;
            const total = summary.total_students || 0;
            const present = activeSession ? (activeSession.present || 0) : 0;
            updateStatCards({
                total_students: total,
                present: present,
                absent: Math.max(0, total - present),
                percentage: total > 0 ? ((present / total) * 100).toFixed(1) : 0
            });

            if (summary.recent_recognitions && summary.recent_recognitions.length > 0) {
                updateRecentActivity(summary.recent_recognitions);
            }
        }

        // Populate session dropdown from sessions list
        const sessionsResponse = await fetch(`${CONFIG.API_BASE_URL}/attendance/sessions`);
        if (sessionsResponse.ok) {
            const sessionsJson = await sessionsResponse.json();
            const sessions = sessionsJson.data || [];
            populateSessionDropdown(sessions);
        }
        
        // Fetch records based on current filters
        await applyFilters();
        
    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

async function onSessionChange(e) {
    currentSessionId = e.target.value;
    if (currentSessionId) {
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/dashboard/session/${currentSessionId}`);
            if (response.ok) {
                const sessionData = await response.json();
                const stats = sessionData.stats || {};
                updateStatCards({
                    total_students: stats.total_students || 0,
                    present: stats.present || 0,
                    absent: stats.absent || 0,
                    percentage: stats.attendance_percentage || 0
                });
            }
        } catch (error) {
            console.error('Failed to load session details:', error);
        }
        await applyFilters();
    } else {
        await loadDashboard();
    }
}

async function applyFilters() {
    try {
        const sessionFilter = currentSessionId;
        const dateFilter = document.getElementById('dateFilter')?.value;
        
        let url = `${CONFIG.API_BASE_URL}/attendance?`;
        const params = new URLSearchParams();
        if (sessionFilter) params.append('session_id', sessionFilter);
        if (dateFilter) params.append('date', dateFilter);
        
        const response = await fetch(url + params.toString());
        if (response.ok) {
            const json = await response.json();
            const records = json.data || json;
            const recordList = Array.isArray(records) ? records : [];
            
            updateAttendanceTable(recordList);
            
            // If recent activity wasn't loaded from summary, fall back to records
            const feed = document.getElementById('activityFeed');
            if (feed && feed.children.length <= 1 && recordList.length > 0) {
                updateRecentActivity(recordList.slice(0, 10));
            }
        }
    } catch (error) {
        console.error('Failed to apply filters:', error);
    }
}

function updateStatCards(data) {
    const totalStudents = document.getElementById('statTotalStudents');
    const presentCount = document.getElementById('statPresent');
    const absentCount = document.getElementById('statAbsent');
    const attendancePercent = document.getElementById('statPercentage');
    
    if (totalStudents) totalStudents.textContent = data.total_students ?? 0;
    if (presentCount) presentCount.textContent = data.present ?? 0;
    if (absentCount) absentCount.textContent = data.absent ?? 0;
    if (attendancePercent) attendancePercent.textContent = `${data.percentage ?? 0}%`;
}

function updateAttendanceTable(records) {
    const tbody = document.querySelector('#dashboardTable tbody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!records || records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center" style="text-align: center; padding: 1.5rem; color: var(--text-muted);">No records found</td></tr>';
        return;
    }
    
    records.forEach((record, index) => {
        const tr = document.createElement('tr');
        
        tr.innerHTML = `
            <td>${index + 1}</td>
            <td><strong>${record.student_id || '-'}</strong></td>
            <td>${record.name || record.student_name || '-'}</td>
            <td>${record.department || 'ECE'}</td>
            <td>${record.time || formatTime(record.created_at || record.timestamp)}</td>
            <td><span class="badge badge-success">Present</span></td>
            <td>${formatConfidence(record.confidence)}</td>
        `;
        
        tbody.appendChild(tr);
    });
}

function updateRecentActivity(events) {
    const feed = document.getElementById('activityFeed');
    if (!feed) return;
    
    feed.innerHTML = '';
    
    if (!events || events.length === 0) {
        feed.innerHTML = '<p style="color: var(--text-muted); font-size: 0.875rem;">No recent activity.</p>';
        return;
    }
    
    events.forEach(event => {
        const div = document.createElement('div');
        div.style.display = 'flex';
        div.style.alignItems = 'center';
        div.style.gap = '0.75rem';
        div.style.padding = '0.5rem 0';
        div.style.borderBottom = '1px solid var(--border, #e2e8f0)';
        
        const name = event.name || event.student_name || event.student_id || 'Student';
        const time = event.time || formatTime(event.timestamp || event.created_at);
        
        div.innerHTML = `
            <div style="width: 2rem; height: 2rem; border-radius: 50%; background: #dcfce7; color: #16a34a; display: flex; align-items: center; justify-content: center; font-weight: bold; flex-shrink: 0;">✓</div>
            <div style="flex: 1; min-width: 0;">
                <div style="font-weight: 500; font-size: 0.875rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${name} marked present</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">${time}</div>
            </div>
        `;
        feed.appendChild(div);
    });
}

async function exportCSV() {
    try {
        let url = `${CONFIG.API_BASE_URL}/attendance/export/csv`;
        if (currentSessionId) {
            url += `?session_id=${currentSessionId}`;
        }
        window.open(url, '_blank');
    } catch (error) {
        console.error('Failed to export CSV:', error);
    }
}

function populateSessionDropdown(sessions) {
    const select = document.getElementById('sessionFilter');
    if (!select) return;
    
    const currentVal = select.value;
    
    while (select.options.length > 1) {
        select.remove(1);
    }
    
    if (sessions && sessions.length > 0) {
        sessions.forEach(session => {
            const option = document.createElement('option');
            option.value = session.session_id;
            option.textContent = `${session.course} (${session.date})`;
            select.appendChild(option);
        });
    }
    
    if (currentVal && Array.from(select.options).some(opt => opt.value === currentVal)) {
        select.value = currentVal;
    }
}

function formatTime(timeString) {
    if (!timeString) return '-';
    try {
        const d = new Date(timeString);
        if (isNaN(d.getTime())) return timeString;
        return d.toLocaleTimeString();
    } catch (e) {
        return timeString;
    }
}

function formatConfidence(confidence) {
    if (confidence === undefined || confidence === null) return '-';
    const val = parseFloat(confidence);
    if (isNaN(val)) return '-';
    
    const pct = val > 1 ? val.toFixed(1) : (val * 100).toFixed(1);
    let color = '#10b981';
    if (val < 0.6) color = '#ef4444';
    else if (val < 0.8) color = '#f59e0b';
    
    return `<span style="color: ${color}; font-weight: 600;">${pct}%</span>`;
}
