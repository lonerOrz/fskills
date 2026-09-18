from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import NoReturn, cast

import tomllib

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = PROJECT_ROOT / "source.toml"
LOCK_FILE = PROJECT_ROOT / "source.lock.toml"

LOCK_VERSION = 1
GITHUB_API = "https://api.github.com"
USER_AGENT = "fskills-source/2.1"


class SourceError(Exception):
    """User-facing configuration or source resolution error."""


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceSpec:
    repo: str | None
    path: Path | None
    branch: str | None
    target: Path
    selectors: tuple[str, ...]

    @property
    def is_local(self) -> bool:
        return self.path is not None

    @property
    def identifier(self) -> str:
        if self.path is not None:
            return self.path.as_posix()
        return cast(str, self.repo)


@dataclass(frozen=True)
class ResolvedPackage:
    source_path: PurePosixPath
    name: str


@dataclass(frozen=True)
class RepositorySnapshot:
    branch: str
    commit: str
    files: frozenset[PurePosixPath]
    directories: frozenset[PurePosixPath]


@dataclass(frozen=True)
class SourceState:
    spec: SourceSpec
    branch: str | None
    remote_commit: str | None
    locked_commit: str | None
    packages: tuple[ResolvedPackage, ...]
    local_packages: tuple[str, ...]

    @property
    def is_local(self) -> bool:
        return self.spec.is_local

    @property
    def commit_changed(self) -> bool:
        if self.is_local:
            return False
        return self.locked_commit != self.remote_commit

    @property
    def local_changed(self) -> bool:
        expected = {package.name for package in self.packages}
        actual = set(self.local_packages)
        return expected != actual

    @property
    def missing_packages(self) -> tuple[str, ...]:
        expected = {package.name for package in self.packages}
        actual = set(self.local_packages)
        return tuple(sorted(expected - actual))

    @property
    def extra_packages(self) -> tuple[str, ...]:
        if self.is_local:
            return ()
        expected = {package.name for package in self.packages}
        actual = set(self.local_packages)
        return tuple(sorted(actual - expected))

    @property
    def needs_sync(self) -> bool:
        if self.is_local:
            return False
        return self.locked_commit is None or self.commit_changed or self.local_changed

    @property
    def status(self) -> str:
        if self.is_local:
            return "LOCAL"
        if self.locked_commit is None:
            return "UNLOCKED"
        if self.commit_changed:
            return "UPDATE"
        if self.local_changed:
            return "DESYNC"
        return "UP-TO-DATE"


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------


def fail(message: str) -> NoReturn:
    raise SourceError(message)


def run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    retries: int = 3,
) -> str:
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")

    last_error = ""
    for attempt in range(1, retries + 1):
        result = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode == 0:
            return result.stdout

        command = " ".join(args)
        detail = result.stderr.strip() or result.stdout.strip()
        last_error = (
            f"command failed: {command}\n{detail}"
            if detail
            else f"command failed: {command}"
        )

        is_network_error = any(
            err in detail.lower()
            for err in (
                "unexpected eof",
                "connection reset",
                "timed out",
                "could not resolve host",
                "failed to connect",
                "tls connect error",
                "gnutls_handshake",
                "ssl routines",
            )
        )

        if is_network_error and attempt < retries:
            summary_err = detail.splitlines()[-1] if detail else "network error"
            print(
                f"warning: network glitch on {args[0]} ({summary_err}), retrying ({attempt}/{retries})...",
                file=sys.stderr,
            )
            time.sleep(1.5 * attempt)
            continue
        break

    fail(last_error)


def ensure_git() -> None:
    if shutil.which("git") is None:
        fail("git is required but was not found in PATH")


def load_toml(path: Path) -> dict[str, object]:
    try:
        with path.open("rb") as handle:
            value = tomllib.load(handle)
    except FileNotFoundError:
        fail(f"file not found: {path.relative_to(PROJECT_ROOT)}")
    except tomllib.TOMLDecodeError as exc:
        fail(f"invalid TOML in {path.relative_to(PROJECT_ROOT)}: {exc}")

    return cast(dict[str, object], value)


