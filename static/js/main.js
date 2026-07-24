let refreshInterval = null;
let latestTunnels = {};
let lastTrafficIn = null;
let lastTrafficOut = null;
let lastTimestamp = null;

let trafficHistory = [];
let prevTrafficHistory = [];
let lastPushTime = Date.now();
let targetMaxVal = 1024;
let currentMaxVal = 1024;
let animFrameId = null;
const VISIBLE_COUNT = 25;

function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatSpeed(bytesPerSec) {
    if (!bytesPerSec || bytesPerSec <= 0) return '0 B/s';
    if (bytesPerSec < 1024) return bytesPerSec.toFixed(0) + ' B/s';
    if (bytesPerSec < 1024 * 1024) return (bytesPerSec / 1024).toFixed(1) + ' KB/s';
    return (bytesPerSec / (1024 * 1024)).toFixed(2) + ' MB/s';
}

function pushTrafficHistory(speedDown, speedUp) {
    const now = Date.now();
    const nowStr = new Date(now).toLocaleTimeString('zh-CN', { hour12: false });
    
    trafficHistory.push({
        time: nowStr,
        down: speedDown || 0,
        up: speedUp || 0
    });

    if (trafficHistory.length > VISIBLE_COUNT + 5) {
        trafficHistory.shift();
    }

    lastPushTime = now;
    startChartAnimLoop();
}

function startChartAnimLoop() {
    if (!animFrameId) {
        function loop() {
            renderTrafficChartFrame();
            animFrameId = requestAnimationFrame(loop);
        }
        animFrameId = requestAnimationFrame(loop);
    }
}

