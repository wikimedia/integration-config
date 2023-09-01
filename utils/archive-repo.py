#!/usr/bin/env python3

from __future__ import print_function

import argparse
import re
import subprocess
import tempfile

# From https://pypi.org/project/python-Levenshtein/
import Levenshtein


def search_for(search, f, out, Print=True):
    search += "\n"

    while True:
        line = f.readline()  # Newline is included
        if line == "":
            raise Exception("Unexpected EOF")
        if Print:
            out.write(line)
        if line == search:
            return


def remove_pipeline_def(repo_name, f, out):
    while True:
        line = f.readline()  # Newline is included

        if line == "":
            raise SystemExit("Did not find a pipeline definition for {}"
                             "in zuul/layout.yaml".format(
                                 repo_name))

        if repo_name not in line:
            out.write(line)
            continue

        if line != "  - name: {}\n".format(repo_name):
            raise Exception("Don't know how to handle line: {}".format(line))

        break

    # We've reached the first line of the pipeline definition.  Skip
    # the rest of the pipeline definition, including the terminating
    # blank line.
    search_for("", f, out, Print=False)


class ArchivedRepo:
    def __init__(self, name=None, text=""):
        self.name = name
        self.text = text

    def add_text(self, line):
        self.text += line

    def set_name(self, name):
        self.name = name


def grok_archived_repo(f):
    """
    Returns an ArchivedRepo or None.
    """
    repo = ArchivedRepo()

    while True:
        line = f.readline()
        if line == "":
            if not repo.text:
                return None
            raise Exception(
                "Unexpected EOF. Text up to this point is {}".format(
                    repo.text))

        repo.add_text(line)

        m = re.match(r"  - name: (.*)", line.rstrip())
        if m:
            repo.set_name(m[1])

        if line.startswith("      - name: archived"):
            return repo


def grok_archive_section(f):
    res = []

    while True:
        repo = grok_archived_repo(f)
        if repo is None:
            break
        res.append(repo)

    return res


def select_archive_section_insert_point(archives, repo_name):
    """
    The list of archived repos is semi-sorted, so use a heuristic to find
    a similar entry to the to-be-archived repo.
    """
    best_index = None
    best_distance = float("inf")

    for idx, r in enumerate(archives):
        distance = Levenshtein.distance(r.name, repo_name)
        if distance < best_distance:
            best_index = idx
            best_distance = distance

    if repo_name > archives[best_index].name:
        best_index += 1

    return best_index


def process_archive_section(repo_name, f, out, comment):
    if comment:
        comment = " # {}".format(comment)
    else:
        comment = ""

    new_archive = ArchivedRepo(
        repo_name,
        """
  - name: {}
    template:
      - name: archived{}
""".format(repo_name, comment))

    search_for(
        "#### Archive repositories ######################################",
        f, out)
    archives = grok_archive_section(f)
    insert_index = select_archive_section_insert_point(archives, repo_name)
    archives.insert(insert_index, new_archive)

    for r in archives:
        out.write(r.text)


def archive(repo_name, comment):
    with tempfile.NamedTemporaryFile("w+") as out:
        with open("zuul/layout.yaml") as f:
            remove_pipeline_def(repo_name, f, out)
            process_archive_section(repo_name, f, out, comment)

        out.flush()

        subprocess.run(["diff", "-U10", "--color",
                        "zuul/layout.yaml", out.name])
        ans = input("Does the diff OK? ")
        if ans != 'y':
            raise SystemExit("Cancelled")

        with open("zuul/layout.yaml", "w") as f:
            out.seek(0)
            f.write(out.read())

        print("zuul/layout.yaml updated")


def main():
    parser = argparse.ArgumentParser(
        description='Archives a repo in zuul/layout.yaml')
    parser.add_argument('repo')
    parser.add_argument('comment', nargs='+')
    args = parser.parse_args()
    archive(args.repo, " ".join(args.comment))


if __name__ == "__main__":
    main()
