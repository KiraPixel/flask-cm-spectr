from jira import JIRA


class JiraConnector:
    def __init__(self, url, username, password):
        try:
            print('JiraConnector | Trying to connect to JIRA...')
            self.jira = JIRA(url, basic_auth=(username, password))
            print('JiraConnector | Connected to JIRA')
        except Exception as e:
            print(f'JiraConnector | Failed to connect to JIRA: {e}')

    def search(self, title):
        jql = f'summary ~ "{title}"order by lastViewed DESC'
        issues = self.jira.search_issues(jql, maxResults=1)
        return issues

    def create_alert(self, title, description, project, equipment_type, obj_name):
        issue_dict = {
            'project': {'key': project},
            'summary': title,
            'description': description,
            'issuetype': {'name': 'Инцидент'},
            'customfield_10301': {'value': equipment_type},
            'customfield_10302': obj_name,
        }
        print(issue_dict)
        new_issue = self.jira.create_issue(fields=issue_dict)
        print(f'JiraConnector | Created issue: {new_issue}')

    def add_comment_to_issue(self, issue_key, comment):
        self.jira.add_comment(issue_key, comment)
        print(f'JiraConnector | Added comment to issue {issue_key}')

    def close_issue(self, issue_key):
        self.jira.transition_issue(issue_key, "Готово")
        print(f'JiraConnector | Close Issue  {issue_key}')