function renderTrafficChartFrame() {
    const canvas = document.getElementById('trafficChartCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    ctx.clearRect(0, 0, width, height);

    if (trafficHistory.length === 0) return;

    const paddingLeft = 52;
    const paddingBottom = 22;
    const paddingTop = 12;
    const paddingRight = 12;

    const chartW = width - paddingLeft - paddingRight;
    const chartH = height - paddingTop - paddingBottom;

    // 1. 计算 60fps 连续亚像素向左滑动偏移量 (Sub-pixel continuous horizontal shift)
    const now = Date.now();
    const progress = Math.min(1.0, Math.max(0.0, (now - lastPushTime) / 1000.0));
    const stepX = chartW / (VISIBLE_COUNT - 1);
    const xShift = progress * stepX; // 在 1s 内从 0.0px 无缝滑向 stepX px

    // 2. 保持历史点位 Y 轴绝对刚性稳定，彻底消除曲线在平移过程中的垂直蠕动变形
    const currentPoints = trafficHistory;

    // 3. 柔和缓动 Y 轴最大刻度
    let rawMax = 1024;
    currentPoints.forEach(p => {
        if (p.down > rawMax) rawMax = p.down;
        if (p.up > rawMax) rawMax = p.up;
    });
    targetMaxVal = rawMax * 1.15;
    currentMaxVal += (targetMaxVal - currentMaxVal) * 0.05;
    const maxVal = currentMaxVal;

    // 4. 绘制背景网格线与 Y 轴刻度
    ctx.strokeStyle = 'rgba(200, 200, 205, 0.35)';
    ctx.lineWidth = 1;
    ctx.font = '10px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.fillStyle = '#8e8e93';
    ctx.textAlign = 'right';

    const gridRows = 4;
    for (let i = 0; i <= gridRows; i++) {
        const y = paddingTop + (chartH / gridRows) * i;
        const val = maxVal * (1 - i / gridRows);

        ctx.beginPath();
        ctx.setLineDash([3, 3]);
        ctx.moveTo(paddingLeft, y);
        ctx.lineTo(width - paddingRight, y);
        ctx.stroke();

        ctx.fillText(formatSpeed(val), paddingLeft - 6, y + 3);
    }
    ctx.setLineDash([]);

    // 5. 裁剪曲线画板区域，确保折线平滑出界
    ctx.save();
    ctx.beginPath();
    ctx.rect(paddingLeft, 0, chartW, height);
    ctx.clip();

    // 6. 绘制向左连续亚像素平移的 Catmull-Rom 贝塞尔曲线 (右侧对齐流式生成右入左出)
    const rightX = width - paddingRight;
    const ptsLen = currentPoints.length;

    function drawSeries(key, strokeColor, gradStart, gradEnd) {
        if (ptsLen < 2) return;

        const pts = currentPoints.map((item, idx) => ({
            x: rightX - (ptsLen - 1 - idx) * stepX - xShift,
            y: paddingTop + chartH * (1 - Math.max(0, item[key]) / maxVal)
        }));

        ctx.beginPath();
        ctx.moveTo(pts[0].x, height - paddingBottom);
        ctx.lineTo(pts[0].x, pts[0].y);

        const tension = 0.25;
        for (let i = 0; i < pts.length - 1; i++) {
            const p0 = pts[Math.max(0, i - 1)];
            const p1 = pts[i];
            const p2 = pts[i + 1];
            const p3 = pts[Math.min(pts.length - 1, i + 2)];

            const cp1x = p1.x + (p2.x - p0.x) * tension;
            const cp1y = p1.y + (p2.y - p0.y) * tension;
            const cp2x = p2.x - (p3.x - p1.x) * tension;
            const cp2y = p2.y - (p3.y - p1.y) * tension;

            ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
        }

        ctx.lineTo(pts[pts.length - 1].x, height - paddingBottom);
        ctx.closePath();

        const grad = ctx.createLinearGradient(0, paddingTop, 0, height - paddingBottom);
        grad.addColorStop(0, gradStart);
        grad.addColorStop(1, gradEnd);
        ctx.fillStyle = grad;
        ctx.fill();

        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        for (let i = 0; i < pts.length - 1; i++) {
            const p0 = pts[Math.max(0, i - 1)];
            const p1 = pts[i];
            const p2 = pts[i + 1];
            const p3 = pts[Math.min(pts.length - 1, i + 2)];

            const cp1x = p1.x + (p2.x - p0.x) * tension;
            const cp1y = p1.y + (p2.y - p0.y) * tension;
            const cp2x = p2.x - (p3.x - p1.x) * tension;
            const cp2y = p2.y - (p3.y - p1.y) * tension;

            ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
        }
        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = 2.2;
        ctx.stroke();
    }

    drawSeries('up', '#34C759', 'rgba(52, 199, 89, 0.20)', 'rgba(52, 199, 89, 0.01)');
    drawSeries('down', '#007AFF', 'rgba(0, 122, 255, 0.20)', 'rgba(0, 122, 255, 0.01)');

    ctx.restore();

    // 7. 绘制向左平滑滚动的 X 轴时间刻度（右对齐安全渲染）
    ctx.textAlign = 'center';
    const labelInterval = 6;
    currentPoints.forEach((item, idx) => {
        if (idx % labelInterval === 0) {
            const x = rightX - (ptsLen - 1 - idx) * stepX - xShift;
            if (x >= paddingLeft + 30 && x <= width - paddingRight - 10) {
                ctx.fillText(item.time, x, height - 4);
            }
        }
    });
}

window.addEventListener('resize', renderTrafficChartFrame);

function nav(id, btn) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.dock-btn').forEach(b => b.classList.remove('active'));
    
    const pageEl = document.getElementById('p-' + id);
    if (pageEl) {
        pageEl.classList.add('active');
    }
    
    const btnEl = btn || document.getElementById('dock-btn-' + id);
    if (btnEl) {
        btnEl.classList.add('active');
    }
    
    try {
        localStorage.setItem('frp_active_tab', id);
    } catch(e) {}
}

document.addEventListener('DOMContentLoaded', function() {
    const savedTab = localStorage.getItem('frp_active_tab') || 'dash';
    nav(savedTab);
    
    initFrpsConfigForm();
    fetchFrpsStatus();
    
    startAutoRefresh();
    refreshConfigs();
    refreshTunnels().then(() => {
        refreshProxies();
    });
});

function startAutoRefresh() {
    refreshInterval = setInterval(() => {
        refreshStatus();
        refreshLogs();
        refreshTunnels();
        fetchFrpsStatus();
    }, 1000);
}

