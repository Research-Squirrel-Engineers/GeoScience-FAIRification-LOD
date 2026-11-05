"""clean_gh_pages.py - remove the old SPARQL Unicorn pages from the root of the branch gh-pages.

Since the move to /semweb/ the root of gh-pages holds only docu/, semweb/ and index.html. Everything else there is the
output of earlier Unicorn runs (about 15 000 entries). The script builds the new root tree with `git mktree` from the
entries that stay and commits it. It uses no index and no checkout: the branch holds names that Windows cannot write
(api/3/action/group_list?all_fields=true), and Git for Windows refuses even to read them into an index. The working
copy of the repository is not touched.

    py tools/clean_gh_pages.py            # dry run: prints what would stay and what would go
    py tools/clean_gh_pages.py --apply    # makes the commit; the push command is printed

Run it from the repository root when no workflow is writing to gh-pages (check the Actions tab).
"""
import argparse
import os
import subprocess
import sys

KEEP = {"docu", "semweb", "index.html", ".nojekyll", "CNAME"}
BRANCH = "origin/gh-pages"


def git(*args, stdin=None, check=True):
    # Bytes in and out: in text mode Windows turns every "\n" written to stdin into "\r\n", and mktree would read the "\r" as part of the name.
    r = subprocess.run(["git", *args], input=None if stdin is None else stdin.encode("utf-8"), capture_output=True)
    if check and r.returncode:
        sys.exit(f"git {' '.join(args)} failed:\n{r.stderr.decode('utf-8', 'replace')}")
    return r.stdout.decode("utf-8", "replace").replace("\r\n", "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    os.chdir(git("rev-parse", "--show-toplevel").strip())
    git("fetch", "origin", "gh-pages")
    rows = [ln for ln in git("ls-tree", BRANCH).splitlines() if ln]          # "<mode> <type> <sha>\t<name>"
    names = [ln.split("\t", 1)[1] for ln in rows]
    drop = sorted(n for n in names if n not in KEEP)
    keep = sorted(n for n in names if n in KEEP)
    print(f"root of {BRANCH}: {len(names)} entries; stay: {', '.join(keep)}; go: {len(drop)}")
    if not {"docu", "semweb", "index.html"} <= set(names):
        sys.exit("docu, semweb or index.html is missing on gh-pages: nothing removed. Let the workflows run first.")
    print("examples of what goes:", ", ".join(drop[:8]), "...")
    if not args.apply:
        print("dry run; add --apply to make the commit")
        return
    # The new root tree holds only the kept entries, referenced by their hashes. No index and no checkout are involved.
    tree = git("mktree", stdin="\n".join(ln for ln in rows if ln.split("\t", 1)[1] in KEEP) + "\n").strip()
    left = [n for n in git("ls-tree", "--name-only", tree).splitlines() if n]
    if sorted(left) != keep:
        sys.exit(f"unexpected result, nothing committed: {left}")
    commit = git("commit-tree", tree, "-p", BRANCH, "-m",
                 "Remove old SPARQL Unicorn pages from the root (now under /semweb/)").strip()
    print(f"commit {commit[:12]} made, nothing checked out. Push it with:\n  git push origin {commit}:refs/heads/gh-pages")
    print("The push is refused if gh-pages moved in the meantime: run the script again.")


if __name__ == "__main__":
    main()