def as_table(value: object, *, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        fail(f"{context} must be a table")
    return cast(dict[str, object], value)


def as_string(value: object, *, context: str) -> str:
    if not isinstance(value, str):
        fail(f"{context} must be a string")
    value = value.strip()
    if not value:
        fail(f"{context} must not be empty")
    return value


def as_string_list(value: object, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        fail(f"{context} must be an array of strings")

    values = cast(list[object], value)
    if not values:
        fail(f"{context} must not be empty")

    result: list[str] = []
    for index, item in enumerate(values, start=1):
        result.append(as_string(item, context=f"{context}[{index}]"))
    return tuple(result)


def normalize_relative_path(value: str, *, field: str) -> Path:
    value = value.strip().rstrip("/")
    if not value:
        fail(f"{field} must not be empty")
    if "\\" in value:
        fail(f"{field} must use POSIX paths: {value!r}")

    path = PurePosixPath(value)
    if path.is_absolute():
        fail(f"{field} must be relative: {value!r}")
    if any(part in {".", "..", ""} for part in path.parts):
        fail(f"{field} contains an invalid path component: {value!r}")

    return Path(*path.parts)


def normalize_selector_path(value: str) -> PurePosixPath:
    if not value or value.startswith("/") or "\\" in value:
        fail(f"invalid selector path: {value!r}")

    path = PurePosixPath(value)
    if path.is_absolute():
        fail(f"invalid selector path: {value!r}")
    if any(part in {".", "..", ""} for part in path.parts):
        fail(f"invalid selector path: {value!r}")

    return path


# ---------------------------------------------------------------------------
# source.toml parsing
# ---------------------------------------------------------------------------


def parse_repo(value: object) -> str:
    repo = as_string(value, context="repo")
    parts = repo.split("/")
    if len(parts) != 2:
        fail(f"repo must use 'owner/repository' format: {repo!r}")

    owner, name = parts
    if not owner or not name or any(part in {".", ".."} for part in parts):
        fail(f"invalid repo: {repo!r}")

    return repo


def validate_selector(selector: str) -> None:
    if selector == "*":
        return

    if selector.startswith("/") or "\\" in selector:
        fail(f"invalid selector: {selector!r}")

    if selector.endswith("/*"):
        base = selector[:-2]
        if not base:
            fail(f"invalid selector: {selector!r}")
        normalize_selector_path(base)
        return

    path = PurePosixPath(selector)
    if not path.parts:
        fail(f"invalid selector: {selector!r}")

    last = path.parts[-1]
    if last.startswith("^"):
        if len(path.parts) < 2:
            fail(f"regex selector requires a base directory: {selector!r}")
        base = PurePosixPath(*path.parts[:-1])
        normalize_selector_path(base.as_posix())
        try:
            re.compile(last)
        except re.error as exc:
            fail(f"invalid regex in selector {selector!r}: {exc}")
        return

    if any(char in selector for char in "*?[]"):
        fail(f"unsupported selector syntax: {selector!r}")

    normalize_selector_path(selector)


def parse_sources() -> tuple[SourceSpec, ...]:
    data = load_toml(SOURCE_FILE)
    raw_sources = data.get("sources")
    if not isinstance(raw_sources, list):
        fail("source.toml must contain [[sources]] entries")

    raw_items = cast(list[object], raw_sources)
    if not raw_items:
        fail("source.toml must contain at least one [[sources]] entry")

    allowed_keys = {"repo", "path", "branch", "target", "skills"}
    result: list[SourceSpec] = []
    seen_identifiers: set[str] = set()

    for index, raw_value in enumerate(raw_items, start=1):
        raw = as_table(raw_value, context=f"sources[{index}]")
        unknown = set(raw) - allowed_keys
        if unknown:
            names = ", ".join(sorted(str(value) for value in unknown))
            fail(f"sources[{index}] has unknown field(s): {names}")

        has_repo = "repo" in raw
        has_path = "path" in raw

        if has_repo and has_path:
            fail(f"sources[{index}] cannot specify both 'repo' and 'path'")
        if not has_repo and not has_path:
            fail(f"sources[{index}] must specify either 'repo' or 'path'")

        selectors = as_string_list(
            raw.get("skills", ["*"]),
            context=f"sources[{index}].skills",
        )
        for selector in selectors:
            validate_selector(selector)

        if has_repo:
            repo = parse_repo(raw.get("repo"))
            identifier = repo
            if identifier in seen_identifiers:
                fail(f"repository declared more than once: {repo}")
            seen_identifiers.add(identifier)

            branch_value = raw.get("branch")
            branch = (
                None
                if branch_value is None
                else as_string(branch_value, context=f"sources[{index}].branch")
            )

            target = normalize_relative_path(
                as_string(
                    raw.get("target", "skills/"), context=f"sources[{index}].target"
                ),
                field=f"sources[{index}].target",
            )

            result.append(
                SourceSpec(
                    repo=repo,
                    path=None,
                    branch=branch,
                    target=target,
                    selectors=selectors,
                )
            )

        else:
            if "branch" in raw:
                fail(f"sources[{index}] local source cannot specify 'branch'")

            path = normalize_relative_path(
                as_string(raw.get("path"), context=f"sources[{index}].path"),
                field=f"sources[{index}].path",
            )
            identifier = path.as_posix()
            if identifier in seen_identifiers:
                fail(f"local path declared more than once: {identifier}")
            seen_identifiers.add(identifier)

            target = (
                normalize_relative_path(
                    as_string(raw.get("target"), context=f"sources[{index}].target"),
                    field=f"sources[{index}].target",
                )
                if "target" in raw
                else path
            )

            result.append(
                SourceSpec(
                    repo=None,
                    path=path,
                    branch=None,
                    target=target,
                    selectors=selectors,
                )
            )

    sources = tuple(result)
    validate_targets(sources)
    return sources


def validate_targets(sources: tuple[SourceSpec, ...]) -> None:
    items = [(source.target, source.identifier) for source in sources]
    for index, (target_a, id_a) in enumerate(items):
        for target_b, id_b in items[index + 1 :]:
            parts_a = target_a.parts
            parts_b = target_b.parts

            if parts_a == parts_b:
                fail(
                    f"multiple sources use the same target {target_a}: {id_a} and {id_b}"
                )

            shorter, longer = (
                (parts_a, parts_b)
                if len(parts_a) < len(parts_b)
                else (parts_b, parts_a)
            )
            if longer[: len(shorter)] == shorter:
                fail(
                    f"source targets overlap: {id_a} -> {target_a} and {id_b} -> {target_b}"
                )


# ---------------------------------------------------------------------------
# GitHub authentication and API
# ---------------------------------------------------------------------------

_VALID_TOKENS_CACHE: list[str] | None = None
_WARNED_TOKENS: set[str] = set()


def github_tokens() -> tuple[str, ...]:
    global _VALID_TOKENS_CACHE
    if _VALID_TOKENS_CACHE is not None:
        return tuple(_VALID_TOKENS_CACHE)

    tokens: list[str] = []
    for variable in ("GH_TOKEN", "GITHUB_TOKEN"):
        token = os.environ.get(variable)
        if token and token.strip() and token.strip() not in tokens:
            tokens.append(token.strip())

    if shutil.which("gh") is not None:
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                gh_token = result.stdout.strip()
                if gh_token and gh_token not in tokens:
                    tokens.append(gh_token)
        except OSError:
            pass

    _VALID_TOKENS_CACHE = tokens
    return tuple(_VALID_TOKENS_CACHE)


def drop_invalid_token(token: str) -> None:
    if _VALID_TOKENS_CACHE and token in _VALID_TOKENS_CACHE:
        _VALID_TOKENS_CACHE.remove(token)


def github_api_get(url: str, *, token: str | None) -> dict[str, object] | None:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            if token and token not in _WARNED_TOKENS:
                print(
                    "warning: GitHub token rejected; falling back to next auth method",
                    file=sys.stderr,
                )
                _WARNED_TOKENS.add(token)
                drop_invalid_token(token)
            return None

        detail = exc.read().decode("utf-8", errors="replace").strip()
        if exc.code == 403:
            fail(f"GitHub API rate limit or permission error for {url}: {detail}")
        fail(f"GitHub API returned HTTP {exc.code} for {url}: {detail}")
    except urllib.error.URLError as exc:
        fail(f"GitHub API request failed for {url}: {exc.reason}")

    try:
        parsed = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"invalid GitHub API response for {url}: {exc}")

    if not isinstance(parsed, dict):
        fail(f"unexpected GitHub API response for {url}")

    return cast(dict[str, object], parsed)


def fetch_remote_tree_via_api(
    repo: str, commit: str
) -> tuple[set[PurePosixPath], set[PurePosixPath]] | None:
    url = f"{GITHUB_API}/repos/{repo}/git/trees/{commit}?recursive=1"
    for token in github_tokens():
        resp = github_api_get(url, token=token)
        if resp is not None:
            return parse_api_tree(resp)

    resp = github_api_get(url, token=None)
    if resp is not None:
        return parse_api_tree(resp)

    return None


def parse_api_tree(
    data: dict[str, object],
) -> tuple[set[PurePosixPath], set[PurePosixPath]]:
    tree = data.get("tree")
    if not isinstance(tree, list):
        fail("invalid git tree returned by GitHub API")

    files: set[PurePosixPath] = set()
    directories: set[PurePosixPath] = set()

    for item in tree:
        if isinstance(item, dict):
            path_str = item.get("path")
            item_type = item.get("type")
            if isinstance(path_str, str):
                p = PurePosixPath(path_str)
                if item_type == "blob":
                    files.add(p)
                    for parent in p.parents:
                        if parent != PurePosixPath("."):
                            directories.add(parent)
                elif item_type == "tree":
                    directories.add(p)

    return files, directories


# ---------------------------------------------------------------------------
# Git Remote & Local Snapshot State
# ---------------------------------------------------------------------------


def github_url(repo: str) -> str:
    return f"https://github.com/{repo}.git"


def resolve_repo_remote_head(
    repo: str, requested_branch: str | None
) -> tuple[str, str]:
    if requested_branch is not None:
        output = run_command(
            ["git", "ls-remote", github_url(repo), f"refs/heads/{requested_branch}"]
        )
        expected_ref = f"refs/heads/{requested_branch}"
        for line in output.splitlines():
            fields = line.split("\t", 1)
            if len(fields) == 2 and fields[1] == expected_ref:
                commit = fields[0].strip().lower()
                if re.fullmatch(r"[0-9a-f]{40}", commit):
                    return requested_branch, commit
        fail(f"branch not found: {repo}:{requested_branch}")

    output = run_command(["git", "ls-remote", "--symref", github_url(repo), "HEAD"])
    branch = None
    commit = None

    for line in output.splitlines():
        line = line.strip()
        if line.startswith("ref: refs/heads/"):
            branch = line.split("\t")[0].removeprefix("ref: refs/heads/").strip()
        elif "\tHEAD" in line:
            commit = line.split("\t")[0].strip().lower()

    if branch and commit and re.fullmatch(r"[0-9a-f]{40}", commit):
        return branch, commit

    fail(f"could not determine default branch or HEAD commit for {repo}")


def fetch_remote_tree_via_git(
    repo: str, branch: str
) -> tuple[set[PurePosixPath], set[PurePosixPath]]:
    with tempfile.TemporaryDirectory(prefix="fskills-tree-") as temp_dir:
        dest = Path(temp_dir) / "repo"
        command = [
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            "--depth",
            "1",
            "--no-tags",
            "--branch",
            branch,
            github_url(repo),
            str(dest),
        ]
        run_command(command)

        output = run_command(
            ["git", "-C", str(dest), "ls-tree", "-r", "--name-only", "HEAD"]
        )
        files = {
            PurePosixPath(line.strip()) for line in output.splitlines() if line.strip()
        }
        directories: set[PurePosixPath] = set()
        for f in files:
            for parent in f.parents:
                if parent != PurePosixPath("."):
                    directories.add(parent)
        return files, directories


def build_repository_snapshot(
    repo: str, branch: str, commit: str
) -> RepositorySnapshot:
    try:
        res = fetch_remote_tree_via_api(repo, commit)
        if res is not None:
            files, directories = res
            return RepositorySnapshot(
                branch=branch,
                commit=commit,
                files=frozenset(files),
                directories=frozenset(directories),
            )
    except SourceError:
        pass

    files, directories = fetch_remote_tree_via_git(repo, branch)
    return RepositorySnapshot(
        branch=branch,
        commit=commit,
        files=frozenset(files),
        directories=frozenset(directories),
    )


def build_local_snapshot(path: Path) -> RepositorySnapshot:
    """扫描本地自研路径构建同构快照，高内聚复用包解析算法。"""
    full_path = PROJECT_ROOT / path
    if not full_path.exists():
        fail(f"local source path does not exist: {path.as_posix()}")
    if not full_path.is_dir():
        fail(f"local source path is not a directory: {path.as_posix()}")

    files: set[PurePosixPath] = set()
    directories: set[PurePosixPath] = set()

    for root, _dirs, filenames in os.walk(full_path):
        root_path = Path(root)
        rel_root = root_path.relative_to(full_path)
        if rel_root != Path("."):
            directories.add(PurePosixPath(rel_root.as_posix()))

        for filename in filenames:
            rel_file = PurePosixPath((rel_root / filename).as_posix())
            files.add(rel_file)
            for parent in rel_file.parents:
                if parent != PurePosixPath("."):
                    directories.add(parent)

    return RepositorySnapshot(
        branch="local",
        commit="local",
        files=frozenset(files),
        directories=frozenset(directories),
    )


# ---------------------------------------------------------------------------
# Skill resolution
# ---------------------------------------------------------------------------


def skill_files_under(
    snapshot: RepositorySnapshot,
    root: PurePosixPath,
) -> tuple[PurePosixPath, ...]:
    prefix = root.parts
    matches = [
        path
        for path in snapshot.files
        if (path.name == "SKILL.md" and path.parts[: len(prefix)] == prefix)
    ]
    return tuple(sorted(matches, key=lambda path: path.as_posix()))


def package_root_for_skill_file(skill_file: PurePosixPath) -> PurePosixPath:
    parent = skill_file.parent
    if parent == PurePosixPath("."):
        fail("SKILL.md at repository root is not a skill package")

    if parent.name == "skill":
        root = parent.parent
        if root == PurePosixPath("."):
            fail(f"invalid package root for {skill_file}")
        return root

    return parent


def is_direct_child(path: PurePosixPath, base: PurePosixPath) -> bool:
    return (
        len(path.parts) == len(base.parts) + 1
        and path.parts[: len(base.parts)] == base.parts
    )


def package_for_directory(
    snapshot: RepositorySnapshot,
    directory: PurePosixPath,
) -> ResolvedPackage | None:
    if not skill_files_under(snapshot, directory):
        return None
    return ResolvedPackage(source_path=directory, name=directory.name)


def resolve_all(snapshot: RepositorySnapshot) -> tuple[ResolvedPackage, ...]:
    packages: dict[PurePosixPath, ResolvedPackage] = {}
    for skill_file in snapshot.files:
        if skill_file.name != "SKILL.md":
            continue
        root = package_root_for_skill_file(skill_file)
        packages[root] = ResolvedPackage(source_path=root, name=root.name)

    if not packages:
        fail("selector '*' matched no SKILL.md files")

    return tuple(sorted(packages.values(), key=lambda p: p.source_path.as_posix()))


def resolve_children(
    snapshot: RepositorySnapshot,
    base: PurePosixPath,
    pattern: re.Pattern[str] | None = None,
) -> tuple[ResolvedPackage, ...]:
    if base not in snapshot.directories:
        fail(f"selector path does not exist: {base.as_posix()}")

    packages: dict[PurePosixPath, ResolvedPackage] = {}
    children = sorted(
        (d for d in snapshot.directories if is_direct_child(d, base)),
        key=lambda d: d.as_posix(),
    )

    for child in children:
        if pattern is not None and pattern.fullmatch(child.name) is None:
            continue
        package = package_for_directory(snapshot, child)
        if package is not None:
            packages[package.source_path] = package

    if not packages:
        selector = (
            f"{base.as_posix()}/*"
            if pattern is None
            else f"{base.as_posix()}/{pattern.pattern}"
        )
        fail(f"selector matched no skill packages: {selector}")

    return tuple(sorted(packages.values(), key=lambda p: p.source_path.as_posix()))


def resolve_exact(snapshot: RepositorySnapshot, path: PurePosixPath) -> ResolvedPackage:
    if path not in snapshot.directories:
        fail(f"skill path does not exist: {path.as_posix()}")

    package = package_for_directory(snapshot, path)
    if package is None:
        fail(f"path is not a skill package (SKILL.md not found): {path.as_posix()}")

    return package


def resolve_selector(
    snapshot: RepositorySnapshot, selector: str
) -> tuple[ResolvedPackage, ...]:
    if selector == "*":
        return resolve_all(snapshot)

    if selector.endswith("/*"):
        return resolve_children(snapshot, normalize_selector_path(selector[:-2]))

    path = PurePosixPath(selector)
    last = path.parts[-1]

    if last.startswith("^"):
        base = PurePosixPath(*path.parts[:-1])
        try:
            pattern = re.compile(last)
        except re.error as exc:
            fail(f"invalid regex in selector {selector!r}: {exc}")
        return resolve_children(snapshot, base, pattern)

    return (resolve_exact(snapshot, path),)


def resolve_packages(
    snapshot: RepositorySnapshot,
    selectors: tuple[str, ...],
) -> tuple[ResolvedPackage, ...]:
    packages: dict[PurePosixPath, ResolvedPackage] = {}
    names: dict[str, PurePosixPath] = {}

    for selector in selectors:
        for package in resolve_selector(snapshot, selector):
            previous = names.get(package.name)
            if previous is not None and previous != package.source_path:
                fail(
                    f"skill name collision: {package.name!r}\n"
                    f"  first: {previous.as_posix()}\n"
                    f"  second: {package.source_path.as_posix()}"
                )
            names[package.name] = package.source_path
            packages[package.source_path] = package

    return tuple(sorted(packages.values(), key=lambda p: p.source_path.as_posix()))


# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------


def load_lock() -> dict[str, str]:
    if not LOCK_FILE.exists():
        return {}

    data = load_toml(LOCK_FILE)
    version = data.get("version")
    if version != LOCK_VERSION:
        fail(
            f"unsupported source.lock.toml version: {version!r}; expected {LOCK_VERSION}"
        )

    raw_sources = data.get("sources", [])
    if not isinstance(raw_sources, list):
        fail("source.lock.toml: sources must be an array of tables")

    result: dict[str, str] = {}
    for index, raw_value in enumerate(cast(list[object], raw_sources), start=1):
        raw = as_table(raw_value, context=f"source.lock.toml sources[{index}]")
        if set(raw) != {"repo", "commit"}:
            fail("source.lock.toml: each source must contain only repo and commit")

        repo = parse_repo(raw.get("repo"))
        commit = as_string(raw.get("commit"), context=f"lock commit for {repo}").lower()
        if re.fullmatch(r"[0-9a-f]{40}", commit) is None:
            fail(f"invalid lock commit for {repo}: {commit!r}")
        if repo in result:
            fail(f"duplicate lock repository: {repo}")

        result[repo] = commit

    return result


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def render_lock(states: tuple[SourceState, ...]) -> str:
    lines = [f"version = {LOCK_VERSION}", ""]
    for state in states:
        if state.is_local:
            continue
        lines.extend(
            [
                "[[sources]]",
                f"repo = {toml_string(cast(str, state.spec.repo))}",
                f"commit = {toml_string(cast(str, state.remote_commit))}",
                "",
            ]
        )
    return "\n".join(lines)


def write_lock_atomic(states: tuple[SourceState, ...]) -> None:
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=".source-lock-",
        suffix=".tmp",
        dir=LOCK_FILE.parent,
        text=True,
    )
    os.close(fd)
    temporary = Path(temp_name)
    try:
        temporary.write_text(render_lock(states), encoding="utf-8")
        temporary.replace(LOCK_FILE)
    finally:
        temporary.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Local Materialized State