function stopAutoRefresh() {
    if(refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

function refreshAll() {
    const btn = document.getElementById('refreshBtn');
    btn.classList.add('spinning');
    
    refreshStatus();
    refreshLogs();
    refreshConfigs();
    fetchFrpsStatus();
    refreshTunnels().then(() => {
        refreshProxies();
    });
    
    setTimeout(() => {
        btn.classList.remove('spinning');
        showToast('已刷新');
    }, 1000);
}

function refreshStatus() {
    fetch('/api/status')
        .then(r => r.json())
        .then(d => {
            const badge = document.getElementById('statusBadge');
            const btnGroup = document.getElementById('btnGroup');
            
            if(d.running) {
                badge.className = 'status-badge running';
                badge.innerHTML = '<span>🟢</span><span>运行中</span>';
                btnGroup.innerHTML = '<button type="button" onclick="controlService(\'stop\')" class="btn btn-danger" id="btnStop">停止</button><button type="button" onclick="controlService(\'restart\')" class="btn btn-secondary" id="btnRestart">重启</button>';
            } else {
                badge.className = 'status-badge stopped';
                badge.innerHTML = '<span>⚪️</span><span>已停止</span>';
                btnGroup.innerHTML = '<button type="button" onclick="controlService(\'start\')" class="btn btn-primary" id="btnStart">启动</button>';
            }
        })
        .catch(e => console.error('Refresh status error:', e));
}

function controlService(action) {
    const btnGroup = document.getElementById('btnGroup');
    if (!btnGroup) return;
    const originalContent = btnGroup.innerHTML;
    
    const actionNames = { 'start': '启动中...', 'stop': '停止中...', 'restart': '重启中...' };
    const loadingText = actionNames[action] || '处理中...';
    btnGroup.innerHTML = `<button type="button" class="btn btn-secondary" disabled><span class="btn-spinner"></span> ${loadingText}</button>`;
    
    fetch('/api/ctrl', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({ a: action })
    })
    .then(r => r.json())
    .then(d => {
        if(d.success) {
            showToast(d.message || '操作成功', 'success');
            setTimeout(() => {
                refreshStatus();
                refreshLogs();
                if (typeof refreshTunnels === 'function') refreshTunnels();
            }, 600);
        } else {
            showToast(d.error || '操作失败', 'error');
            btnGroup.innerHTML = originalContent;
        }
    })
    .catch(e => {
        console.error('Control service error:', e);
        showToast('网络开小差或服务器错误', 'error');
        btnGroup.innerHTML = originalContent;
    });
}

function refreshLogs() {
    fetch('/api/logs')
        .then(r => r.json())
        .then(d => {
            document.getElementById('logsContent').textContent = d.logs;
        })
        .catch(e => console.error('Refresh logs error:', e));
}

function refreshTunnels() {
    return fetch('/api/tunnels')
        .then(r => r.json())
        .then(d => {
            const card = document.getElementById('metricsCard');
            const statusTextEl = document.getElementById('metricStatusText');
            if(d.success) {
                latestTunnels = d.tunnels;
                if (card) card.style.display = 'block';
                if (statusTextEl) {
                    statusTextEl.innerHTML = '🟢 实时监控中';
                    statusTextEl.style.color = 'var(--apple-green)';
                }

                // 计算实时速率
                const now = Date.now();
                const currentIn = d.total_traffic_in || 0;
                const currentOut = d.total_traffic_out || 0;
                let speedDown = 0;
                let speedUp = 0;

                if (lastTimestamp && lastTimestamp < now && lastTrafficIn !== null && lastTrafficOut !== null) {
                    const durationSec = (now - lastTimestamp) / 1000;
                    if (durationSec > 0) {
                        const deltaIn = Math.max(0, currentIn - lastTrafficIn);
                        const deltaOut = Math.max(0, currentOut - lastTrafficOut);
                        speedDown = deltaIn / durationSec;
                        speedUp = deltaOut / durationSec;
                    }
                }

                lastTrafficIn = currentIn;
                lastTrafficOut = currentOut;
                lastTimestamp = now;

                pushTrafficHistory(speedDown, speedUp);

                const speedDownEl = document.getElementById('metricSpeedDown');
                const speedUpEl = document.getElementById('metricSpeedUp');
                const totalInEl = document.getElementById('metricTotalIn');
                const totalOutEl = document.getElementById('metricTotalOut');
                const connsEl = document.getElementById('metricConns');

                if (speedDownEl) speedDownEl.textContent = formatSpeed(speedDown);
                if (speedUpEl) speedUpEl.textContent = formatSpeed(speedUp);
                if (totalInEl) totalInEl.textContent = formatBytes(currentIn);
                if (totalOutEl) totalOutEl.textContent = formatBytes(currentOut);
                if (connsEl) connsEl.textContent = d.total_conns || 0;

                if (d.type_counts) {
                    if (document.getElementById('metricTcp')) document.getElementById('metricTcp').textContent = d.type_counts.tcp || 0;
                    if (document.getElementById('metricUdp')) document.getElementById('metricUdp').textContent = d.type_counts.udp || 0;
                    if (document.getElementById('metricHttp')) document.getElementById('metricHttp').textContent = d.type_counts.http || 0;
                    if (document.getElementById('metricHttps')) document.getElementById('metricHttps').textContent = d.type_counts.https || 0;
                }
                
                document.querySelectorAll('.proxy-status').forEach(el => {
                    const name = el.getAttribute('data-name');
                    if (d.tunnels[name]) {
                        const t = d.tunnels[name];
                        if (t.status === 'running') {
                            const connText = t.cur_conns > 0 ? ` 🔗 ${t.cur_conns}` : '';
                            el.innerHTML = '🟢 在线' + connText;
                            el.style.color = 'var(--apple-green)';
                            el.title = `活动连接数: ${t.cur_conns || 0} | 接收流量: ${formatBytes(t.traffic_in)} | 发送流量: ${formatBytes(t.traffic_out)}`;
                        } else {
                            el.innerHTML = '🔴 异常';
                            el.style.color = 'var(--apple-red)';
                            el.title = t.err || '代理异常';
                        }
                    } else {
                        el.innerHTML = '⚪ 离线';
                        el.style.color = 'var(--apple-text-secondary)';
                        el.title = '';
                    }
                });
            } else {
                if (card) {
                    card.style.display = 'block';
                    if (statusTextEl) {
                        statusTextEl.innerHTML = '🔴 ' + (d.error || '管理控制台未连通');
                        statusTextEl.style.color = 'var(--apple-red)';
                    }
                }
                latestTunnels = {};
            }
        })
        .catch(e => {
            console.error('Refresh tunnels error:', e);
            const card = document.getElementById('metricsCard');
            if (card) card.style.display = 'block';
            latestTunnels = {};
        });
}

function refreshProxies() {
    fetch('/api/proxies')
        .then(r => r.json())
        .then(d => {
            const list = document.getElementById('proxyList');
            if(d.proxies.length === 0) {
                list.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><div class="empty-text">暂无转发配置</div></div>';
            } else {
                list.innerHTML = d.proxies.map(function(p, i) {
                    let statusHtml = '⚪ 离线';
                    let statusColor = 'var(--apple-text-secondary)';
                    let statusTitle = '';
                    if (latestTunnels && latestTunnels[p.name]) {
                        const t = latestTunnels[p.name];
                        if (t.status === 'running') {
                            const connText = t.cur_conns > 0 ? ` 🔗 ${t.cur_conns}` : '';
                            statusHtml = '🟢 在线' + connText;
                            statusColor = 'var(--apple-green)';
                            statusTitle = `活动连接数: ${t.cur_conns || 0} | 接收流量: ${formatBytes(t.traffic_in)} | 发送流量: ${formatBytes(t.traffic_out)}`;
                        } else {
                            statusHtml = '🔴 异常';
                            statusColor = 'var(--apple-red)';
                            statusTitle = t.err || '代理异常';
                        }
                    }
                    const badgeHtml = `<span class="proxy-status" data-name="${p.name}" style="font-size:12px;color:${statusColor};margin-left:8px;font-weight:600" title="${statusTitle}">${statusHtml}</span>`;
                    return '<div class="proxy-item" id="proxy-' + i + '">' +
                        '<div class="proxy-icon">📡</div>' +
                        '<div class="proxy-info">' +
                        '<div style="display:flex;align-items:center">' +
                        '<span class="proxy-name">' + p.name + '</span>' +
                        badgeHtml +
                        '</div>' +
                        '<span class="proxy-detail">' + p.localIP + ':' + p.localPort + '<span class="arrow">→</span>' + p.remotePort + '</span>' +
                        '</div>' +
                        '<div class="proxy-type">' + p.type.toUpperCase() + '</div>' +
                        '<div class="proxy-actions">' +
                        '<button class="btn-icon" onclick="editProxy(' + i + ')">✏️</button>' +
                        '<button class="btn-icon btn-delete" onclick="deleteProxy(' + i + ')">🗑️</button>' +
                        '</div></div>';
                }).join('');
            }
        })
        .catch(e => console.error('Refresh proxies error:', e));
}

function editProxy(idx) {
    const p = proxies[idx];
    document.getElementById('proxyIndex').value = idx;
    document.getElementById('pName').value = p.name;
    document.getElementById('pType').value = p.type;
    document.getElementById('pLocalIP').value = p.localIP;
    document.getElementById('pLocalPort').value = p.localPort;
    document.getElementById('pRemotePort').value = p.remotePort || '';
    document.getElementById('pCustomDomain').value = p.customDomain || '';
    document.getElementById('pHttpUser').value = p.httpUser || '';
    document.getElementById('pHttpPassword').value = p.httpPassword || '';
    toggleAuthFields();
    document.getElementById('modalTitle').textContent = '编辑代理';
    document.getElementById('proxyModal').classList.add('active');
}

function addProxy() {
    document.getElementById('proxyIndex').value = -1;
    document.getElementById('pName').value = '';
    document.getElementById('pType').value = 'tcp';
    document.getElementById('pLocalIP').value = '127.0.0.1';
    document.getElementById('pLocalPort').value = '';
    document.getElementById('pRemotePort').value = '';
    document.getElementById('pCustomDomain').value = '';
    document.getElementById('pHttpUser').value = '';
    document.getElementById('pHttpPassword').value = '';
    toggleAuthFields();
    document.getElementById('modalTitle').textContent = '添加代理';
    document.getElementById('proxyModal').classList.add('active');
}

function toggleAuthFields() {
    const type = document.getElementById('pType').value;
    const authDiv = document.getElementById('authFields');
    if(type === 'http' || type === 'https') {
        authDiv.style.display = 'block';
    } else {
        authDiv.style.display = 'none';
    }
}

function deleteProxy(idx) {
    if(confirm('确定要删除这个代理配置吗？')) {
        const btn = document.querySelector('#proxy-' + idx + ' .btn-delete');
        if (btn) { btn.innerHTML = '⏳'; btn.disabled = true; }
        fetch('/api/proxy/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({index: idx})
        }).then(r => r.json()).then(d => {
            if(d.success) { 
                showToast('已删除，正在刷新...'); 
                setTimeout(() => location.reload(), 500); 
            }
            else { 
                showToast(d.error, 'error'); 
                if (btn) { btn.innerHTML = '🗑️'; btn.disabled = false; }
            }
        }).catch(e => {
            showToast('服务重启中，即将刷新...', 'success');
            setTimeout(() => location.reload(), 3000);
        });
    }
}

