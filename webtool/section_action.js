// section_action.js

import { showInfoDialog, closeInfoDialog, showErrorDialog, showToast, showDetailDialog, closeDetailDialog, showDialog, showDialogMessage, hideDialogMessage } from './dialog.js';
import { getPathWithNamespace, setValueIfElementExists, highlightElement, getErrorMessage, escapeHtml } from './util.js';
import { executeCodeReviewWithAxios, fetchRules, saveRule } from './custom.js';
import { saveFormData, toggleSection, addCustomSection, updateSectionVisibility, cancelAllSectionCheckboxes, removeCustomSections, updateCommitInputs } from './section.js';
import { pollForReport } from './progress.js';
import { switchTab, displayReport } from './result.js';
import { vars, typeMapping, inbuiltSections } from './variable.js';

function getSessionId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('session') || 'default';
}

export function executeCodeReview() {
    const accessTokenDisplay = document.getElementById('access-token-display');
    const enableAccessToken = accessTokenDisplay.getAttribute('data-type') === 'password';
    const accessToken = enableAccessToken ? accessTokenDisplay.getAttribute('data-value') : '';

    const type = document.querySelector('input[name="type"]:checked')?.value || '';
    let commitId, fromCommitId, toCommitId;

    if (type === 'whole') {
        commitId = document.getElementById('commit-id')?.value || '';
    } else {
        fromCommitId = document.getElementById('from-commit-id')?.value || '';
        toCommitId = document.getElementById('to-commit-id')?.value || '';
    }

    // Get the selected rule name
    const rulesDropdown = document.getElementById('rules-dropdown');
    let selectedRuleName = null;
    if (rulesDropdown && rulesDropdown.options.length > 0) {
        selectedRuleName = rulesDropdown.options[rulesDropdown.selectedIndex].text;
        console.log('Selected:', selectedRuleName);
    }

    const params = {
        endpoint: document.getElementById('endpoint')?.value || '',
        apiKey: document.getElementById('api-key')?.value || '',
        enableApiKey: document.getElementById('enable-api-key')?.checked || false,
        accessToken: accessToken,
        enableAccessToken: enableAccessToken,
        repositoryUrl: document.getElementById('repository-url-display')?.textContent || '',
        type: typeMapping[type] || type,
        commitId: commitId,
        fromCommitId: fromCommitId,
        toCommitId: toCommitId,
        branch: document.getElementById('repository-branch-display')?.textContent || '',
        targetFileList: document.getElementById('target-file-list')?.value || '',
        prompt: generatePrompt(),
        model: document.getElementById('model-select')?.value || '',
        systemPrompt: document.getElementById('system-text')?.value || '',
        triggerEvent: document.querySelector('input[name="trigger-event"]:checked')?.value || 'merge',
        confirm: document.getElementById('confirm')?.checked || false,
        confirmPrompt: document.getElementById('confirm-prompt')?.value || '',
        enableThinking: document.getElementById('enable-thinking')?.checked || false,
        thinkingBudget: parseInt(document.getElementById('thinking-budget')?.value || '2000')
    };    

    if (selectedRuleName !== null) {
        params.ruleName = selectedRuleName;
    }

    switchTab('progress');
    const progressContent = document.getElementById('progress-content');
    if (progressContent) {
        progressContent.innerHTML = '';
    }

    const statusContainer = document.createElement('div');
    statusContainer.id = 'status-container';
    statusContainer.textContent = '发送请求中...';
    progressContent?.appendChild(statusContainer);

    executeCodeReviewWithAxios(params)
        .then(response => {
            if (response.status !== 200 || !response.data.succ) {
                throw new Error(JSON.stringify(response.data));
            }
            if (response.data.request_id) {
                if (statusContainer) {
                    statusContainer.textContent = '请求已发送，请稍事等待';
                }
                vars.reportStartTime = Date.now() - 2000; // 从2秒开始计时，这样显示时就会从3秒开始
                // 处理返回的 commit_id
                if (response.data.commit_id) {
                    document.getElementById('code-review-commit-id').value = response.data.commit_id;
                }
                pollForReport(params.endpoint, response.data.request_id, document.getElementById('code-review-commit-id').value, params.apiKey);
            } else {
                throw new Error("Missing request_id in response");
            }
        })
        .catch(error => {
            console.error(error)
            displayReport({ error: error.message });
        });
}

