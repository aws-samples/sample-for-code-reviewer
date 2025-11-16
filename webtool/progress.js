// progress.js

import { formatDate, formatDuration } from './util.js';
import { showToast } from './dialog.js';
import { switchTab } from './result.js';
import { vars } from './variable.js';

export function updateReportTimer() {
    const elapsedSeconds = Math.floor((Date.now() - vars.reportStartTime) / 1000);
    const statusContainer = document.getElementById('status-container');
    if (statusContainer) {
        statusContainer.textContent = `正在获取报告...已过去${elapsedSeconds}秒`;
    }
}

export function renderJsonMessage(jsonData) {
    const progressContent = document.getElementById('progress-content');
    if (!progressContent) return;

    // 保留状态容器
    let statusContainer = document.getElementById('status-container');
    if (!statusContainer) {
        statusContainer = document.createElement('div');
        statusContainer.id = 'status-container';
        progressContent.insertBefore(statusContainer, progressContent.firstChild);
    }

    // 检查 tasks 是否为 null 或空数组
    const isTasksEmpty = !jsonData.tasks || jsonData.tasks.length === 0;

    // 更新摘要
    if (isTasksEmpty) {
        updateSummary("正在获取代码仓库信息");
    } else {
        updateSummary(jsonData.summary);
    }

    // 任务时间信息元素
    let taskTimeInfo = document.getElementById('task-time-info');

    if (!isTasksEmpty) {
        jsonData.tasks.sort((a, b) => a.number - b.number);

        // 计算任务时间信息
        let earliestStart = Infinity;
        let latestEnd = -Infinity;
        jsonData.tasks.forEach((task) => {
            if (task.bedrock_start_time) {
                earliestStart = Math.min(earliestStart, new Date(task.bedrock_start_time).getTime());
            }
            if (task.bedrock_end_time) {
                latestEnd = Math.max(latestEnd, new Date(task.bedrock_end_time).getTime());
            }
        });

        // 创建或更新任务时间信息元素
        if (!taskTimeInfo) {
            taskTimeInfo = document.createElement('div');
            taskTimeInfo.id = 'task-time-info';
            progressContent.insertBefore(taskTimeInfo, progressContent.firstChild.nextSibling);
        }

        if (earliestStart !== Infinity && latestEnd !== -Infinity) {
            const totalDuration = latestEnd - earliestStart;
            const formattedDuration = formatDuration(totalDuration);

            taskTimeInfo.innerHTML = `
                <h3>任务时间信息</h3>
                <p>任务最早开始时间: ${formatDate(new Date(earliestStart))}</p>
                <p>任务最晚结束时间: ${formatDate(new Date(latestEnd))}</p>
                <p>总任务执行时长: ${formattedDuration}</p>
            `;
        } else {
            taskTimeInfo.innerHTML = '<p>暂无任务时间信息</p>';
        }

        jsonData.tasks.forEach((task) => {
            updateOrCreateTaskElement(task);
        });

        // 移除不再存在的任务
        const existingTasks = progressContent.querySelectorAll('.task');
        existingTasks.forEach(taskElement => {
            const taskNumber = taskElement.getAttribute('data-task-number');
            if (!jsonData.tasks.some(task => task.number.toString() === taskNumber)) {
                progressContent.removeChild(taskElement);
            }
        });
    } else {
        // 如果没有任务数据，移除任务时间信息和所有任务元素
        if (taskTimeInfo) {
            taskTimeInfo.remove();
        }
        const existingTasks = progressContent.querySelectorAll('.task');
        existingTasks.forEach(taskElement => {
            progressContent.removeChild(taskElement);
        });
    }
}

export function updateOrCreateTaskElement(task) {
    const progressContent = document.getElementById('progress-content');
    let taskElement = document.querySelector(`.task[data-task-number="${task.number}"]`);
    
    if (!taskElement) {
        taskElement = document.createElement('div');
        taskElement.className = 'task';
        taskElement.setAttribute('data-task-number', task.number);
        taskElement.innerHTML = `<h4>Task ${task.number}</h4>`;
        
        // 找到正确的插入位置
        let insertAfter = null;
        const existingTasks = progressContent.querySelectorAll('.task');
        for (let existing of existingTasks) {
            const existingNumber = parseInt(existing.getAttribute('data-task-number'));
            if (existingNumber < task.number) {
                insertAfter = existing;
            } else {
                break;
            }
        }
        
        if (insertAfter) {
            insertAfter.insertAdjacentElement('afterend', taskElement);
        } else {
            // 如果没有找到合适的位置，插入到第一个任务之前
            const firstTask = progressContent.querySelector('.task');
            if (firstTask) {
                progressContent.insertBefore(taskElement, firstTask);
            } else {
                progressContent.appendChild(taskElement);
            }
        }
    }

    // 定义新的字段顺序
    const fields = [
        {key: 'succ', label: '是否成功', multiline: false},
        {key: 'bedrock_model', label: '模型', multiline: false},
        {key: 'bedrock_start_time', label: 'Bedrock Start', multiline: false},
        {key: 'bedrock_end_time', label: 'Bedrock End', multiline: false},
        {key: 'bedrock_timecost', label: 'Bedrock Timecost', multiline: false},
        {key: 'bedrock_system', label: '系统提示词', multiline: true},
        {key: 'bedrock_prompt', label: '用户提示词', multiline: true},
        {key: 'bedrock_payload', label:'Bedrock Payload', multiline: true},
        {key: 'reasoning', label: 'Extended Thinking', multiline: true}
    ];
    
    fields.forEach(field => {
        // 只有当字段存在且不为空时才创建或更新
        if (task.hasOwnProperty(field.key) && task[field.key] !== null && task[field.key] !== undefined && task[field.key] !== '') {
            updateOrCreateFieldElement(taskElement, field, task);
        } else {
            // 如果字段不存在或为空，移除相应的元素（如果存在的话）
            const existingField = taskElement.querySelector(`.field[data-field="${field.key}"]`);
            if (existingField) {
                taskElement.removeChild(existingField);
            }
        }
    });

    updateOrCreateReplyElement(taskElement, task);

    // 只在 task.message 存在且不为空时显示错误信息
    if (task.message && task.message.trim() !== '') {
        updateOrCreateMessageElement(taskElement, task);
    } else {
        // 如果没有错误信息，移除可能存在的错误信息元素
        const errorElement = taskElement.querySelector('.field[data-field="error_message"]');
        if (errorElement) {
            taskElement.removeChild(errorElement);
        }
    }
}

