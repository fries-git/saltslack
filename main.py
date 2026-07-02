import os
import dotenv as env
import requests
import json

env.load_dotenv()
tracked = []
latestsave = []
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
    user_id = body["user_id"]
    user_info = app.client.users_info(user=user_id)

    if user_info["ok"]:
        user_name = user_info["user"]["name"]
        print(f"User {user_name} is now tracking repository: {repo}")

    else:
        respond(f"Failed to retrieve user info for user ID: {user_id}")
        print(f"Failed to retrieve user info for user ID: {user_id}")
        return
    
    if not repo:
        respond("Please provide a repository link to track.")
        return
    
    if not is_valid_repo(repo):
        respond(f"`{repo}` is not a valid GitHub repository.")
        return
    
    else:
        respond(f"Tracking repository: {repo}")
        tracked.append({
            "repo": repo,
            "user": user_id  # store the Slack user ID, not the username
        })

@app.command("/untrackrepo")
def command(ack, body, respond):
    ack()
    repo = normalize_repo(body["text"].strip())
    user_id = body["user_id"]
    
    if not repo:
        respond("Please provide a repository link to untrack.")
        return
    
    for item in tracked:
        if item["repo"] == repo and item["user"] == user_id:
            tracked.remove(item)
            respond(f"Stopped tracking repository: {repo}")
            return
    
    respond(f"You are not tracking repository: {repo}")

@app.command("/updaterepos")
def command(ack, body, respond):
    ack()
    checkrepos()

@app.event("message")
def handle_message_events(body, logger):
    logger.info(body)

latestcommits = {}

def checkrepo(repo):
    url = f"https://api.github.com/repos/{repo}/commits"
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        return None
    data = response.json()
    if not data:
        return None
    latest = data[0]
    sha = latest["sha"]
    if repo not in latestcommits:
        latestcommits[repo] = sha
        return None  # First run, don't notify
    if latestcommits[repo] != sha:
        latestcommits[repo] = sha
        return (
            f"New commit detected in {repo}\n"
            f"{latest['commit']['message']}\n"
            f"{latest['html_url']}"
        )

    return None

def checkrepos():
    for item in tracked:
        update = checkrepo(item["repo"])

        if update:
            app.client.chat_postMessage(
                channel=item["user"],
                text=update
            )

checkrepos()
handler = SocketModeHandler(app, str(xapptoken))
handler.start()