export function refresh_rules() {
    const endpoint = document.getElementById('endpoint')?.value || '';
    const repositoryUrl = document.getElementById('repository-url-display')?.textContent || '';
    const repositoryType = document.getElementById('repository-type-display')?.getAttribute('data-value') || 'gitlab';
    const accessTokenDisplay = document.getElementById('access-token-display');
    const enableAccessToken = accessTokenDisplay.getAttribute('data-type') === 'password';
    const accessToken = enableAccessToken ? accessTokenDisplay.getAttribute('data-value') : '';
    const apiKey = document.getElementById('api-key')?.value || '';
    const enableApiKey = document.getElementById('enable-api-key')?.checked || false;
    const branch = document.getElementById('repository-branch-display')?.textContent || '';

    if (endpoint && repositoryUrl && (enableAccessToken ? accessToken : true)) {
        showInfoDialog('信息', '加载规则中...');
        fetchRules(endpoint, repositoryUrl, repositoryType, enableAccessToken ? accessToken : '', enableApiKey ? apiKey : '', branch)
            .then((rules) => {
                closeInfoDialog();
                showAllSections();
                vars.globalRules.length = 0; // Clear the existing rules
                vars.globalRules.push(...rules); // Add new rules

                // 从 URL 中获取 anchor
                const urlAnchor = window.location.hash.slice(1);
                
                const rulesDropdown = document.getElementById('rules-dropdown');
                if (rulesDropdown) {
                    rulesDropdown.innerHTML = '';
                    let matchFound = false;

                    rules.forEach((rule, index) => {
                        const option = document.createElement('option');
                        option.value = rule.filename;
                        option.textContent = rule.name;
                        rulesDropdown.appendChild(option);

                        if (rule.filename === urlAnchor) {
                            rulesDropdown.value = rule.filename;
                            matchFound = true;
                        }
                    });

                    if (!matchFound && rules.length > 0) {
                        rulesDropdown.value = rules[0].filename;
                    }
                }

                initializeSections(rules.find(rule => rule.filename === rulesDropdown.value));
                updateSectionVisibility()
            })
            .catch((error) => {
                closeInfoDialog();
                console.error(error)
                showErrorDialog(error.message);
                updateSectionVisibility(false)
                hideAllSections();
            });
    } else {
        showErrorDialog('请先填写 Endpoint、代码仓库地址' + (enableAccessToken ? '和 Access Token' : ''));
        hideAllSections();
    }
}

export function showAllSections() {
    const hiddenSections = document.querySelectorAll('.hidden-on-load');
    hiddenSections.forEach(section => {
        if (!section.closest('#endpoint-config') && !section.closest('#repository-config')) {
            section.classList.remove('hidden-on-load');
            section.classList.add('hidden-on-load-disabled');
        }
    });
}

export function hideAllSections() {
    const hiddenSections = document.querySelectorAll('.hidden-on-load-disabled');
    hiddenSections.forEach(section => {
        if (!section.closest('#endpoint-config') && !section.closest('#repository-config')) {
            section.classList.remove('hidden-on-load-disabled');
            section.classList.add('hidden-on-load');
        }
    });
}