# ---------------------------------------------------------------------------


def local_package_names(target: Path) -> tuple[str, ...]:
    if not target.exists():
        return ()
    if not target.is_dir():
        fail(f"target exists but is not a directory: {target}")

    return tuple(
        sorted(
            entry.name
            for entry in target.iterdir()
            if (entry.is_dir() and not entry.name.startswith("."))
        )
    )


def build_source_state(
    spec: SourceSpec,
    locked_commits: dict[str, str],
) -> SourceState:
    target = PROJECT_ROOT / spec.target

    if spec.is_local:
        snapshot = build_local_snapshot(cast(Path, spec.path))
        packages = resolve_packages(snapshot, spec.selectors)
        return SourceState(
            spec=spec,
            branch=None,
            remote_commit=None,
            locked_commit=None,
            packages=packages,
            local_packages=local_package_names(target),
        )

    repo = cast(str, spec.repo)
    branch, remote_commit = resolve_repo_remote_head(repo, spec.branch)
    snapshot = build_repository_snapshot(repo, branch, remote_commit)
    packages = resolve_packages(snapshot, spec.selectors)

    return SourceState(
        spec=spec,
        branch=branch,
        remote_commit=remote_commit,
        locked_commit=locked_commits.get(repo),
        packages=packages,
        local_packages=local_package_names(target),
    )


