// help.js

let currentPage = 1;
const totalPages = 2;

function getSessionId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('session') || 'default';
}

export function showHelpDialog() {
    const helpDialogOverlay = document.getElementById('help-dialog-overlay');
    if (!helpDialogOverlay) {
        console.error("Cannot find element with id 'help-dialog-overlay'");
        return;
    }
    helpDialogOverlay.style.display = 'flex';

    const helpPages = document.querySelectorAll('.help-page');
    const prevButton = document.getElementById('prev-page');
    const nextButton = document.getElementById('next-page');
    const pageIndicator = document.getElementById('page-indicator');
    const navigationContainer = document.createElement('div');
    navigationContainer.className = 'help-navigation';

    if (!prevButton || !nextButton || !pageIndicator) {
        console.error("Cannot find one or more navigation elements");
        return;
    }

    function updatePage() {
        helpPages.forEach((page, index) => {
            if (page) {
                page.style.display = index + 1 === currentPage ? 'block' : 'none';
            } else {
                console.error(`Help page at index ${index} is undefined`);
            }
        });
        pageIndicator.textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页`;
        prevButton.disabled = currentPage === 1;
        
        if (currentPage === totalPages) {
            nextButton.textContent = '关闭';
        } else {
            nextButton.textContent = '下一页';
        }
    }

    function resetDialog() {
        currentPage = 1;
        updatePage();
    }

    function closeDialog() {
        helpDialogOverlay.style.display = 'none';
        resetDialog();
    }

    prevButton.onclick = () => {
        if (currentPage > 1) {
            currentPage--;
            updatePage();
        }
    };

    nextButton.onclick = () => {
        if (currentPage < totalPages) {
            currentPage++;
            updatePage();
        } else {
            closeDialog();
        }
    };

    helpDialogOverlay.onclick = (event) => {
        if (event.target === helpDialogOverlay) {
            closeDialog();
        }
    };

    // 创建新的导航容器
    const dialogButtons = document.querySelector('.dialog-buttons');
    navigationContainer.appendChild(prevButton);
    navigationContainer.appendChild(pageIndicator);
    navigationContainer.appendChild(nextButton);
    dialogButtons.innerHTML = '';
    dialogButtons.appendChild(navigationContainer);

    resetDialog();

    const showOnStartupCheckbox = document.getElementById('show-help-on-startup');
    const sessionId = getSessionId();
    const showHelpOnStartup = localStorage.getItem(`${sessionId}_showHelpOnStartup`) !== 'false';
    showOnStartupCheckbox.checked = showHelpOnStartup;
    
    showOnStartupCheckbox.addEventListener('change', function() {
        localStorage.setItem(`${sessionId}_showHelpOnStartup`, this.checked.toString());
    });
}

export function closeHelpDialog() {
    const helpDialogOverlay = document.getElementById('help-dialog-overlay');
    if (helpDialogOverlay) {
        helpDialogOverlay.style.display = 'none';
    }
}
