// section.js

import { showAllSections } from './section_action.js';
import { highlightElement, is_ready } from './util.js';
import { vars, inbuiltSections, nonCancelableSections, typeMapping } from './variable.js';

function getSessionId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('session') || 'default';
}

export function toggleSection(checkbox) {
    const section = checkbox.closest('.section-wrapper').querySelector('.section');
    section.classList.toggle('collapsed', !checkbox.checked);
    saveFormData();
}

export function loadSectionData(sectionId, data){
    if (data) {
        setValueIfElementExists(`${sectionId}-guide`, data.guide);
        setValueIfElementExists(`${sectionId}-text`, data.value);
    }
}

export function addCustomSection(name = '', guide = '', value = '') {
    const sortableSections = document.getElementById('sortable-sections');
    const newSectionWrapper = document.createElement('div');
    newSectionWrapper.className = 'section-wrapper';
    const newCheckbox = document.createElement('input');
    newCheckbox.type = 'checkbox';
    newCheckbox.className = 'section-checkbox';
    newCheckbox.checked = true;
    newSectionWrapper.appendChild(newCheckbox);
    const newSection = document.createElement('div');
    newSection.className = 'section custom-section';
    newSection.setAttribute('data-name', name);
    newSection.innerHTML = `
        <h2 class="section-title">${name || '新配置'}</h2>
        <div class="section-content">
            <div class="input-row">
                <label for="section-name">配置名称:</label>
                <input type="text" class="section-name" name="name-${name}" value="${name}">
            </div>
            <div class="input-row">
                <label for="section-guide">引导语:</label>
                <input type="text" class="section-guide" name="guide-${name}" value="${guide}">
            </div>
            <textarea placeholder="Section Value">${value}</textarea>
            <button class="delete-section">删除配置</button>
        </div>
    `;
    newSectionWrapper.appendChild(newSection);
    sortableSections.appendChild(newSectionWrapper);
    
    const titleElement = newSection.querySelector('.section-title');
    const nameInput = newSection.querySelector('.section-name');
    nameInput.addEventListener('input', function() {
        titleElement.textContent = this.value || '新配置';
        newSection.setAttribute('data-name', this.value);
        saveFormData();
    });

    newSection.querySelector('.delete-section').addEventListener('click', function() {
        sortableSections.removeChild(newSectionWrapper);
        saveFormData();
    });
    newSection.querySelectorAll('input, textarea').forEach(input => {
        input.addEventListener('input', saveFormData);
    });
    newSection.querySelectorAll('input[type="text"], textarea').forEach(input => {
        input.addEventListener('input', resetTemplateDropdown);
    });

    newCheckbox.addEventListener('change', () => toggleSection(newCheckbox));
    newCheckbox.addEventListener('change', resetTemplateDropdown);

    titleElement.draggable = true;
    titleElement.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', '');  // Required for Firefox
    });

    return newSection;
}

export function resetTemplateDropdown() {
    const dropdown = document.getElementById('template-dropdown');
    if (dropdown) {
        dropdown.value = '';  // 将下拉框重置为"选择模板"选项
    }
}

export function updateTemplateDropdown(type) {
    const dropdown = document.getElementById('template-dropdown');
    if (!dropdown) return;  // 如果下拉框不存在，直接返回

    dropdown.innerHTML = '';
    
    // 添加一个默认选项
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = '选择模板';
    dropdown.appendChild(defaultOption);
    
    const serverType = typeMapping[type] || type;
    if (vars.templateData && vars.templateData[serverType] && vars.templateData[serverType].length > 0) {
        vars.templateData[serverType].forEach((template, index) => {
            const option = document.createElement('option');
            option.value = index.toString();
            option.textContent = template.name;
            dropdown.appendChild(option);
        });
    }
}