def resolve_sources(locked_commits: dict[str, str]) -> tuple[SourceState, ...]:
    sources = parse_sources()
    states = tuple(build_source_state(source, locked_commits) for source in sources)
    validate_destination_collisions(states)
    return states


def validate_destination_collisions(states: tuple[SourceState, ...]) -> None:
    destinations: dict[Path, tuple[str, PurePosixPath]] = {}
    for state in states:
        for package in state.packages:
            destination = state.spec.target / package.name
            previous = destinations.get(destination)
            if previous is not None:
                first_id, first_path = previous
                fail(
                    f"skill destination collision: {destination.as_posix()}\n"
                    f"  first: {first_id}:{first_path.as_posix()}\n"
                    f"  second: {state.spec.identifier}:{package.source_path.as_posix()}"
                )
            destinations[destination] = (state.spec.identifier, package.source_path)


# ---------------------------------------------------------------------------
# Materialization & Pruning
# ---------------------------------------------------------------------------


def clone_full_repository(repo: str, branch: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "git",
        "clone",
        "--depth",
        "1",
        "--no-tags",
        "--branch",
        branch,
        github_url(repo),
        str(destination),
    ]
    run_command(command)


def stage_source(
    state: SourceState,
    repo_dir: Path,
    staging_root: Path,
) -> Path:
    staging_target = staging_root / Path(*state.spec.target.parts)
    staging_target.mkdir(parents=True, exist_ok=True)

    for package in state.packages:
        source = repo_dir / Path(*package.source_path.parts)
        destination = staging_target / package.name
        if not source.is_dir():
            fail(f"resolved skill package is not a directory: {source}")
        shutil.copytree(source, destination, symlinks=True)

    return staging_target


