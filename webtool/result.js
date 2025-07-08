// result.js

import { vars } from './variable.js';

export function switchTab(tabName) {
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.toggle('active', button.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        if (content.id === `${tabName}-tab`) {
            content.classList.add('active');
            content.style.display = 'block';
        } else {
            content.classList.remove('active');
            content.style.display = 'none';
        }
    });

    if (tabName === 'report') {
        const reportFrame = document.getElementById('report-frame');
        if (reportFrame) {
            reportFrame.style.display = 'block';
            reportFrame.focus();
        }
    }
}

export function initializeResultArea() {
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', () => switchTab(button.dataset.tab));
    });

    // 初始化时默认显示进度标签页
    switchTab('progress');
}

export function displayReport(data) {
    const progressContent = document.getElementById('progress-content');
    switchTab('progress');

    if (progressContent) {
        if (data.error) {
            progressContent.innerHTML = `
                <h2>错误</h2>
                <div class="error-container">
                    <pre class="error">${data.error}</pre>
                </div>
            `;
        } else {
            progressContent.innerHTML = `
                <h2>代码评审报告</h2>
                <pre>${JSON.stringify(data, null, 2)}</pre>
            `;
        }
    }
}