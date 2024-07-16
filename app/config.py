import json

with open('config.json', 'r') as f:
    config = json.load(f)

with open('config_jira.json', 'r') as f:
    jira_config = json.load(f)