def apply_staged_targets(
    staged: tuple[tuple[SourceState, Path], ...],
    transaction_root: Path,
) -> None:
    backups_root = transaction_root / "backups"
    swaps: list[tuple[Path, Path | None]] = []

    try:
        for state, staged_target in staged:
            target = PROJECT_ROOT / state.spec.target
            target.parent.mkdir(parents=True, exist_ok=True)

            backup: Path | None = None
            if target.exists() or target.is_symlink():
                backup = backups_root / Path(*state.spec.target.parts)
                backup.parent.mkdir(parents=True, exist_ok=True)
                target.rename(backup)

            swaps.append((target, backup))
            staged_target.rename(target)

    except OSError as exc:
        for target, backup in reversed(swaps):
            try:
                if target.exists():
                    shutil.rmtree(target) if target.is_dir() else target.unlink()
                if backup is not None and backup.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    backup.rename(target)
            except OSError:
                pass
        fail(f"failed to apply staged skills: {exc}")

    for _, backup in swaps:
        if backup is not None and backup.exists():
            shutil.rmtree(backup, ignore_errors=True)


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def short_commit(commit: str | None) -> str:
    return "-" if commit is None else commit[:12]


def state_to_dict(state: SourceState) -> dict[str, object]:
    return {
        "type": "local" if state.is_local else "remote",
        "repo": state.spec.repo,
        "path": state.spec.path.as_posix() if state.spec.path is not None else None,
        "branch": state.branch,
        "remote_commit": state.remote_commit,
        "locked_commit": state.locked_commit,
        "target": state.spec.target.as_posix(),
        "status": state.status,
        "needs_sync": state.needs_sync,
        "selectors": list(state.spec.selectors),
        "packages": [
            {"name": p.name, "source_path": p.source_path.as_posix()}
            for p in state.packages
        ],
        "missing_packages": list(state.missing_packages),
        "extra_packages": list(state.extra_packages),
    }


