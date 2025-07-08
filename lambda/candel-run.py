import re, codelib


def run():
    event = dict(
        repo_url='http://gitlab.teonbox.com/pub/account-book',
        project_id='pub/account-book',
    )
    repo_context = codelib.init_repo_context(event)
    project = repo_context.get('project')
    print(project.name)

    commit_id1 = '3c9f36c3e854fed2bc9bee53ae8fda94d2528e9a'
    commit_id2 = '3ccb8b71e99ff08c8e82938aa5820f7671198976'
    res = codelib.get_involved_files(repo_context, commit_id2, commit_id1)
    print('rs:', res)
    # commits = project.commits.list(ref_name='main', since=commit_id1, until=commit_id2)
    commits = project.commits.list(ref_name=f'{commit_id1}..{commit_id2}')
    print('COmmits:')
    for commit in commits:
        diff = commit.diff()
        print(diff)

run()