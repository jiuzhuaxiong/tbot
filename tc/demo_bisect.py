"""
Demonstration of a git bisect
"""
import tbot

@tbot.testcase
def demo_bisect(tb: tbot.TBot) -> None:
    """ Demonstrate git bisecting """
    repo = tb.config["tbot.workdir"] / "uboot-bisect-demo"
    tb.call("uboot_checkout", builddir=repo)

    # Add 4 bad commits
    for i in range(0, 4):
        tb.shell.exec0(f"cd {repo}; echo 'asdfghjkl{i}' >>common/autoboot.c")

        string = "very ".join(map(lambda x: "", range(0, i + 1)))
        tb.shell.exec0(f"cd {repo}; git add common/autoboot.c")
        tb.shell.exec0(f"cd {repo}; git commit -m 'A {string}bad commit'")

    bad = tb.call("git_bisect",
                  gitdir=repo,
                  good="HEAD~10",
                  and_then="uboot_build",
                  params={"builddir": repo},
                 )

    bad_commit = tb.shell.exec0(f"cd {repo}; git show {bad}")
    tb.log.log_msg(f"BAD COMMIT:\n{bad_commit}")