export function loadFormData() {
    const sessionId = getSessionId();
    if (!vars.formData) {
        return {};
    }

    const savedData = localStorage.getItem(`formData_${sessionId}`);

    if (savedData) {
        Object.assign(vars.formData, JSON.parse(savedData));
    } else {
        // 使用默认值
        Object.assign(vars.formData, {
            gitlabBranch: 'main',
            targetFileList: '**',
            type: 'files',
            model: 'claude3-sonnet',
            accessToken: '',
            enableAccessToken: false,
            endpoint: 'https://endpoint.cr.teonbox.com/codereview',
            triggerEvent: 'merge',
            confirm: false,
            confirmPrompt: ''
        });
    }

    // 设置表单值
    setValueIfElementExists('target-file-list', vars.formData.targetFileList || '**');
    setValueIfElementExists('model-select', vars.formData.model || 'claude3-sonnet');
    setValueIfElementExists('endpoint', vars.formData.endpoint || 'https://endpoint.cr.teonbox.com/codereview');

    // 设置 Gitlab 地址、Access Token 和 Branch 显示
    const gitlabUrlDisplay = document.getElementById('gitlab-url-display');
    const accessTokenDisplay = document.getElementById('access-token-display');
    const branchDisplay = document.getElementById('gitlab-branch-display');
    if (gitlabUrlDisplay) {
        gitlabUrlDisplay.textContent = vars.formData.gitlabUrl || '';
    }
    if (accessTokenDisplay) {
        if (vars.formData.enableAccessToken && vars.formData.accessToken) {
            accessTokenDisplay.textContent = '••••••••';
            accessTokenDisplay.setAttribute('data-value', vars.formData.accessToken);
            accessTokenDisplay.setAttribute('data-type', 'password');
        } else {
            accessTokenDisplay.textContent = '未配置';
            accessTokenDisplay.setAttribute('data-value', '');
            accessTokenDisplay.setAttribute('data-type', 'text');
        }
    }
    if (branchDisplay) {
        branchDisplay.textContent = vars.formData.gitlabBranch || 'main';
    }

    // 设置类型单选按钮
    const typeRadio = document.querySelector(`input[name="type"][value="${vars.formData.type || 'files'}"]`);
    if (typeRadio) {
        typeRadio.checked = true;
        updateTemplateDropdown(vars.formData.type || 'files');
    }

    // 设置触发事件单选按钮
    const triggerEventRadio = document.querySelector(`input[name="trigger-event"][value="${vars.formData.triggerEvent || 'merge'}"]`);
    if (triggerEventRadio) {
        triggerEventRadio.checked = true;
    }

    // 设置二次检查复选框
    const confirmCheckbox = document.getElementById('confirm');
    if (confirmCheckbox) {
        confirmCheckbox.checked = vars.formData.confirm || false;
    }

    // 设置二次检查提示词
    const confirmPromptTextarea = document.getElementById('confirm-prompt');
    if (confirmPromptTextarea) {
        confirmPromptTextarea.value = vars.formData.confirmPrompt || '';
    }

    // 根据类型显示或隐藏相应的提交ID输入框
    updateCommitInputs();

    // 加载其他保存的数据
    if (savedData) {
        setValueIfElementExists('commit-id', vars.formData.commitId || '');
        setValueIfElementExists('from-commit-id', vars.formData.fromCommitId || '');
        setValueIfElementExists('to-commit-id', vars.formData.toCommitId || '');
        setValueIfElementExists('system-text', vars.formData.systemPrompt || '');

        // 加载其他部分（项目描述、数据库结构等）
        inbuiltSections.forEach(sectionId => {
            if (vars.formData[sectionId]) {
                loadSectionData(sectionId, vars.formData[sectionId]);
            }
        });

        const apiKeyInput = document.getElementById('api-key');
        const enableApiKeyCheckbox = document.getElementById('enable-api-key');
        
        if (vars.formData.enableApiKey !== undefined) {
            enableApiKeyCheckbox.checked = vars.formData.enableApiKey;
            apiKeyInput.disabled = !vars.formData.enableApiKey;
            if (vars.formData.enableApiKey) {
                apiKeyInput.value = vars.formData.apiKey || '';
                apiKeyInput.placeholder = '请填写API Key';
            } else {
                apiKeyInput.value = '';
                apiKeyInput.placeholder = '不需要填写API Key';
            }
        } else {
            enableApiKeyCheckbox.checked = false;
            apiKeyInput.disabled = true;
            apiKeyInput.value = '';
            apiKeyInput.placeholder = '不需要填写API Key';
        }

        // 加载复选框状态
        if (vars.formData.checkboxStates) {
            for (const [id, checked] of Object.entries(vars.formData.checkboxStates)) {
                const checkbox = document.getElementById(id);
                if (checkbox) {
                    checkbox.checked = checked;
                    toggleSection(checkbox);
                }
            }
        }

        // 加载自定义部分
        if (vars.formData.customSections) {
            vars.formData.customSections.forEach(section => {
                addCustomSection(section.name, section.guide, section.value);
            });
        }

        // 恢复部分顺序
        if (vars.formData.sectionOrder) {
            const sortableSections = document.getElementById('sortable-sections');
            if (sortableSections) {
                vars.formData.sectionOrder.forEach(id => {
                    const section = document.getElementById(id);
                    if (section) {
                        sortableSections.appendChild(section.closest('.section-wrapper'));
                    }
                });
            }
        }
    }

    // 重置报告框架
    const reportFrame = document.getElementById('report-frame');
    if (reportFrame) {
        reportFrame.src = '';
        reportFrame.style.display = 'none';
    }
    const reportContent = document.getElementById('report-content');
    if (reportContent) {
        reportContent.innerHTML = '';
        reportContent.style.display = 'block';
    }

    // 为所有相关的输入字段和复选框添加事件监听器
    addEventListenersToInputs();

    // 更新 Section 可见性
    updateSectionVisibility();

    // 检查 URL 中是否存在 anchor，如果存在，则使用该值来选择对应的规则
    const anchor = window.location.hash.slice(1);
    if (anchor) {
        const rulesDropdown = document.getElementById('rules-dropdown');
        const option = Array.from(rulesDropdown.options).find(opt => opt.value === anchor);
        if (option) {
            rulesDropdown.value = anchor;
            saveFormData();
        }
    }
}

