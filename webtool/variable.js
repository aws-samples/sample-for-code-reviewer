// variable.js

export const vars = {
    formData: {
        endpoint: '',
        repositoryUrl: '',
        repositoryType: 'gitlab',
        apiKey: '',
        enableApiKey: false,
        accessToken: '',
        enableAccessToken: false,
        repositoryBranch: 'main',
        model: 'claude4.5-sonnet',
        targetFileList: '**',
        type: 'files',
        commitId: '',
        fromCommitId: '',
        toCommitId: '',
        systemPrompt: '',
        business: {
            guide: '',
            text: ''
        },
        sql: {
            guide: '',
            text: ''
        },
        requirement: {
            guide: '',
            text: ''
        },
        keypoint: {
            guide: '',
            text: ''
        },
        output: {
            guide: '',
            text: ''
        },
        other: {
            guide: '',
            text: ''
        },
        task: {
            guide: '',
            text: ''
        },
        response: {
            guide: '',
            text: ''
        },
        customSections: [],
        checkboxStates: {},
        sectionOrder: [],
        triggerEvent: 'merge',
        enableThinking: false,
        thinkingBudget: 2000
    },

    globalRules: [],

    currentMessage: '',
    reportStartTime: null,
    reportTimer: null,
    showHelpOnStartup: true,

    templateData: {
        all: [],
        single: [],
        diff: []
    },

    isRulesRefreshed: false
};

export const triggerEventMapping = {
    "push": "Push",
    "merge": "Merge Request"
};

export const typeMapping = {
    'whole': 'all',
    'files': 'single',
    'diffs': 'diff'
};

export const inbuiltSections = [
    'system',
    'business',
    'sql',
    'requirement',
    'keypoint',
    'output',
    'other',
    'task',
    'response'
];

export const nonCancelableSections = ['endpoint-config', 'repository-config', 'rules-config', 'toolbar'];