export function updateOrCreateFieldElement(taskElement, field, task) {
    let fieldElement = taskElement.querySelector(`.field[data-field="${field.key}"]`);
    let value = '';

    if (field.key === 'succ') {
        value = task.succ ? 'true' : 'false';
    } else if (field.key === 'bedrock_payload') {
        try {
            const jsonPayload = JSON.parse(task[field.key]);
            value = JSON.stringify(jsonPayload, null, 4);
        } catch (error) {
            value = task[field.key] || '';
        }
    } else if (field.key === 'bedrock_timecost') {
        value = formatDuration(task[field.key]);
    } else if (field.key === 'bedrock_prompt') {
        try {
            const promptData = JSON.parse(task[field.key]);
            if (Array.isArray(promptData)) {
                value = formatPromptArray(promptData);
            } else {
                value = task[field.key] || '';
            }
        } catch (error) {
            value = task[field.key] || '';
        }
    } else {
        value = task[field.key] || '';
    }

    const isPlainText = ['succ', 'bedrock_model', 'bedrock_start_time', 'bedrock_end_time', 'bedrock_timecost'].includes(field.key);

    if (!fieldElement) {
        fieldElement = createFieldElement(field.label, value, field.multiline, field.key === 'bedrock_payload', isPlainText);
        fieldElement.setAttribute('data-field', field.key);
        taskElement.appendChild(fieldElement);
    } else {
        const valueElement = fieldElement.querySelector('input, textarea, .plain-text-value');
        if (valueElement) {
            if (valueElement.tagName === 'SPAN') {
                valueElement.textContent = value;
            } else {
                valueElement.value = value;
            }
        }
        
        if (!isPlainText) {
            const copyButton = fieldElement.querySelector('.copy-button');
            if (copyButton) {
                copyButton.style.display = 'inline-block';
                copyButton.onclick = () => {
                    navigator.clipboard.writeText(value).then(() => {
                        showToast('已复制到剪贴板');
                    }).catch(err => {
                        console.error('复制失败:', err);
                        showToast('复制失败');
                    });
                };
            }
        }
    }
}

function formatPromptArray(promptArray) {
    return promptArray.join('\n\n--------------------------------------------------\n\n');
}

export function updateOrCreateReplyElement(taskElement, task) {
    let replyElement = taskElement.querySelector('.field[data-field="bedrock_reply"]');
    let replyContent = '';

    if (task.result && task.result.trim() !== '') {
        try {
            const parsedResult = JSON.parse(task.result);
            if (parsedResult.content) {
                replyContent = typeof parsedResult.content === 'object' 
                    ? JSON.stringify(parsedResult.content, null, 2) 
                    : parsedResult.content;
            }
        } catch (error) {
            replyContent = task.result;
        }
    }

    if (replyContent) {
        if (!replyElement) {
            replyElement = createFieldElement('Bedrock响应', replyContent, true, false);
            replyElement.setAttribute('data-field', 'bedrock_reply');
            taskElement.appendChild(replyElement);
        } else {
            const textarea = replyElement.querySelector('textarea');
            if (textarea.value !== replyContent) {
                textarea.value = replyContent;
            }
        }
    } else {
        // 如果没有响应内容，移除响应元素（如果存在的话）
        if (replyElement) {
            taskElement.removeChild(replyElement);
        }
    }
}

