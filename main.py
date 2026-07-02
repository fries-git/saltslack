import os
import dotenv as env
import requests
import json

env.load_dotenv()
repos = []
latest_commits = {}
xapptoken = os.getenv("xapptoken")
xoxbtoken = os.getenv("xoxbtoken")

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

def normalize_repo(text):
    return text.strip().replace("https://github.com/", "").replace("github.com/", "").strip("/")

def is_valid_repo(repo):
    url = f"https://api.github.com/repos/{repo}"
    response = requests.get(url, timeout=10)
    return response.status_code == 200

app = App(token = str(xoxbtoken))

@app.command("/trackrepo")
def command(ack, body, respond):
    ack()
    repo = normalize_repo(body["text"].strip())
    if not repo:
        respond("Please provide a repository link to track.")
        return
    
    if not is_valid_repo(repo):
        respond(f"`{repo}` is not a valid GitHub repository.")
        return
    else:
        respond(f"Tracking repository: {repo}")
        repos.append(repo)

    user_id = body["user_id"]

@app.command("/updaterepos")
def command(ack, body, respond):
    ack()
    respond(checkrepos())

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

def checkrepos():
    updates = []

    for repo in repos:
        url = f"https://api.github.com/repos/{repo}/commits"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            updates.append(f"Error fetching commits for {repo}")
            continue

        data = response.json()
        if not data:
            continue

        latest_sha = data[0]["sha"]

        if repo not in latest_commits:
            latest_commits[repo] = latest_sha
            continue  # first time setup, no alert

        if latest_sha != latest_commits[repo]:
            latest_commits[repo] = latest_sha

            commit = data[0]
            updates.append(
                f"New commit in {repo}\n"
                f"Message: {commit['commit']['message']}\n"
                f"{commit['html_url']}"
            )

    return "\n\n".join(updates) if updates else "No new commits."

checkrepos()
handler = SocketModeHandler(app, str(xapptoken))
handler.start()