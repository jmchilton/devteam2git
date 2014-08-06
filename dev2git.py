# TODO: Try to merge suites into a single directory in github.
# TODO(?): Preserve history.
import argparse
from fabric.api import local
from fabric.context_managers import lcd
from bioblend import toolshed

TOOLSHED = "https://toolshed.g2.bx.psu.edu"
OWNER = "devteam"




def list():
    repos = dev_repos()
    map( summarize_repo, repos )

def build():
    repos = dev_repos()
    execute("rm -rf repo")
    execute("mkdir repo")
    with lcd("repo"):
        execute("mkdir tools suites packages")
        execute("git init .")
        for repo in dev_repos():
            repo_type = repo[ "type" ]
            if repo_type == "tool_dependency_definition":
                clone_package(repo)
            elif repo_type == "unrestricted":
                clone_tool(repo)
            elif repo_type == "repository_suite_definition":
                clone_suite(repo)
            else:
                print "WARN: Unhandled repo type %s" % repo_type

def clone_package(repo):
    with lcd("packages"):
        clone_repo(repo)


def clone_tool(repo):
    with lcd("tools"):
        clone_repo(repo)        


def clone_suite(repo):
    with lcd("suites"):
        clone_repo(repo)


def dev_repos():
    ts = toolshed.ToolShedInstance(url=TOOLSHED)
    repos = ts.repositories.get_repositories()
    repos = [r for r in repos if r["owner"] == OWNER]
    return repos


def clone_repo(repo):
    execute("hg clone %s/repos/%s/%s" % (TOOLSHED, repo["owner"], repo["name"]))
    execute("rm -rf .hg")


def summarize_repo(repo):
    print "name: %s, type %s, id %s" % ( repo[ "name" ], repo["type"], repo["id"] )


def execute(cmd):
    local(cmd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', metavar='action', type=str)
    args = parser.parse_args()
    eval(args.action)()


if __name__ == "__main__":
    main()