export function updateOrCreateMessageElement(taskElement, task) {
    let messageElement = taskElement.querySelector('.field[data-field="error_message"]');
    let messageContent = task.message || '';

    try {
        const messageObj = JSON.parse(messageContent);
        messageContent = JSON.stringify(messageObj, null, 4);
    } catch (error) {
        // 如果不是 JSON 字符串，保持原样
    }

    if (!messageElement) {
        messageElement = createFieldElement('错误信息', messageContent, true, false);
        messageElement.setAttribute('data-field', 'error_message');
        taskElement.appendChild(messageElement);
    } else {
        const textarea = messageElement.querySelector('textarea');
        if (textarea.value !== messageContent) {
            textarea.value = messageContent;
        }
    }
}

export function createFieldElement(label, value, isMultiline = false, formatJson = false, isPlainText = false) {
    const fieldElement = document.createElement('div');
    fieldElement.className = 'field';
    fieldElement.style.display = 'flex';
    fieldElement.style.alignItems = 'flex-start';

    const labelElement = document.createElement('label');
    labelElement.textContent = label;
    labelElement.style.minWidth = '150px';
    labelElement.style.marginRight = '10px';

    if (formatJson && typeof value === 'string') {
        try {
            const jsonObj = JSON.parse(value);
            value = JSON.stringify(jsonObj, null, 2);
        } catch (error) {
            // 如果解析失败，保持原始字符串
        }
    }

    let valueElement;
    if (isPlainText) {
        valueElement = document.createElement('span');
        valueElement.textContent = value;
        valueElement.className = 'plain-text-value';
    } else {
        valueElement = isMultiline ? document.createElement('textarea') : document.createElement('input');
        valueElement.value = value;
        valueElement.readOnly = true;
        if (isMultiline) {
            valueElement.rows = 2;
        }
    }
    valueElement.style.flexGrow = '1';
    valueElement.style.marginRight = '5px';

    fieldElement.appendChild(labelElement);
    fieldElement.appendChild(valueElement);

    if (!isPlainText) {
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-button';
        copyButton.textContent = 'Copy';
        copyButton.style.flexShrink = '0';
        copyButton.onclick = () => {
            navigator.clipboard.writeText(value).then(() => {
                showToast('已复制到剪贴板');
            }).catch(err => {
                console.error('复制失败:', err);
                showToast('复制失败');
            });
        };
        fieldElement.appendChild(copyButton);
    }

    return fieldElement;
}

export function pollForReport(endpoint, requestId, apiKey) {
    let statusContainer = document.getElementById('status-container');
    let progressContent = document.getElementById('progress-content');
    
    if (!statusContainer) {
        statusContainer = document.createElement('div');statusContainer.id = 'status-container';
        progressContent?.appendChild(statusContainer);
    }
    
    if (!vars.reportTimer) {
        vars.reportTimer = setInterval(() => {
            const elapsedSeconds = Math.floor((Date.now() - vars.reportStartTime) / 1000);
            statusContainer.textContent = `正在获取报告...已过去${elapsedSeconds}秒`;
        }, 1000);}

    const codeReviewCommitId = document.getElementById('code-review-commit-id').value;

    getCodeReviewReport(endpoint, requestId, codeReviewCommitId, apiKey)
        .then(response => {
            if (response.status !== 200 || !response.data.succ) {
                throw new Error(JSON.stringify(response.data));
            }
            if (response.data.ready && response.data.url) {
                clearInterval(vars.reportTimer);
                vars.reportTimer = null;
                const reportFrame = document.getElementById('report-frame');
                
                if (reportFrame) {
                    // 检查 tasks 是否为空
                    if (!response.data.tasks || response.data.tasks.length === 0) {
                        // 如果 tasks 为空，使用 summary 作为进度信息
                        statusContainer.textContent = response.data.summary || '报告已准备就绪，但没有具体任务信息。';} else {
                        // 如果 tasks 不为空, 刷新summary 和 task sections
                        renderJsonMessage({
                            summary:response.data.summary,
                            tasks: response.data.tasks
                        });
                    }

                    setTimeout(() => {
                        reportFrame.src = `${response.data.url}`;
                        switchTab('report');
                    }, 1000);
                }
            } else {
                renderJsonMessage({
                    summary: response.data.summary || "正在获取代码仓库信息",
                    tasks: response.data.tasks || []
                });
                setTimeout(() => pollForReport(endpoint, requestId, apiKey), 1000);
            }
        })
        .catch(error => {
            clearInterval(vars.reportTimer);
            vars.reportTimer = null;
            displayReport({ error: error.message });
        });
}

export function updateSummary(summary) {
    let summaryElement = document.querySelector('.summary');
    if (summary) {
        if (!summaryElement) {
            summaryElement = document.createElement('div');
            summaryElement.className = 'summary';
            const progressContent = document.getElementById('progress-content');
            progressContent.insertBefore(summaryElement, progressContent.firstChild.nextSibling);
        }
        summaryElement.innerHTML = `<h3>Summary</h3><p>${summary}</p>`;
    } else if (summaryElement) {
        summaryElement.remove();
    }
}

export function getCodeReviewReport(endpoint, requestId, commitId, apiKey) {
    const headers = {
        'X-API-KEY': apiKey,
        'Content-Type': 'application/json'
    };
    return axios.get(`${endpoint}/result?request_id=${requestId}&commit_id=${commitId}`, { headers });
}