function saveProxy(e) {
    e.preventDefault();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = '保存并重启中...';
    submitBtn.disabled = true;

    const data = {
        index: parseInt(document.getElementById('proxyIndex').value),
        name: document.getElementById('pName').value,
        type: document.getElementById('pType').value,
        localIP: document.getElementById('pLocalIP').value,
        localPort: parseInt(document.getElementById('pLocalPort').value),
        remotePort: parseInt(document.getElementById('pRemotePort').value),
        customDomain: document.getElementById('pCustomDomain').value,
        httpUser: document.getElementById('pHttpUser').value,
        httpPassword: document.getElementById('pHttpPassword').value
    };
    fetch('/api/proxy/save', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }).then(r => r.json()).then(d => {
        if(d.success) { 
            showToast('保存成功，正在刷新...'); 
            setTimeout(() => location.reload(), 500); 
        }
        else { 
            showToast(d.error, 'error'); 
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }).catch(e => {
        showToast('服务重启中，即将刷新...', 'success');
        setTimeout(() => location.reload(), 3000);
    });
}

function closeModal() { document.getElementById('proxyModal').classList.remove('active'); }

function showToast(msg, type) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast show' + (type ? ' ' + type : '');
    setTimeout(() => { t.classList.remove('show'); }, 2500);
}