export function savePromptToFile() {
    const rulesDropdown = document.getElementById('rules-dropdown');
    const selectedRule = rulesDropdown?.value;

    if (selectedRule) {
        const prompt = generatePromptYaml();
        const yamlString = jsyaml.dump(prompt);
        const buttons = [
            {
                enabled: true,
                label: '拷贝',
                action: () => {
                    navigator.clipboard.writeText(yamlString).then(() => {
                        showToast('提示词已复制到剪贴板');
                    }).catch(err => {
                        console.error('复制失败:', err);
                        showToast('复制失败');
                    });
                }
            },
            {
                enabled: true,
                label: '保存',
                action: () => {
                    const endpoint = document.getElementById('endpoint').value;
                    const repositoryUrl = document.getElementById('repository-url-display').textContent;
                    const accessTokenDisplay = document.getElementById('access-token-display');
                    const enableAccessToken = accessTokenDisplay.getAttribute('data-type') === 'password';
                    const accessToken = enableAccessToken ? accessTokenDisplay.getAttribute('data-value') : '';
                    const apiKey = document.getElementById('api-key').value;
                    const enableApiKey = document.getElementById('enable-api-key').checked;
                    const branch = document.getElementById('repository-branch-display').textContent;

                    const project_id = getPathWithNamespace(repositoryUrl);
                    const repoUrl = repositoryUrl.replace(`/${project_id}`, '');

                    showDialogMessage('正在保存提示词...');
                    saveRule(endpoint, repoUrl, project_id, branch, yamlString, enableAccessToken ? accessToken : '', enableApiKey ? apiKey : null, selectedRule)
                        .then(data => {
                            hideDialogMessage();
                            if (data.succ) {
                                showToast('提示词已保存');
                                closeDetailDialog();
                            } else {
                                showDialogMessage(getErrorMessage(data.message), true);
                            }
                        })
                        .catch(error => {
                            hideDialogMessage();
                            showDialogMessage(getErrorMessage(error.message), true);
                        });
                }
            },
            {
                enabled: true,
                label: '取消',
                action: closeDetailDialog
            }
        ];

        showDetailDialog(`提示词文件 ${selectedRule}`, yamlString, buttons);
    } else {
        showToast('请先选择规则');
    }
}

export function generatePromptYaml() {
    const sessionId = getSessionId();
    if (!vars.formData) {
        return {};
    }

    const { type, targetFileList, model, systemPrompt } = vars.formData;
    const mode = typeMapping[type] || type;
    const branch = document.getElementById('repository-branch-display')?.textContent || '';
    const target = targetFileList;
    const system = systemPrompt.trim(); // 去掉系统提示词前后的空格
    const name = document.getElementById('rules-dropdown')?.selectedOptions[0]?.textContent || '';
    const triggerEvent = document.querySelector('input[name="trigger-event"]:checked')?.value || 'merge';
    const confirm = document.getElementById('confirm')?.checked || false;
    const confirmPrompt = document.getElementById('confirm-prompt')?.value || '';

    let yaml = {
        name: name,
        mode: mode,
        branch: branch,
        target: target,
        model: model,
        event: triggerEvent,
        system: system,
        confirm: confirm
    };

    // 只有当confirm为true时，才添加confirmPrompt字段
    if (confirm) {
        yaml.confirmPrompt = confirmPrompt;
    }

    // 获取界面上 section 的实际排序
    const sections = Array.from(document.querySelectorAll('#sortable-sections .section-wrapper, #response'));
    
    let order = [];
    sections.forEach(sectionWrapper => {
        const section = sectionWrapper.classList.contains('section') ? sectionWrapper : sectionWrapper.querySelector('.section');
        const checkbox = sectionWrapper.querySelector('.section-checkbox');
        
        if ((section.id !== 'repository-config' && section.id !== 'rules-config' && checkbox && checkbox.checked) || section.id === 'response') {
            let configName = section.dataset.configName;
            if (!configName) {
                if (section.id === 'response') {
                    configName = 'response';
                } else if (section.id === 'system') {
                    configName = 'system';
                }  else {
                    const nameInput = section.querySelector('.section-name');
                    configName = nameInput ? nameInput.value : '';
                }
            }
            
            const guideElement = section.querySelector('.section-guide') || section.querySelector('input[type="text"]');
            const guide = guideElement ? guideElement.value.trim() : '';
            const value = section.querySelector('textarea')?.value.trim() || '';

            console.log('Guide:', configName, guide, section.querySelector('.section-guide'))
            

            if (value) {
                yaml[configName] = guide ? `${guide}\n${value}` : value;
                order.push(configName);
            }
        }
    });

    // 确保系统提示词在第一位，输出要求在最后
    order = order.filter(item => item !== 'system' && item !== 'response');
    order.unshift('system');
    order.push('response');

    yaml.order = order.join(',');

    return yaml;
}