def print_state(state: SourceState) -> None:
    source_label = (
        f"{state.spec.identifier} (local)" if state.is_local else state.spec.identifier
    )
    print(f"Source: {source_label}")

    if not state.is_local:
        print(f"  branch: {state.branch}")
        print(f"  remote: {short_commit(state.remote_commit)}")
        print(f"  locked: {short_commit(state.locked_commit)}")

    print(f"  target: {state.spec.target.as_posix()}/")
    print(f"  status: {state.status}")

    for selector in state.spec.selectors:
        print(f"  selector: {selector}")
    for package in state.packages:
        print(f"    + {package.name} ({package.source_path.as_posix()})")

    if state.missing_packages:
        print("  missing locally (will add):")
        for name in state.missing_packages:
            print(f"    ! {name}")

    if state.extra_packages:
        print("  extra locally (will prune):")
        for name in state.extra_packages:
            print(f"    - {name}")

    print(f"  packages: {len(state.packages)}")
    print()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_check(*, as_json: bool = False) -> int:
    ensure_git()

    try:
        locked = load_lock()
        states = resolve_sources(locked)

        configured_remote_repos = {s.spec.repo for s in states if not s.is_local}
        stale_lock = sorted(set(locked) - configured_remote_repos)

        updates = [state for state in states if state.commit_changed]
        unlocked = [
            state
            for state in states
            if not state.is_local and state.locked_commit is None
        ]
        desynced = [state for state in states if state.local_changed]
        needs_sync = any(state.needs_sync for state in states) or bool(stale_lock)

        if as_json:
            report = {
                "summary": {
                    "sources": len(states),
                    "updates": len(updates),
                    "unlocked": len(unlocked),
                    "local_desync": len(desynced),
                    "stale_lock_entries": len(stale_lock),
                    "needs_sync": needs_sync,
                },
                "stale_locks": stale_lock,
                "sources": [state_to_dict(s) for s in states],
            }
            print(json.dumps(report, indent=2))
            return 0

        for state in states:
            print_state(state)

        print("Check passed.")
        print(f"  sources: {len(states)}")
        print(f"  updates: {len(updates)}")
        print(f"  unlocked: {len(unlocked)}")
        print(f"  local desync (missing/extra): {len(desynced)}")
        print(f"  stale lock entries: {len(stale_lock)}")

    except SourceError as exc:
        if as_json:
            print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


