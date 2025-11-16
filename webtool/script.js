// script.js

import { showTooltip, hideTooltip, showToast, showNewRuleDialog, showDetailDialog, closeDetailDialog, showRepositoryInfoDialog, showErrorDialog } from './dialog.js';
import { executeCodeReview, refresh_rules, savePromptToFile, clearForm, generatePrompt, initializeSections, updateConfirmComponents } from './section_action.js';
import { toggleSection, addCustomSection, updateTemplateDropdown, loadFormData, saveFormData, addRuleToDropdown, updateSectionVisibility, initializeDragAndDrop, updateCommitInputs } from './section.js';
import { initializeResultArea } from './result.js';
import { showHelpDialog, closeHelpDialog } from './help.js';
import { vars, typeMapping } from './variable.js';
import { getUrlAnchor, is_ready, escapeHtml } from './util.js';
import { fetchYamlResources } from './custom.js';

// 获取当前session
function getCurrentSession() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('session') || 'default';
}

// 使用session前缀保存到LocalStorage
function setLocalStorageWithSession(key, value) {
    const session = getCurrentSession();
    localStorage.setItem(`${session}_${key}`, JSON.stringify(value));
}

// 从LocalStorage获取带session前缀的数据
function getLocalStorageWithSession(key) {
    const session = getCurrentSession();
    const value = localStorage.getItem(`${session}_${key}`);
    return value ? JSON.parse(value) : null;
}

