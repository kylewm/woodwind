from fabric.api import local, prefix, cd, run, env, lcd, sudo

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


def push_remote():
    with cd(REMOTE_PATH):
        run("git add -p")
        run("git diff-index --quiet HEAD || git commit")
        run("git push origin master")


def restart():
    with cd(REMOTE_PATH):
        with prefix("source venv/bin/activate"):
            run("pip install --upgrade -r requirements.txt")
    sudo("restart woodwind")
    sudo("restart woodwind-tornado")


def deploy():
    commit()
    push()
    pull()
    restart()