def cmd_update() -> int:
    ensure_git()

    try:
        locked = load_lock()
        states = resolve_sources(locked)

        changed = tuple(state for state in states if state.needs_sync)
        configured_remote_repos = {s.spec.repo for s in states if not s.is_local}
        stale_lock = sorted(set(locked) - configured_remote_repos)

        print("Update plan:")
        for state in states:
            if state.is_local:
                action = "SKIP"
                reason = "local source"
                print(f"  {action:4} {state.spec.identifier:32} ({reason})")
                continue

            if not state.needs_sync:
                action = "SKIP"
                reason = "up-to-date"
            else:
                action = "SYNC"
                reasons: list[str] = []
                if state.locked_commit is None:
                    reasons.append("unlocked")
                elif state.commit_changed:
                    reasons.append("remote commit changed")
                if state.missing_packages:
                    reasons.append(f"+{len(state.missing_packages)} missing")
                if state.extra_packages:
                    reasons.append(f"-{len(state.extra_packages)} extra")
                reason = ", ".join(reasons)

            print(
                f"  {action:4} {state.spec.identifier:32} "
                f"{short_commit(state.locked_commit)} -> {short_commit(state.remote_commit)} "
                f"({reason})"
            )

        if stale_lock:
            print("\nStale lock entries will be removed:")
            for repo in stale_lock:
                print(f"  - {repo}")

        print()

        if not changed and not stale_lock:
            print("Everything is already up-to-date.")
            return 0

        with tempfile.TemporaryDirectory(
            prefix=".fskills-update-",
            dir=PROJECT_ROOT,
        ) as transaction_name:
            transaction_root = Path(transaction_name)
            staged: list[tuple[SourceState, Path]] = []

            for index, state in enumerate(changed):
                repo_dest = transaction_root / "repos" / f"repo-{index}"
                print(f"Fetching {state.spec.identifier}@{cast(str, state.branch)}...")
                clone_full_repository(
                    cast(str, state.spec.repo),
                    cast(str, state.branch),
                    repo_dest,
                )

                staged_target = stage_source(
                    state, repo_dest, transaction_root / "staging"
                )
                staged.append((state, staged_target))

            apply_staged_targets(tuple(staged), transaction_root)
            write_lock_atomic(states)

    except SourceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Update completed successfully.")
    return 0