export function saveFormData() {
    const sessionId = getSessionId();
    vars.formData.endpoint = document.getElementById('endpoint')?.value || '';
    vars.formData.gitlabUrl = document.getElementById('gitlab-url-display')?.textContent || '';
    vars.formData.apiKey = document.getElementById('api-key').value;
    vars.formData.enableApiKey = document.getElementById('enable-api-key').checked;
    vars.formData.accessToken = document.getElementById('access-token-display')?.getAttribute('data-value') || '';
    vars.formData.enableAccessToken = document.getElementById('access-token-display')?.getAttribute('data-type') === 'password';
    vars.formData.gitlabBranch = document.getElementById('gitlab-branch-display')?.textContent || 'main';
    vars.formData.model = document.getElementById('model-select')?.value || '';
    vars.formData.targetFileList = document.getElementById('target-file-list')?.value || '';
    vars.formData.type = document.querySelector('input[name="type"]:checked')?.value || '';
    vars.formData.commitId = document.getElementById('commit-id')?.value || '';
    vars.formData.fromCommitId = document.getElementById('from-commit-id')?.value || '';
    vars.formData.toCommitId = document.getElementById('to-commit-id')?.value || '';
    vars.formData.systemPrompt = document.getElementById('system-text')?.value || '';
    vars.formData.confirm = document.getElementById('confirm')?.checked || false;
    vars.formData.confirmPrompt = document.getElementById('confirm-prompt')?.value || '';

    inbuiltSections.forEach(sectionId => {
        vars.formData[sectionId] = {
            guide: document.getElementById(`${sectionId}-guide`)?.value || '',
            value: document.getElementById(`${sectionId}-text`)?.value || ''
        };
    });

    vars.formData.customSections = [];
    vars.formData.checkboxStates = {};
    vars.formData.sectionOrder = Array.from(document.querySelectorAll('#sortable-sections .section-wrapper'))
        .map(wrapper => wrapper.querySelector('.section').id);
    vars.formData.triggerEvent = document.querySelector('input[name="trigger-event"]:checked')?.value || 'merge';
    
    document.querySelectorAll('.section-checkbox').forEach(checkbox => {
        vars.formData.checkboxStates[checkbox.id] = checkbox.checked;
    });

    document.querySelectorAll('.custom-section').forEach(section => {
        vars.formData.customSections.push({
            name: section.querySelector('.section-name').value,
            guide: section.querySelector('.section-guide').value,
            value: section.querySelector('textarea').value
        });
    });

    localStorage.setItem(`formData_${sessionId}`, JSON.stringify(vars.formData));

    // 更新 Section 可见性
    updateSectionVisibility();
}

function setValueIfElementExists(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.value = value;
    }
}

function addEventListenersToInputs() {
    const sections = document.querySelectorAll('.section-wrapper:not(#gitlab-config, #rules-config)');
    sections.forEach(sectionWrapper => {
        const inputs = sectionWrapper.querySelectorAll('input[type="text"], textarea');
        inputs.forEach(input => {
            input.addEventListener('input', resetTemplateDropdown);});

        const checkbox = sectionWrapper.querySelector('.section-checkbox');
        if (checkbox){
            checkbox.addEventListener('change', resetTemplateDropdown);
        }
    });

    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('delete-section')) {
            resetTemplateDropdown();
        }
    });

    // 添加 API Key 输入框和复选框的事件监听器
    const apiKeyInput = document.getElementById('api-key');
    const enableApiKeyCheckbox = document.getElementById('enable-api-key');

    enableApiKeyCheckbox.addEventListener('change', function() {
        apiKeyInput.disabled = !this.checked;
        if (this.checked) {
            apiKeyInput.value = '';
            apiKeyInput.placeholder = '请填写API Key';
            apiKeyInput.focus();
        } else {
            apiKeyInput.value = '';
            apiKeyInput.placeholder = '不需要填写API Key';
        }
        saveFormData();
    });

    apiKeyInput.addEventListener('focus', function() {
        if (this.value === '不需要填写API Key') {
            this.value = '';
        }
    });

    apiKeyInput.addEventListener('blur', function() {
        if (!this.value.trim() && enableApiKeyCheckbox.checked) {
            this.value = '';
        } else if (!enableApiKeyCheckbox.checked) {
            this.value = '';
            this.placeholder = '不需要填写API Key';
        }
        saveFormData();
    });

    // 添加类型单选按钮的事件监听器
    const typeRadios = document.querySelectorAll('input[name="type"]');
    typeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            updateCommitInputs();
            saveFormData();
        });
    });

    // 添加二次检查复选框的事件监听器
    const confirmCheckbox = document.getElementById('confirm');
    if (confirmCheckbox) {
        confirmCheckbox.addEventListener('change', function() {
            updateConfirmComponents();
            saveFormData();
        });
    }

    // 添加二次检查提示词的事件监听器
    const confirmPromptTextarea = document.getElementById('confirm-prompt');
    if (confirmPromptTextarea) {
        confirmPromptTextarea.addEventListener('input', saveFormData);
    }
}

