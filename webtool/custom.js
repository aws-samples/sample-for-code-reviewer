// custom.js

import { getPathWithNamespace, getErrorMessage, get_dict_key } from './util.js';
import { showInfoDialog, closeInfoDialog, showErrorDialog, showDialogMessage, hideDialogMessage } from './dialog.js';
import { vars, typeMapping } from './variable.js';

export function executeCodeReviewWithAxios(params) {
	const {
		endpoint,
		apiKey,
		gitlabUrl,
		type,
		commitId,
		fromCommitId,
		toCommitId,
		branch,
		targetFileList,
		prompt,
		model,
		systemPrompt,
		triggerEvent,
		ruleName,
		confirm,
		confirmPrompt
	} = params;
	
	const headers = {
		'X-API-KEY': apiKey,
		'Content-Type': 'application/json'
	};

	const pathWithNamespace = getPathWithNamespace(gitlabUrl);
	
	let data = {
		'invoker': 'webtool',
		'target_branch': branch,
		'previous_commit_id': fromCommitId,
		'web_url': gitlabUrl,
		'ref': branch,
		'path_with_namespace': pathWithNamespace,
		'prompt_user': prompt,
		'prompt_system': systemPrompt,
		'model': model,
		'target': targetFileList,
		'rule_name': ruleName,
		'confirm': confirm
	}
	if (confirm) {
		data['confirm_prompt'] = confirmPrompt || ''
	}

	const accessTokenDisplay = document.getElementById('access-token-display');
	const enableAccessToken = accessTokenDisplay.getAttribute('data-type') === 'password';
	const accessToken = accessTokenDisplay.getAttribute('data-value');

	if (enableAccessToken && accessToken) {
		data['private_token'] = accessToken;
	}

	if (type == 'whole') {
		data['mode'] = type;
		data['event_type'] = triggerEvent;
		data['commit_id'] = commitId;
	} else {
		data['mode'] = type;
		data['event_type'] = triggerEvent;
		data['commit_id'] = toCommitId;
		data['previous_commit_id'] = fromCommitId;
	}
	console.log('Test:', type, typeMapping, data['mode']);
	return axios.post(`${endpoint}`, data, { headers })
		.then(response => {
			if (response.data.commit_id && !data['commit_id']) {
				return {
					...response,
					newCommitId: response.data.commit_id
				};
			}
			return response;
		});
}

export function fetchRules(endpoint, gitlabUrl, accessToken, apiKey, branch) {
	showInfoDialog('信息提示', '正在刷新规则，请稍后');

	const headers = {
		'Content-Type': 'application/json'
	};

	if (accessToken) {
		headers['X-Gitlab-Token'] = accessToken;
	}

	if (apiKey) {
		headers['X-API-KEY'] = apiKey;
	}

	const pathWithNamespace = getPathWithNamespace(gitlabUrl);
	const repoUrl = gitlabUrl.replace(`/${pathWithNamespace}`, '');

	return axios.get(`${endpoint}/rules`, {
		headers,
		params: {
			project_id: pathWithNamespace,
			repo_url: repoUrl,
			target_branch: branch
		}
	}).then(response => {
		if (response.status !== 200 || !response.data.succ) {
			throw new Error(getErrorMessage(response.data.message));
		}

		const rulesDropdown = document.getElementById('rules-dropdown');
		rulesDropdown.innerHTML = '';

		response.data.data.forEach(rule => {
			const option = document.createElement('option');
			option.value = rule.filename;
			option.textContent = rule.name;
			rulesDropdown.appendChild(option);
		});

		vars.globalRules.length = 0;
		vars.globalRules.push(...response.data.data);
		return response.data.data;
	}).finally(() => {
		closeInfoDialog();
	});
}

export function getCodeReviewReport(endpoint, requestId, commitId, apiKey) {
	const headers = {
		'X-API-KEY': apiKey,
		'Content-Type': 'application/json'
	};
	return axios.get(`${endpoint}/result?request_id=${requestId}&commit_id=${commitId}`, { headers });
}

export function saveRule(endpoint, repoUrl, projectId, branch, content, accessToken, apiKey, selectedRule) {
	const data = {
		repo_url: repoUrl,
		project_id: projectId,
		target_branch: branch,
		content: content
	};

	const headers = {
		'Content-Type': 'application/json'
	};

	if (accessToken) {
		headers['X-Gitlab-Token'] = accessToken;
	}

	if (apiKey) {
		headers['X-API-KEY'] = apiKey;
	}

	showDialogMessage('正在保存提示词...', false);

	return axios.put(`${endpoint}/rules/${selectedRule}`, data, { headers })
		.then(response => {
			hideDialogMessage();
			return response.data || {}
		})
}

export function fetchYamlResources() {
	const domain = ''
	const yamlFiles = ['template.all.yaml', 'template.diff.yaml', 'template.single.yaml'];
	const promises = yamlFiles.map(file => 
		axios.get(domain + file)
			.then(response => {
				let result = jsyaml.load(response.data);
				console.log('Load ', file, ':', result)
				return { [file.split('.')[1]]: result.rules || [] };
			})
			.catch(error => {
				console.error(`Error fetching ${file}:`, error);
				return { [file.split('.')[1]]: [] };
			})
	);

	return Promise.all(promises)
		.then(results => {
			const combinedResult = Object.assign({}, ...results);
			vars.templateData = combinedResult;
			return combinedResult;
		});
}