def cmd_link(destination_str: str, *, force: bool = False) -> int:
    """严格依据所有 sources (包含远程与本地自研) 选择器解析出的激活包建立软链接。"""
    dest_path = Path(destination_str).expanduser().resolve()
    if not dest_path.exists():
        dest_path.mkdir(parents=True, exist_ok=True)
    elif not dest_path.is_dir():
        fail(f"destination exists but is not a directory: {dest_path}")

    # 解析所有合法声明的源与激活包
    locked = load_lock()
    states = resolve_sources(locked)

    expected_links: dict[str, Path] = {}  # package_name -> abs_pkg_path

    for state in states:
        target_dir = (PROJECT_ROOT / state.spec.target).resolve()
        # 仅遍历当前被 selectors (如 skills = [...]) 激活命中的包
        for package in state.packages:
            pkg_path = (target_dir / package.name).resolve()
            if not pkg_path.is_dir():
                continue

            if package.name in expected_links:
                first = expected_links[package.name].relative_to(PROJECT_ROOT)
                second = pkg_path.relative_to(PROJECT_ROOT)
                fail(
                    f"skill name collision when linking: {package.name!r}\n"
                    f"  first:  {first}\n"
                    f"  second: {second}"
                )
            expected_links[package.name] = pkg_path

    print(f"Linking {len(expected_links)} skills to {dest_path.as_posix()}/")

    created = 0
    updated = 0
    pruned = 0

    project_root_resolved = PROJECT_ROOT.resolve()

    # 清理死链或在 --force 下强制排他清理
    for entry in sorted(dest_path.iterdir()):
        entry_name = entry.name

        if entry.is_symlink():
            try:
                raw_target = os.readlink(entry)
                is_pointing_to_fskills = str(project_root_resolved) in os.path.abspath(
                    os.path.join(dest_path, raw_target)
                )
            except OSError:
                is_pointing_to_fskills = False

            if entry_name not in expected_links:
                # 指向本项目但不再激活的旧软链默认清理；外部软链仅在 --force 时清理
                if is_pointing_to_fskills or force:
                    print(f"  - prune link: {entry_name}")
                    entry.unlink()
                    pruned += 1
                continue

        elif entry_name in expected_links:
            if force:
                print(f"  - force remove existing non-symlink: {entry_name}")
                shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
                pruned += 1
            else:
                fail(
                    f"destination item already exists and is not a symlink: {entry}\n"
                    f"  use --force to overwrite and remove existing non-symlink items."
                )

    # 建立软链接
    for skill_name, src_path in expected_links.items():
        link_target = dest_path / skill_name

        if link_target.is_symlink():
            try:
                current_src = link_target.resolve()
                if current_src == src_path:
                    continue
            except (OSError, RuntimeError):
                pass
            link_target.unlink()
            updated += 1
        else:
            created += 1

        print(f"  + link: {skill_name} -> {src_path.relative_to(PROJECT_ROOT)}")
        link_target.symlink_to(src_path, target_is_directory=True)

    print(
        f"Completed: {created} created, {updated} updated, {pruned} pruned."
        if (created or updated or pruned)
        else "All links are already up-to-date."
    )
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def usage() -> None:
    print(
        "Usage:\n"
        "  python .github/scripts/source.py check [--json]\n"
        "  python .github/scripts/source.py update\n"
        "  python .github/scripts/source.py link <destination> [--force]"
    )


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        usage()
        return 2

    command = argv[1]
    if command in {"-h", "--help", "help"}:
        usage()
        return 0

    if command == "check":
        as_json = len(argv) == 3 and argv[2] == "--json"
        if len(argv) == 3 and not as_json:
            usage()
            return 2
        if len(argv) > 3:
            usage()
            return 2
        return cmd_check(as_json=as_json)

    if command == "update":
        if len(argv) != 2:
            usage()
            return 2
        return cmd_update()

    if command == "link":
        if len(argv) < 3:
            usage()
            return 2

        destination = None
        force = False

        for arg in argv[2:]:
            if arg == "--force":
                force = True
            elif not arg.startswith("-") and destination is None:
                destination = arg
            else:
                usage()
                return 2

        if destination is None:
            usage()
            return 2

        return cmd_link(destination, force=force)

    print(f"ERROR: unknown command: {command}", file=sys.stderr)
    usage()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