document.getElementById('proxyModal').addEventListener('click', function(e) {
    if(e.target === this) closeModal();
});

function openAuthModal() {
    document.getElementById('aUser').value = '';
    document.getElementById('aPass').value = '';
    document.getElementById('aEnabled').checked = authConfig.auth_enabled;
    toggleAuthInputs();
    document.getElementById('authModal').classList.add('active');
}

function closeAuthModal() {
    document.getElementById('authModal').classList.remove('active');
}

function toggleAuthInputs() {
    const enabled = document.getElementById('aEnabled').checked;
    const uInput = document.getElementById('aUser');
    const pInput = document.getElementById('aPass');
    uInput.required = enabled;
    pInput.required = enabled;
    uInput.disabled = !enabled;
    pInput.disabled = !enabled;
    if(!enabled) {
        uInput.value = '';
        pInput.value = '';
    }
}

function saveAuth(e) {
    e.preventDefault();
    const data = {
        username: document.getElementById('aUser').value,
        password: document.getElementById('aPass').value,
        auth_enabled: document.getElementById('aEnabled').checked
    };
    fetch('/api/auth/update', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }).then(r => r.json()).then(d => {
        if(d.success) {
            showToast('设置更新成功！正在重新载入');
            closeAuthModal();
            setTimeout(() => location.reload(), 1500);
        } else {
            showToast(d.error, 'error');
        }
    });
}