// 根据选择的模型更新 Extended Thinking 配置的可见性
function updateThinkingVisibility() {
    const modelSelect = document.getElementById('model-select');
    const enableThinkingRow = document.querySelector('.input-row:has(#enable-thinking)');
    const thinkingBudgetRow = document.getElementById('thinking-budget-row');

    if (!modelSelect || !enableThinkingRow) return;

    const selectedModel = modelSelect.value;

    // 支持 Extended Thinking 的模型列表
    const thinkingSupportedModels = [
        'claude3.7-sonnet',
        'claude4-opus',
        'claude4-opus-4.1',
        'claude4-sonnet',
        'claude4.5-sonnet',
        'claude4.5-haiku'
    ];

    const supportsThinking = thinkingSupportedModels.includes(selectedModel);

    // 显示或隐藏 Extended Thinking 配置
    if (supportsThinking) {
        enableThinkingRow.style.display = 'flex';
        // 如果启用了 thinking，也显示 budget 输入框
        const enableThinkingCheckbox = document.getElementById('enable-thinking');
        if (enableThinkingCheckbox && enableThinkingCheckbox.checked && thinkingBudgetRow) {
            thinkingBudgetRow.style.display = 'flex';
        }
    } else {
        enableThinkingRow.style.display = 'none';
        if (thinkingBudgetRow) {
            thinkingBudgetRow.style.display = 'none';
        }
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // 调用新增的函数
    const addSectionBtn = document.getElementById('add-section');
    const leftPanel = document.getElementById('left-panel');
    const typeRadios = document.querySelectorAll('input[name="type"]');
    const commitWhole = document.getElementById('commit-whole');
    const commitRange = document.getElementById('commit-range');
    const viewPromptBtn = document.getElementById('view-prompt');
    const savePromptBtn = document.getElementById('save-prompt');
    const executeReviewBtn = document.getElementById('execute-review');
    const sortableSections = document.getElementById('sortable-sections');
    
    // Clear button
    const clearBtn = document.getElementById('clear-btn');
    clearBtn.addEventListener('click', function() {
        clearForm();
    });

    const helpBtn = document.getElementById('help-btn');
    const exportBtn = document.getElementById('export-btn');
    const templateDropdown = document.getElementById('template-dropdown');

    // Access Token Input
    const toggleAccessToken = document.getElementById('toggle-access-token-display');
    const accessTokenDisplay = document.getElementById('access-token-display');

    if (toggleAccessToken && accessTokenDisplay) {
        toggleAccessToken.addEventListener('click', function() {
            const type = accessTokenDisplay.getAttribute('data-type') === 'password' ? 'text' : 'password';
            accessTokenDisplay.setAttribute('data-type', type);
            accessTokenDisplay.textContent = type === 'password' ? '••••••••' : accessTokenDisplay.getAttribute('data-value');
            this.textContent = type === 'password' ? '👁️' : '🔒';
        });
    }
    
    // API KEY checkbox
    const apiKeyInput = document.getElementById('api-key');
    const enableApiKeyCheckbox = document.getElementById('enable-api-key');

    enableApiKeyCheckbox.addEventListener('change', function() {
        apiKeyInput.disabled = !this.checked;
        if (!this.checked) {
            apiKeyInput.value = '';
            apiKeyInput.placeholder = '不需要填写API Key';
        } else {
            apiKeyInput.value = '';
            apiKeyInput.placeholder = '请填写API Key';
            apiKeyInput.focus();
        }
    });
    apiKeyInput.disabled = true;
    apiKeyInput.placeholder = '不需要填写API Key';

    // 添加提示功能
    const helpIcons = document.querySelectorAll('.help-icon');
    helpIcons.forEach(icon => {
        icon.addEventListener('mouseenter', showTooltip);
        icon.addEventListener('mouseleave', hideTooltip);
    });
    helpBtn.addEventListener('click', function() {
        showHelpDialog();
    });

    exportBtn.addEventListener('click', function() {
        const exportData = generatePromptYaml();
        const yamlString = jsyaml.dump(exportData);
        navigator.clipboard.writeText(yamlString).then(() => {
            showToast('配置已复制到剪贴板');
        }).catch(err => {
            console.error('复制失败:', err);
            showToast('复制失败');
        });
    });    
    
    templateDropdown.addEventListener('change', function() {
        const selectedIndex = this.value;
        if (selectedIndex !== '') {
            try {
                const selectedType = document.querySelector('input[name="type"]:checked')?.value || 'all';
                const serverType = typeMapping[selectedType] || selectedType;
                const selectedTemplate = vars.templateData[serverType][parseInt(selectedIndex)];
                initializeSections(selectedTemplate);
            } catch (error) {
                console.error('Error applying template:', error);
                showToast('应用模板时发生错误');
            }
        }
    });

    typeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            updateTemplateDropdown(this.value);
            updateCommitInputs();
            saveFormData();
        });
    });

    // 初始化模板下拉框
    updateTemplateDropdown('all');

    // Drag and drop functionality
    initializeDragAndDrop(sortableSections);

    document.querySelectorAll('.section-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', () => toggleSection(checkbox));
    });

    addSectionBtn.addEventListener('click', () => addCustomSection());

    document.querySelectorAll('input, textarea').forEach(input => {
        input.addEventListener('input', saveFormData);
    });

    viewPromptBtn.addEventListener('click', () => {
        const prompt = generatePrompt();
        showDetailDialog("提示词", prompt, [
            {
                enabled: true,
                label: '关闭',
                action: closeDetailDialog
            },
            {
                enabled: true,
                label: '复制内容',
                action: () => {
                    navigator.clipboard.writeText(prompt).then(() => {
                        showToast('提示词已复制到剪贴板');
                    }).catch(err => {
                        console.error('复制失败:', err);
                        showToast('复制失败');
                    });
                }
            }
        ]);
    });

    savePromptBtn.addEventListener('click', savePromptToFile);

    executeReviewBtn.addEventListener('click', executeCodeReview);

    // Make section titles draggable
    document.querySelectorAll('#sortable-sections .section-wrapper').forEach(wrapper => {
        const title = wrapper.querySelector('h2');
        if (!wrapper.closest('#repository-config') && !wrapper.closest('#rules-config') && !wrapper.closest('#output-requirements') && !wrapper.closest('#system')) {
            title.draggable = true;
            title.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', '');  // Required for Firefox
            });
        }
    });

    loadFormData();

    // Model select change event - save form data and update thinking visibility
    document.getElementById('model-select').addEventListener('change', function() {
        updateThinkingVisibility();
        saveFormData();
    });

    // 启动时显示Help Dialog
    const savedShowHelpOnStartup = getLocalStorageWithSession('showHelpOnStartup');
    let showHelpOnStartup;
    if (savedShowHelpOnStartup === null) {
        showHelpOnStartup = true;
    } else {
        showHelpOnStartup = savedShowHelpOnStartup === 'true';
    }
    if (showHelpOnStartup) {
        showHelpDialog();
    }

    // 添加刷新规则按钮的事件监听器
    const refreshRulesBtn = document.getElementById('refresh-rules');
    if (refreshRulesBtn) {
        refreshRulesBtn.addEventListener('click', refresh_rules);
    }

    // 添加新规则按钮的事件监听器
    const newRuleBtn = document.getElementById('new-rule');
    if (newRuleBtn) {
        newRuleBtn.addEventListener('click', () => {
            showNewRuleDialog((ruleName, fileName) => {
                addRuleToDropdown(ruleName, fileName);
            });
        });
    }

    // 检查 代码仓库配置状态并显示提示信息
    updateSectionVisibility();

    // 加载template yamls
    fetchYamlResources().then(() => {
        // 初始化模板下拉框
        const initialType = document.querySelector('input[name="type"]:checked')?.value || 'all';
        updateTemplateDropdown(initialType);
    });

    // 如果 代码仓库信息已配置，触发 refresh_rules
    if (is_ready()) {
        refresh_rules();
    }

    // 添加规则下拉框的change事件监听器
    const rulesDropdown = document.getElementById('rules-dropdown');
    if (rulesDropdown) {
        rulesDropdown.addEventListener('change', function() {
            const selectedRule = this.value;
            if (selectedRule) {
                const selectedRuleData = vars.globalRules.find(rule => rule.filename === selectedRule);
                if (selectedRuleData) {
                    initializeSections(selectedRuleData);
                }
                // 更新 URL 的 anchor
                window.location.hash = selectedRule;
                saveFormData();
            }
        });
    }

    // 添加编辑按钮的事件监听器
    const editRepositoryInfoBtn = document.getElementById('edit-repository-info');
    if (editRepositoryInfoBtn) {
        editRepositoryInfoBtn.addEventListener('click', showRepositoryInfoDialog);
    }

    // 初始化结果区域
    initializeResultArea();

    // 监听Repository配置的变化
    const repositoryUrlDisplay = document.getElementById('repository-url-display');
    const repositoryBranchDisplay = document.getElementById('repository-branch-display');

    const observer = new MutationObserver(() => {
        updateSectionVisibility();
    });

    observer.observe(repositoryUrlDisplay, { childList: true, characterData: true, subtree: true });
    observer.observe(accessTokenDisplay, { attributes: true, attributeFilter: ['data-value'] });
    observer.observe(repositoryBranchDisplay, { childList: true, characterData: true, subtree: true });

    // 更新触发事件单选按钮的事件监听器
    const triggerEventRadios = document.querySelectorAll('input[name="trigger-event"]');
    triggerEventRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            saveFormData();
        });
    });

    // Extended Thinking checkbox 事件监听器
    const enableThinkingCheckbox = document.getElementById('enable-thinking');
    const thinkingBudgetRow = document.getElementById('thinking-budget-row');
    if (enableThinkingCheckbox && thinkingBudgetRow) {
        enableThinkingCheckbox.addEventListener('change', function() {
            thinkingBudgetRow.style.display = this.checked ? 'flex' : 'none';
            saveFormData();
        });
    }

    // Thinking budget input 事件监听器
    const thinkingBudgetInput = document.getElementById('thinking-budget');
    if (thinkingBudgetInput) {
        thinkingBudgetInput.addEventListener('input', saveFormData);
    }

    // 检查 URL 中是否存在 anchor
    const anchor = getUrlAnchor();
    if (anchor) {
        if (rulesDropdown) {
            const option = Array.from(rulesDropdown.options).find(opt => opt.value === anchor);
            if (option) {
                rulesDropdown.value = anchor;
                const selectedRuleData = vars.globalRules.find(rule => rule.filename === anchor);
                if (selectedRuleData) {
                    initializeSections(selectedRuleData);
                }
            }
        }
    }

    // 添加刷新数据按钮的事件监听器
    const refreshDataBtn = document.getElementById('refresh-data');
    if (refreshDataBtn) {
        refreshDataBtn.addEventListener('click', refresh_rules);
    }

    // 页面加载时调用 updateSectionVisibility
    updateSectionVisibility();

    // 页面加载时更新 Extended Thinking 可见性
    updateThinkingVisibility();

    // 监听 Endpoint 和 代码仓库配置的变化
    const endpointInput = document.getElementById('endpoint');
    endpointInput.addEventListener('blur', () => {
        if (is_ready()) {
            refresh_rules();
        } else {
            updateSectionVisibility();
        }
    });

    const repositoryConfigObserver = new MutationObserver(() => {
        if (is_ready()) {
            refresh_rules();
        } else {
            updateSectionVisibility();
        }
    });

    repositoryConfigObserver.observe(repositoryUrlDisplay, { childList: true, characterData: true, subtree: true });
    repositoryConfigObserver.observe(accessTokenDisplay, { attributes: true, attributeFilter: ['data-value'] });
    repositoryConfigObserver.observe(repositoryBranchDisplay, { childList: true, characterData: true, subtree: true });

    // 初始化commit输入框显示状态
    updateCommitInputs();

    // 初始化二次检查相关控件
    updateConfirmComponents();

    // 添加二次检查复选框的事件监听器
    const confirmCheckbox = document.getElementById('confirm');
    if (confirmCheckbox) {
        confirmCheckbox.addEventListener('change', updateConfirmComponents);
    }

    // 在所有资源加载完成后，显示body
    window.addEventListener('load', function() {
        document.body.style.visibility = 'visible';
    });
});

export { getCurrentSession, setLocalStorageWithSession, getLocalStorageWithSession };