export function addRuleToDropdown(ruleName, fileName) {
    const rulesDropdown = document.getElementById('rules-dropdown');
    if (rulesDropdown) {
        const option = document.createElement('option');
        option.value = fileName;
        option.textContent = ruleName;
        rulesDropdown.appendChild(option);
        rulesDropdown.value = fileName;
        saveFormData();
    }
}

export function updateSectionVisibility(succ=true) {
    const sectionsToToggle = document.querySelectorAll('.section-wrapper:not(:has(#endpoint-config)):not(:has(#gitlab-config)):not(:has(#refresh-data-section)), .button-row');
    const gitlabConfigMessage = document.getElementById('gitlab-config-message');
    const refreshButtonSection = document.getElementById('refresh-data-section');
    
    if (succ && is_ready()) {
        sectionsToToggle.forEach(section => {
            section.classList.remove('hidden-section');
        });
        if (gitlabConfigMessage) {
            gitlabConfigMessage.classList.add('hidden-message');
        }
        if (refreshButtonSection) {
            refreshButtonSection.classList.add('hidden-message');
        }
    } else {
        sectionsToToggle.forEach(section => {
            section.classList.add('hidden-section');
        });
        if (gitlabConfigMessage) {
            gitlabConfigMessage.classList.remove('hidden-message');
        }
        if (refreshButtonSection) {
            refreshButtonSection.classList.remove('hidden-message');
        }
    }
}

export function initializeDragAndDrop() {
    const sortableSections = document.getElementById('sortable-sections');
    if (sortableSections) {
        sortableSections.addEventListener('dragstart', (e) => {
            if (e.target.tagName === 'H2') {
                e.target.closest('.section-wrapper').classList.add('dragging');
            }
        });

        sortableSections.addEventListener('dragend', (e) => {
            if (e.target.tagName === 'H2') {
                e.target.closest('.section-wrapper').classList.remove('dragging');
                saveFormData();
            }
        });

        sortableSections.addEventListener('dragover', (e) => {
            e.preventDefault();
            const afterElement = getDragAfterElement(sortableSections, e.clientY);
            const draggable = document.querySelector('.dragging');
            if (draggable && afterElement) {
                if (afterElement.parentNode === sortableSections) {
                    sortableSections.insertBefore(draggable, afterElement);
                }
            } else if (draggable) {
                sortableSections.appendChild(draggable);
            }
        });
    }
}

function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.section-wrapper:not(.dragging)')];

    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

export function cancelAllSectionCheckboxes() {
    document.querySelectorAll('.section-checkbox').forEach(checkbox => {
        if (!nonCancelableSections.includes(checkbox.closest('.section-wrapper').querySelector('.section').id)) {
            checkbox.checked = false;
            toggleSection(checkbox);
        }
    });
}

export function removeCustomSections() {
    const sortableSections = document.getElementById('sortable-sections');
    if (sortableSections) {
        const customSections = sortableSections.querySelectorAll('.custom-section');
        customSections.forEach(section => {
            sortableSections.removeChild(section.closest('.section-wrapper'));
        });
    }
}

export function updateCommitInputs() {
    const type = document.querySelector('input[name="type"]:checked')?.value;
    const commitWhole = document.getElementById('commit-whole');
    const commitRange = document.getElementById('commit-range');
    
    if (type === 'whole') {
        commitWhole.style.display = 'block';
        commitRange.style.display = 'none';
    } else {
        commitWhole.style.display = 'none';
        commitRange.style.display = 'block';
    }
}