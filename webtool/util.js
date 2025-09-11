// util.js

export function formatDate(date) {
    return date.toISOString().replace('T', ' ').slice(0, -1);
}

export function formatDuration(milliseconds) {
    if (!milliseconds) return '';
    
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    
    const remainingMinutes = minutes % 60;
    const remainingSeconds = seconds % 60;
    const remainingMilliseconds = milliseconds % 1000;

    let result = '';
    if (hours > 0) result += `${hours}小时 `;
    if (remainingMinutes > 0) result += `${remainingMinutes}分钟 `;
    if (remainingSeconds > 0 || remainingMilliseconds > 0) {
        result += `${remainingSeconds}.${remainingMilliseconds.toString().padStart(3, '0')}秒`;
    }
    
    return result.trim();
}

export function getPathWithNamespace(repositoryUrl) {
    const url = new URL(repositoryUrl);
    let path = url.pathname.replace(/^\//, '');
    if (path.endsWith('.git')) {
        path = path.slice(0, -4);
    }
    return path;
}

export function setValueIfElementExists(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.value = value;
    }
}

export function highlightElement(element) {
    element.classList.add('highlight-animation');
    setTimeout(() => {
        element.classList.remove('highlight-animation');
    }, 2000);
}

export function getErrorMessage(errorType) {
    switch (errorType) {
        case 'AuthenticationError':
            return '身份认证失败，请检查AccessToken是否正确';
        case 'NotFound':
            return '资源不存在，请检查项目、分支、文件等地址是否不正确';
        case 'Forbidden':
            return '不允许的操作，请检查AccessToken权限是否足够，读取至少需要Reporter Role的read api权限。';
        case 'Unauthorized':
            return '身份认证失败，请检查AccessToken是否正确。';
        default:
            return '发生未知错误，请稍后重试。';
    }
}

export function getUrlAnchor() {
    const anchor = window.location.hash.slice(1);
    return anchor;
}

export function is_ready() {
    const endpoint = document.getElementById('endpoint')?.value;
    const repositoryUrl = document.getElementById('repository-url-display')?.textContent;
    const accessTokenDisplay = document.getElementById('access-token-display');
    const enableAccessToken = accessTokenDisplay?.getAttribute('data-type') === 'password';
    const accessToken = enableAccessToken ? accessTokenDisplay?.getAttribute('data-value') : '';

    return endpoint && repositoryUrl && (enableAccessToken ? accessToken : true);
}

export function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

export function get_dict_key(obj, value) {
    for (let key in obj) {
        if (obj[key] === value) {
            return key;
        }
    }
    return null;
}