export function clearForm() {
    const sessionId = getSessionId();
    // 保存 showHelpOnStartup 的值
    const showHelpOnStartup = localStorage.getItem('showHelpOnStartup');

    // 清空当前 session 的 Local Storage
    Object.keys(localStorage).forEach(key => {
        if (key.startsWith(`${sessionId}_`)) {
            localStorage.removeItem(key);
        }
    });

    // 恢复 showHelpOnStartup 的值
    if (showHelpOnStartup !== null) {
        localStorage.setItem('showHelpOnStartup', showHelpOnStartup);
    }

    // 清空所有内置 Section 的内容并取消勾选
    inbuiltSections.forEach(sectionId => {
        const section = document.getElementById(sectionId);
        if (section) {
            const checkbox = document.getElementById(`${sectionId}-check`);
            const guide = section.querySelector('input[type="text"]');
            const value = section.querySelector('textarea');
            
            if (checkbox) {
                checkbox.checked = false;
                toggleSection(checkbox);
            }
            if (guide) guide.value = '';
            if (value) value.value = '';
        }
    });
    saveFormData();

    // 删除所有自定义 Section
    const sortableSections = document.getElementById('sortable-sections');
    const customSections = sortableSections?.querySelectorAll('.custom-section');
    customSections?.forEach(section =>{
        section.closest('.section-wrapper')?.remove();
    });
    // 重置模板下拉框resetTemplateDropdown();

    // 重新加载表单数据loadFormData();

    //显示提示消息
    showToast('表单已清空，代码仓库配置保持不变');
}

export function applyTemplate(templateIndex) {
    const selectedType = document.querySelector('input[name="type"]:checked')?.value|| 'all';
    const serverType = typeMapping[selectedType] || selectedType;
    const template = vars.templateData[serverType][templateIndex];
    if(!template) return;

    initializeSections(template);
}

export function generatePrompt() {
    let prompt= '';
    
    const type= document.querySelector('input[name="type"]:checked')?.value;
    if(type === 'diffs') {
        prompt = `以下是我的代码的diffs
{{code}}

`;
    } else {
        prompt = `以下是我的代码
{{code}}

`;
    }
    
    const sortableSections = document.querySelectorAll('#sortable-sections .section-wrapper');
    const responseSection = document.querySelector('#response');
    console.log('Sortable sections:', sortableSections)
    
    function processSection(sectionWrapper) {
        const checkbox = sectionWrapper.querySelector('.section-checkbox');
        const section = sectionWrapper.classList.contains('.section') ? sectionWrapper : sectionWrapper.querySelector('.section');
        
        if (!checkbox || checkbox.checked) {
            let guide = section.querySelector('.section-guide')?.value || section.querySelector('input[type="text"]')?.value || '';
            let value = section.querySelector('textarea')?.value || '';

            console.log('Test:', guide, value)
            if (guide) {
                prompt += `${guide}\n`;
            }
            if (value) {
                prompt += `${value}\n\n`;
            } else if (guide) {
                prompt += '\n';
            }
        }
    }

    sortableSections.forEach(processSection);

    return prompt.trim();
}