document.getElementById('authModal').addEventListener('click', function(e) {
    if(e.target === this) closeAuthModal();
});

function refreshConfigs() {
    fetch('/api/configs')
        .then(r => r.json())
        .then(d => {
            const list = document.getElementById('configList');
            list.innerHTML = d.configs.map(f => {
                const isActive = f === d.active;
                const activeBadge = isActive ? '<span class="status-badge running btn-sm" style="padding:4px 8px;font-size:12px">● 激活中</span>' : '';
                const switchBtn = isActive ? '' : `<button class="btn btn-secondary btn-sm" onclick="switchConfig('${f}')">切换</button>`;
                const activeBgClass = isActive ? 'style="background:rgba(0,122,255,0.05)"' : '';
                return '<div class="proxy-item" ' + activeBgClass + '>' +
                    '<div class="proxy-icon">📄</div>' +
                    '<div class="proxy-info">' +
                    '<span class="proxy-name" style="font-family:monospace">' + f + '</span>' +
                    '</div>' +
                    '<div style="display:flex;align-items:center;gap:10px">' +
                    activeBadge +
                    switchBtn +
                    '</div></div>';
            }).join('');
        })
        .catch(e => console.error('Refresh configs error:', e));
}

function switchConfig(filename) {
    if (confirm(`确定要切换并激活配置文件 [${filename}] 吗？\n（系统将立即重新加载该配置下的所有转发规则）`)) {
        fetch('/api/config/switch', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({file: filename})
        }).then(r => r.json()).then(d => {
            if(d.success) {
                showToast('配置切换成功！服务已重新加载');
                setTimeout(() => location.reload(), 1500);
            } else {
                showToast(d.error, 'error');
            }
        });
    }
}

function addConfig() {
    document.getElementById('cName').value = '';
    document.getElementById('configModal').classList.add('active');
}

