from fabric.api import local, prefix, cd, run, env, lcd

env.hosts = ['orin.kylewm.com']

REMOTE_PATH = '/srv/www/kylewm.com/woodwind'


def commit():
    local("git add -p")
    local("git diff-index --quiet HEAD || git commit")


def push():
    local("git push origin master")


def pull():
    with cd(REMOTE_PATH):
        run("git pull origin master")
        run("git submodule update")


def restart():
    with cd(REMOTE_PATH):
        with prefix("source venv/bin/activate"):
            run("pip install -r requirements.txt")
            run("supervisorctl restart ww:*")


def deploy():
    commit()
    push()
    pull()
    restart()