export function initializeSections(rule) {
    if (!rule) {
        console.log('No rule provided for initialization');
        return;
    }
    console.log('initializeSections:', rule)

    // Clean operation
    cancelAllSectionCheckboxes();
    removeCustomSections();

    // Calculate order
    let order = rule.order ? rule.order.split(',').map(item => item.trim()) : Object.keys(rule).filter(key => inbuiltSections.includes(key));

    // Ensure 'system' is first and 'response' is last
    order = order.filter(item => item !== 'system' && item !== 'response');
    order.unshift('system');
    order.push('response');

    // Set configuration rule properties
    const mappedMode = Object.keys(typeMapping).find(key => typeMapping[key] === rule.mode) || rule.mode;
    const typeRadios = document.querySelectorAll('input[name="type"]');
    let firstTypeRadio = null;
    typeRadios.forEach((radio, index) => {
        if (index === 0) firstTypeRadio = radio;
        if (radio.value === mappedMode) {
            radio.checked = true;
            highlightElement(radio);
        }
    });
    if (!document.querySelector('input[name="type"]:checked') && firstTypeRadio) {
        firstTypeRadio.checked = true;
        highlightElement(firstTypeRadio);
    }

    setValueIfElementExists('target-file-list', rule.target || '');
    highlightElement(document.getElementById('target-file-list'));
    
    const modelSelect = document.getElementById('model-select');
    if (modelSelect) {
        const modelOption = Array.from(modelSelect.options).find(option => option.value === rule.model);
        if (modelOption) {
            modelSelect.value = rule.model;
        } else if (modelSelect.options.length > 0) {
            modelSelect.selectedIndex = 0;
        }
        highlightElement(modelSelect);
    }

    // Set trigger event
    const triggerEventRadios = document.querySelectorAll('input[name="trigger-event"]');
    triggerEventRadios.forEach(radio => {
        if (radio.value === rule.event) {
            radio.checked = true;
            highlightElement(radio);
        }
    });

    // Set confirm checkbox
    const confirmCheckbox = document.getElementById('confirm');
    if (confirmCheckbox) {
        confirmCheckbox.checked = rule.confirm || false;
        highlightElement(confirmCheckbox);
    }

    // Set confirm prompt
    const confirmPromptTextarea = document.getElementById('confirm-prompt');
    if (confirmPromptTextarea) {
        confirmPromptTextarea.value = rule.confirmPrompt || '';
        highlightElement(confirmPromptTextarea);
    }

    // Load data for each section according to the order
    order.forEach(key => {
        let section;
        if (inbuiltSections.includes(key)) {
            section = document.getElementById(key);
        } else {
            let value = rule[key] || '';
            let guide = '';
            let sectionValue = value;

            // Check if the first line ends with a colon
            const lines = value.split('\n');
            if (lines[0].endsWith(':') || lines[0].endsWith('：')) {
                guide = lines[0];
                sectionValue = lines.slice(1).join('\n').trim();
            }
            console.log('Test 3 parts:', key, guide, sectionValue)
            section = addCustomSection(key, guide, sectionValue);
        }

        if (section) {
            const checkbox = section.closest('.section-wrapper').querySelector('.section-checkbox');
            const guideInput = section.querySelector('.section-guide') || section.querySelector('input[type="text"]');
            const textarea = section.querySelector('textarea');
            const nameInput = section.querySelector('.section-name');

            if (checkbox) {
                checkbox.checked = true;
                toggleSection(checkbox);
            }

            if (nameInput) {
                nameInput.value = key;
            }

            if (guideInput && textarea) {
                let value = (rule[key] || '').trim();
                let guide = '';

                // Check if the first line ends with a colon
                const lines = value.split('\n');
                if (lines[0].endsWith(':') || lines[0].endsWith('：')) {
                    guide = lines[0];
                    value = lines.slice(1).join('\n').trim();
                }

                guideInput.value = guide;
                textarea.value = value;

                highlightElement(guideInput);
                highlightElement(textarea);
            }
        }
    });

    // Reorder sections
    const sectionContainer = document.getElementById('sortable-sections');
    const systemSection = document.getElementById('system');
    if (systemSection) {
        sectionContainer.insertBefore(systemSection.closest('.section-wrapper'), sectionContainer.firstChild);
    }
    order.forEach(key => {
        if (key !== 'system' && key !== 'response') {
            const section = document.getElementById(key) || document.querySelector(`.custom-section[data-name="${key}"]`);
            if (section) {
                sectionContainer.appendChild(section.closest('.section-wrapper'));
            }
        }
    });
    const responseSection = document.getElementById('response');
    if (responseSection) {
        sectionContainer.appendChild(responseSection.closest('.section-wrapper'));
    }

    // Update commit ID visibility
    updateCommitInputs();

    // Update confirm components visibility
    updateConfirmComponents();

    saveFormData();

    // Update URL anchor
    window.location.hash = rule.filename;
}

function resetTemplateDropdown() {
    const dropdown = document.getElementById('template-dropdown');
    if (dropdown) {
        dropdown.value = '';  // 将下拉框重置为"选择模板"选项
    }
}

export function updateConfirmComponents() {
    const confirmCheckbox = document.getElementById('confirm');
    const confirmPromptContainer = document.getElementById('confirm-prompt-row');
    
    if (confirmCheckbox && confirmPromptContainer) {
        confirmPromptContainer.style.display = confirmCheckbox.checked ? 'flex' : 'none';
    }
}