function closeConfigModal() {
    document.getElementById('configModal').classList.remove('active');
}

// 确保该函数成功注册并绑定
function saveConfig(e) {
    e.preventDefault();
    const data = {
        name: document.getElementById('cName').value
    };
    fetch('/api/config/create', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }).then(r => r.json()).then(d => {
        if(d.success) {
            showToast('配置文件创建成功！');
            closeConfigModal();
            refreshConfigs();
        } else {
            showToast(d.error, 'error');
        }
    });
}

document.getElementById('configModal').addEventListener('click', function(e) {
    if(e.target === this) closeConfigModal();
});

// ==================== FRPS Dashboard (方案二) 前端逻辑 ====================
function initFrpsConfigForm() {
    if (typeof frpsConfig !== 'undefined' && frpsConfig) {
        const enabledElem = document.getElementById('frpsDashEnabled');
        if (enabledElem) enabledElem.checked = !!frpsConfig.dash_enabled;
        const addrElem = document.getElementById('frpsDashAddr');
        if (addrElem) addrElem.value = frpsConfig.dash_addr || '';
        const portElem = document.getElementById('frpsDashPort');
        if (portElem) portElem.value = frpsConfig.dash_port || 7500;
        const userElem = document.getElementById('frpsDashUser');
        if (userElem) userElem.value = frpsConfig.dash_user || 'admin';
        const pwdElem = document.getElementById('frpsDashPassword');
        if (pwdElem) pwdElem.value = frpsConfig.dash_password || 'admin';
    }
}

function testFrpsConfig() {
    const btn = document.getElementById('btnTestFrpsConfig');
    if (btn) {
        btn.disabled = true;
        btn.textContent = '⏳ 测试中...';
    }

    const data = {
        dash_addr: document.getElementById('frpsDashAddr').value,
        dash_port: document.getElementById('frpsDashPort').value,
        dash_user: document.getElementById('frpsDashUser').value,
        dash_password: document.getElementById('frpsDashPassword').value
    };

    fetch('/api/frps/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(r => r.json()).then(d => {
        if (btn) {
            btn.disabled = false;
            btn.textContent = '🔍 测试服务端连接';
        }
        if (d.success) {
            showToast(d.message || '🎉 连接成功！');
        } else {
            showToast(d.error || '测试连接失败', 'error');
        }
    }).catch(err => {
        if (btn) {
            btn.disabled = false;
            btn.textContent = '🔍 测试服务端连接';
        }
        showToast('请求异常: ' + err, 'error');
    });
}

function saveFrpsConfig(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSaveFrpsConfig');
    if (btn) btn.disabled = true;

    const data = {
        dash_enabled: document.getElementById('frpsDashEnabled').checked,
        dash_addr: document.getElementById('frpsDashAddr').value,
        dash_port: document.getElementById('frpsDashPort').value,
        dash_user: document.getElementById('frpsDashUser').value,
        dash_password: document.getElementById('frpsDashPassword').value
    };

    fetch('/api/frps/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).then(r => r.json()).then(d => {
        if (btn) btn.disabled = false;
        if (d.success) {
            showToast('FRPS Dashboard 对接配置已保存！');
            fetchFrpsStatus();
        } else {
            showToast(d.error || '保存失败', 'error');
        }
    }).catch(err => {
        if (btn) btn.disabled = false;
        showToast('请求失败: ' + err, 'error');
    });
}

