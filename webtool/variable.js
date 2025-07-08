// variable.js

export const vars = {
    formData: {
        endpoint: '',
        gitlabUrl: '',
        apiKey: '',
        enableApiKey: false,
        accessToken: '',
        enableAccessToken: false,
        gitlabBranch: 'main',
        model: 'claude3-sonnet',
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
        triggerEvent: 'merge'
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

export const nonCancelableSections = ['endpoint-config', 'gitlab-config', 'rules-config', 'toolbar'];