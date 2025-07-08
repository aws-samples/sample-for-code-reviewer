// dialog.js

import { saveFormData } from './section.js';
import { refresh_rules } from './section_action.js';
import { addRuleToDropdown, updateSectionVisibility } from './section.js';
import { escapeHtml } from './util.js';

export function showTooltip(event) {
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = event.target.dataset.tooltip;
    document.body.appendChild(tooltip);

    const iconRect = event.target.getBoundingClientRect();
    tooltip.style.top = `${iconRect.bottom + window.scrollY + 5}px`;
    tooltip.style.left = `${iconRect.left + window.scrollX}px`;
}

export function hideTooltip() {
    const tooltip = document.querySelector('.tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

export function showToast(message) {
    const toast = document.getElementById('toast-message');
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 2000);
}

export function showDialog(options) {
    const dialogOverlay = document.getElementById('common-dialog');
    const dialog = dialogOverlay.querySelector('.dialog');
    const dialogTitle = dialog.querySelector('h3');
    const dialogContent = dialog.querySelector('.dialog-content');
    const dialogButtons = dialog.querySelector('.dialog-buttons');

    // Set dialog style
    dialog.className = 'dialog';
    dialog.classList.add(options.style === 'small' ? 'small-dialog' : 'default-dialog');
    dialog.setAttribute('data-style', options.style || 'default');

    // Set title
    dialogTitle.textContent = options.title;

    // Set content
    dialogContent.innerHTML = options.content;

    // Clear existing buttons
    dialogButtons.innerHTML = '';

    // Add buttons
    options.buttons.forEach(button => {
        if (button.enabled) {
            const btn = document.createElement('button');
            btn.textContent = button.label;
            btn.addEventListener('click', button.action);
            dialogButtons.appendChild(btn);
        }
    });

    // Event handlers
    if (options.events) {
        if (options.events.beforeOpen) options.events.beforeOpen();
        dialogOverlay.style.display = 'flex';
        if (options.events.afterOpen) options.events.afterOpen();

        dialogOverlay.onclick = (event) => {
            if (event.target === dialogOverlay) {
                if (options.events.beforeClose) options.events.beforeClose();
                dialogOverlay.style.display = 'none';
                if (options.events.afterClose) options.events.afterClose();
            }
        };
    } else {
        dialogOverlay.style.display = 'flex';
    }
}

export function closeDialog() {
    const dialogOverlay = document.getElementById('common-dialog');
    if (dialogOverlay) {
        dialogOverlay.style.display = 'none';
    }
}

export function showErrorDialog(message) {
    showDialog({
        title: '错误',
        content: `<p>${message}</p>`,
        buttons: [
            {
                enabled: true,
                label: '确定',
                action: closeDialog
            }
        ],
        style: 'small'
    });
}

export function showInfoDialog(title, message) {
    showDialog({
        title: title,
        content: `<p>${message}</p>`,
        buttons: [],
        style: 'small'
    });
}

export function closeInfoDialog() {
    closeDialog();
}

export function showDetailDialog(title, content, buttons) {
    // 移除重复的response部分
    const contentLines = content.split('\n');
    const responseIndex = contentLines.findIndex(line => line.trim().startsWith('注意：'));
    if (responseIndex !== -1) {
        content = contentLines.slice(0, responseIndex).join('\n');
    }

    showDialog({
        title: title,
        content: `<pre>${escapeHtml(content)}</pre>`,
        buttons: buttons,
        style: 'default',
        events: {
            afterOpen: () => {
                const dialogContent = document.querySelector('.dialog-content');
                if (dialogContent) {
                    dialogContent.scrollTop = 0;
                }
            },
            beforeClose: () => {
                const dialogContent = document.querySelector('.dialog-content');
                if (dialogContent) {
                    dialogContent.scrollTop = 0;
                }
            }
        }
    });
}

export function closeDetailDialog() {
    closeDialog();
}

function validateGitlabUrl(url) {
    if (url === '') {
        return true; // Allow empty URL
    }
    try {
        new URL(url);
        return true;
    } catch (error) {
        return false;
    }
}

export function showGitlabInfoDialog() {
    showDialog({
        title: '修改Gitlab信息',
        content: `
            <div class="input-row">
                <label for="edit-gitlab-url">Gitlab地址:</label>
                <input type="text" id="edit-gitlab-url">
            </div>
            <div class="input-row">
                <label for="edit-access-token">Access Token:</label>
                <div class="password-input-container">
                    <input type="password" id="edit-access-token">
                    <button type="button" id="edit-toggle-access-token" class="toggle-password">👁️</button>
                    <div class="checkbox-container">
                        <input type="checkbox" id="edit-enable-access-token">
                        <label for="edit-enable-access-token">启用</label>
                    </div>
                </div>
            </div>
            <div class="input-row">
                <label for="edit-gitlab-branch">Branch:</label>
                <input type="text" id="edit-gitlab-branch">
            </div>
        `,
        buttons: [
            {
                enabled: true,
                label: '确认',
                action: () => {
                    const gitlabUrlInput = document.getElementById('edit-gitlab-url');
                    const accessTokenInput = document.getElementById('edit-access-token');
                    const enableAccessTokenCheckbox = document.getElementById('edit-enable-access-token');
                    const gitlabBranchInput = document.getElementById('edit-gitlab-branch');

                    if (!validateGitlabUrl(gitlabUrlInput.value)) {
                        showErrorDialog('请输入有效的Gitlab URL或留空');
                        return;
                    }

                    if (enableAccessTokenCheckbox.checked && !accessTokenInput.value.trim()) {
                        showErrorDialog('启用Access Token时，Access Token不能为空');
                        return;
                    }

                    const gitlabUrlDisplay = document.getElementById('gitlab-url-display');
                    const accessTokenDisplay = document.getElementById('access-token-display');
                    const gitlabBranchDisplay = document.getElementById('gitlab-branch-display');

                    gitlabUrlDisplay.textContent = gitlabUrlInput.value;
                    accessTokenDisplay.setAttribute('data-value', accessTokenInput.value);
                    accessTokenDisplay.setAttribute('data-enabled', enableAccessTokenCheckbox.checked);
                    if (enableAccessTokenCheckbox.checked && accessTokenInput.value) {
                        accessTokenDisplay.textContent = '••••••••';
                        accessTokenDisplay.setAttribute('data-type', 'password');
                    } else {
                        accessTokenDisplay.textContent = '未配置';
                        accessTokenDisplay.setAttribute('data-type', 'text');
                    }
                    gitlabBranchDisplay.textContent = gitlabBranchInput.value;

                    saveFormData();
                    closeGitlabInfoDialog();
                    updateSectionVisibility();

                    // 检查是否满足触发 refresh_rules 的条件
                    if (gitlabUrlInput.value && (!enableAccessTokenCheckbox.checked || (enableAccessTokenCheckbox.checked && accessTokenInput.value))) {
                        refresh_rules();
                    }
                }
            },
            {
                enabled: true,
                label: '取消',
                action: closeGitlabInfoDialog
            }
        ],
        events: {
            beforeOpen: () => {
                const currentGitlabUrl = document.getElementById('gitlab-url-display').textContent;
                const currentAccessToken = document.getElementById('access-token-display').getAttribute('data-value');
                const currentEnableAccessToken = document.getElementById('access-token-display').getAttribute('data-type') === 'password';
                const currentGitlabBranch = document.getElementById('gitlab-branch-display').textContent;

                const gitlabUrlInput = document.getElementById('edit-gitlab-url');
                const accessTokenInput = document.getElementById('edit-access-token');
                const enableAccessTokenCheckbox = document.getElementById('edit-enable-access-token');
                const toggleAccessTokenBtn = document.getElementById('edit-toggle-access-token');
                const gitlabBranchInput = document.getElementById('edit-gitlab-branch');

                gitlabUrlInput.value = currentGitlabUrl;
                accessTokenInput.value = currentAccessToken;
                enableAccessTokenCheckbox.checked = currentEnableAccessToken;
                accessTokenInput.type = 'password';
                toggleAccessTokenBtn.textContent = '👁️';
                gitlabBranchInput.value = currentGitlabBranch;

                toggleAccessTokenBtn.onclick = function() {
                    if (accessTokenInput.type === 'password') {
                        accessTokenInput.type = 'text';
                        toggleAccessTokenBtn.textContent = '🔒';
                    } else {
                        accessTokenInput.type = 'password';
                        toggleAccessTokenBtn.textContent = '👁️';
                    }
                };

                enableAccessTokenCheckbox.addEventListener('change', function() {
                    accessTokenInput.disabled = !this.checked;
                });

                accessTokenInput.disabled = !enableAccessTokenCheckbox.checked;
            }
        },
        style: 'default'
    });
}

export function closeGitlabInfoDialog() {
    closeDialog();
}

export function showNewRuleDialog() {
    const newRuleDialog = document.getElementById('new-rule-dialog');
    if (!newRuleDialog) {
        console.error("Cannot find element with id 'new-rule-dialog'");
        return;
    }
    newRuleDialog.style.display = 'flex';

    const confirmButton = document.getElementById('confirm-new-rule');
    const cancelButton = document.getElementById('cancel-new-rule');
    const ruleNameInput = document.getElementById('new-rule-name');
    const fileNameInput = document.getElementById('new-rule-filename');
    
    let errorMessageElement = newRuleDialog.querySelector('#new-rule-error-message');
    if (!errorMessageElement) {
        errorMessageElement = document.createElement('p');
        errorMessageElement.id = 'new-rule-error-message';
        errorMessageElement.style.color = 'red';
        const dialogContent = newRuleDialog.querySelector('.dialog-content');
        dialogContent.appendChild(errorMessageElement);
    }

    const validateFields = () => {
        let isValid = true;
        let errorMessage = '';

        if (!ruleNameInput.value.trim()) {
            isValid = false;
            errorMessage = '请输入规则名称';
        } else if (!fileNameInput.value.trim()) {
            isValid = false;
            errorMessage = '请输入文件名称';
        } else if (!fileNameInput.value.endsWith('.yaml')) {
            isValid = false;
            errorMessage = '文件名称必须以 .yaml 结尾';
        } else {
            const existingValues = Array.from(document.getElementById('rules-dropdown').options).map(option => option.value);
            if (existingValues.includes(fileNameInput.value)) {
                isValid = false;
                errorMessage = '文件名称已存在，请使用其他名称';
            }
        }

        errorMessageElement.textContent = errorMessage;
        return isValid;
    };

    confirmButton.addEventListener('click', () => {
        if (validateFields()) {
            const ruleName = ruleNameInput.value.trim();
            const fileName = fileNameInput.value.trim();
            addRuleToDropdown(ruleName, fileName);
            closeNewRuleDialog();
        }
    });

    cancelButton.addEventListener('click', closeNewRuleDialog);

    const dialogButtons = newRuleDialog.querySelector('.dialog-buttons');
    dialogButtons.style.display = 'flex';
    dialogButtons.style.justifyContent = 'flex-end';
}

export function closeNewRuleDialog() {
    const newRuleDialog = document.getElementById('new-rule-dialog');
    if (newRuleDialog) {
        newRuleDialog.style.display = 'none';
    }
    const ruleNameInput = document.getElementById('new-rule-name');
    const fileNameInput = document.getElementById('new-rule-filename');
    const errorMessageElement = document.getElementById('new-rule-error-message');
    
    if (ruleNameInput) ruleNameInput.value = '';
    if (fileNameInput) fileNameInput.value = '';
    if (errorMessageElement) errorMessageElement.textContent = '';
}

function scrollDialogToTop() {
    setTimeout(() => {
        const dialogContent = document.querySelector('#common-dialog .dialog-content');
        if (dialogContent) {
            dialogContent.scrollLeft = 0;
            dialogContent.scrollTop = 0;
        }
    }, 0);
}

export function showDialogMessage(message, isError = false) {
    scrollDialogToTop();
    const dialogContent = document.querySelector('#common-dialog .dialog-content');
    if (dialogContent) {
        const mask = document.createElement('div');
        mask.className = 'dialog-message-mask';
        mask.innerHTML = `
            <div class="dialog-message-content">
                ${message}
                ${isError ? '<button class="close-error-message">关闭错误消息</button>' : ''}
            </div>
        `;
        
        // 移除已存在的mask（如果有）
        const existingMask = dialogContent.querySelector('.dialog-message-mask');
        if (existingMask) {
            existingMask.remove();
        }
        
        // 将mask插入到dialog-content的开头
        dialogContent.insertBefore(mask, dialogContent.firstChild);

        // 添加关闭按钮的事件监听器
        if (isError) {
            const closeButton = mask.querySelector('.close-error-message');
            closeButton.addEventListener('click', hideDialogMessage);
        }
    }
}

export function hideDialogMessage() {
    const mask = document.querySelector('#common-dialog .dialog-message-mask');
    if (mask) {
        mask.remove();
    }
}