function renderFrpsProxiesList(proxies) {
    const container = document.getElementById('frpsProxyDetailsContainer');
    const tbody = document.getElementById('frpsProxiesTbody');
    if (!container || !tbody) return;

    if (!proxies) {
        container.style.display = 'none';
        tbody.innerHTML = '';
        return;
    }

    let allProxies = [];
    for (const ptype in proxies) {
        if (Array.isArray(proxies[ptype])) {
            proxies[ptype].forEach(p => {
                allProxies.push({
                    name: p.name || '-',
                    type: ptype,
                    port: p.listen_port || p.listenPort || p.conf?.remote_port || p.conf?.remotePort || '-',
                    status: p.status || 'online',
                    conns: p.cur_conns !== undefined ? p.cur_conns : (p.curConns || 0),
                    trafficIn: p.today_traffic_in !== undefined ? p.today_traffic_in : (p.todayTrafficIn || 0),
                    trafficOut: p.today_traffic_out !== undefined ? p.today_traffic_out : (p.todayTrafficOut || 0)
                });
            });
        }
    }

    if (allProxies.length === 0) {
        container.style.display = 'none';
        tbody.innerHTML = '';
        return;
    }

    container.style.display = 'block';
    tbody.innerHTML = allProxies.map(p => {
        const isOnline = p.status === 'online';
        const statusBadge = isOnline 
            ? `<span style="color:var(--apple-green);font-weight:600">🟢 在线</span>` 
            : `<span style="color:var(--apple-red);font-weight:600">🔴 离线</span>`;
        
        return `
            <tr style="border-bottom:1px solid var(--apple-separator)">
                <td style="padding:6px 8px;font-weight:600">${escapeHtml(p.name)}</td>
                <td style="padding:6px 8px"><span style="background:var(--apple-gray-bg, #f2f2f7);padding:2px 6px;border-radius:4px;font-size:11px">${p.type.toUpperCase()}</span></td>
                <td style="padding:6px 8px">${p.port}</td>
                <td style="padding:6px 8px">${statusBadge}</td>
                <td style="padding:6px 8px">${p.conns}</td>
                <td style="padding:6px 8px">${formatBytes(p.trafficIn)} / ${formatBytes(p.trafficOut)}</td>
            </tr>
        `;
    }).join('');
}

function fetchFrpsStatus() {
    fetch('/api/frps/status')
        .then(r => r.json())
        .then(d => {
            const metricsCard = document.getElementById('frpsMetricsCard');
            if (!metricsCard) return;

            if (!d.enabled) {
                metricsCard.style.display = 'none';
                return;
            }

            metricsCard.style.display = 'block';

            const badge = document.getElementById('frpsStatusBadge');
            const vElem = document.getElementById('frpsVersion');
            const cElem = document.getElementById('frpsClientCounts');
            const connElem = document.getElementById('frpsTotalConns');
            const inElem = document.getElementById('frpsTotalTrafficIn');
            const outElem = document.getElementById('frpsTotalTrafficOut');
            const tagsElem = document.getElementById('frpsProxyTypesTag');

            if (d.success && d.server_info) {
                const info = d.server_info;
                if (badge) {
                    badge.style.color = 'var(--apple-green)';
                    badge.textContent = '🟢 已连通';
                }
                if (vElem) vElem.textContent = info.version || '0.x';
                if (cElem) cElem.textContent = info.client_counts !== undefined ? info.client_counts : (info.clientCounts || 0);
                if (connElem) connElem.textContent = info.cur_conns !== undefined ? info.cur_conns : (info.curConns || 0);
                if (inElem) inElem.textContent = formatBytes(info.total_traffic_in || info.totalTrafficIn || 0);
                if (outElem) outElem.textContent = formatBytes(info.total_traffic_out || info.totalTrafficOut || 0);

                if (tagsElem && info.proxy_type_count) {
                    const pt = info.proxy_type_count;
                    const tags = [];
                    for (const k in pt) {
                        if (pt[k] > 0) {
                            tags.push(`<span style="background:var(--apple-gray-bg, #f2f2f7);padding:4px 8px;border-radius:6px;font-weight:600">${k.toUpperCase()}: ${pt[k]}</span>`);
                        }
                    }
                    tagsElem.innerHTML = tags.length ? tags.join(' ') : '<span style="font-size:12px;color:var(--apple-text-secondary)">服务端未注册任何代理规则</span>';
                }

                renderFrpsProxiesList(d.proxies);
            } else {
                if (badge) {
                    badge.style.color = 'var(--apple-red)';
                    badge.textContent = '🔴 ' + (d.error || '未连通');
                }
                renderFrpsProxiesList(null);
            }
        })
        .catch(err => {
            console.error('FRPS status error:', err);
        });
}

