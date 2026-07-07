"""Delte konstanter for workspace-capabilities.

Udskilt fra workspace_capabilities.py (Boy Scout-reglen) som den ene sandhed
for capability-fil-navne, tekst-prefikser, output-grænser og exec-allowlists.
Både hoved-modulet og undermodulerne (exec/documents) importerer herfra, så der
ikke opstår dobbelt-sandhed. Ren data — ingen logik, ingen side-effekter.

Alle symboler re-eksporteres fra core.tools.workspace_capabilities for
bagudkompatibilitet.
"""
from __future__ import annotations

CAPABILITY_FILES = {
    "tools": "TOOLS.md",
    "skills": "SKILLS.md",
}
RUNTIME_NOTE_PREFIX = "RUNTIME_NOTE:"
READ_FILE_PREFIX = "READ_FILE:"
SEARCH_FILE_PREFIX = "SEARCH_FILE:"
READ_EXTERNAL_FILE_PREFIX = "READ_EXTERNAL_FILE:"
LIST_EXTERNAL_DIR_PREFIX = "LIST_EXTERNAL_DIR:"
EXEC_COMMAND_PREFIX = "EXEC_COMMAND:"
WRITE_FILE_PREFIX = "WRITE_FILE:"
WRITE_MEMORY_FILE_PREFIX = "WRITE_MEMORY_FILE:"
REPLACE_MEMORY_LINE_PREFIX = "REPLACE_MEMORY_LINE:"
DELETE_MEMORY_LINE_PREFIX = "DELETE_MEMORY_LINE:"
REWRITE_MEMORY_FILE_PREFIX = "REWRITE_MEMORY_FILE:"
APPEND_DAILY_MEMORY_PREFIX = "APPEND_DAILY_MEMORY:"
PROPOSE_SOURCE_EDIT_PREFIX = "PROPOSE_SOURCE_EDIT:"
WRITE_EXTERNAL_FILE_PREFIX = "WRITE_EXTERNAL_FILE:"
RUNTIME_INSPECT_PREFIX = "RUNTIME_INSPECT:"
PROJECT_GREP_PREFIX = "PROJECT_GREP:"
MULTI_READ_PREFIX = "MULTI_READ:"
PROJECT_OUTLINE_PREFIX = "PROJECT_OUTLINE:"
MAX_FILE_OUTPUT_CHARS = 8000
MAX_SEARCH_MATCHES = 5
MAX_MATCH_EXCERPT_CHARS = 160
MAX_EXEC_OUTPUT_CHARS = 4000
MAX_EXEC_SECONDS = 8
MAX_MULTI_READ_FILES = 10
MAX_MULTI_READ_CHARS = 24000
MAX_GREP_MATCHES = 50
MAX_GREP_MATCH_CHARS = 200
NON_DESTRUCTIVE_EXEC_ALLOWLIST = {
    "cd",
    "pwd",
    "ls",
    "lsblk",
    "lscpu",
    "lshw",
    "lspci",
    "cat",
    "head",
    "tail",
    "wc",
    "stat",
    "file",
    "free",
    "whoami",
    "id",
    "hostnamectl",
    "nvidia-smi",
    "nproc",
    "uname",
    "uptime",
    "date",
    "df",
    "ps",
    "pgrep",
    "env",
    "printenv",
    "rg",
    "find",
    "tree",
}
GIT_READ_EXEC_ALLOWLIST = {
    ("status",),
    ("diff", "--stat"),
    ("diff", "--name-only"),
    ("branch", "--show-current"),
    ("rev-parse", "--show-toplevel"),
    ("show", "--stat", "-n", "1"),
}
GIT_MUTATING_SUBCOMMANDS = {
    "add",
    "commit",
    "reset",
    "checkout",
    "switch",
    "restore",
    "merge",
    "rebase",
    "pull",
    "push",
    "stash",
    "cherry-pick",
    "revert",
    "fetch",
}
GIT_BLOCKED_SUBCOMMANDS = {
    "clean",
    "gc",
    "filter-branch",
    "worktree",
    "submodule",
    "config",
}
APPROVED_MUTATING_EXEC_ALLOWLIST = {
    "mv",
    "cp",
    "chmod",
}
APPROVED_SUDO_EXEC_ALLOWLIST = {
    "chmod",
    "chown",
    "systemctl",
    "journalctl",
    "docker",
    "apt",
    "apt-get",
    "dpkg",
    "pip",
    "pip3",
    "npm",
    "nvm",
    "snap",
    "flatpak",
    "dnf",
    "yum",
    "brew",
    "make",
    "cargo",
    "go",
    "kubectl",
    "tee",
    "cp",
    "mv",
    "mkdir",
    "rmdir",
    "ln",
    "tar",
    "curl",
    "wget",
    "mount",
    "umount",
    "fdisk",
    "parted",
    "lsblk",
    "blkid",
    "cryptsetup",
    "ufw",
    "iptables",
    "ip",
    "ip6tables",
    "ss",
    "netstat",
    "nginx",
    "apache2",
    "supervisorctl",
    "crontab",
    "useradd",
    "usermod",
    "userdel",
    "groupadd",
    "groupdel",
    "passwd",
    "visudo",
    "sed",
    "awk",
    "cat",
    "find",
    "install",
    "rsync",
    "dd",
}
MUTATING_EXEC_PROPOSAL_TOKENS = {
    "sudo",
    "mv",
    "cp",
    "chmod",
    "chown",
    "tee",
    "sed",
    "npm",
    "pip",
    "pip3",
    "apt",
    "apt-get",
    "dnf",
    "yum",
    "brew",
    "git",
    "make",
    "cargo",
    "go",
    "docker",
    "kubectl",
}
HARD_BLOCKED_EXEC_TOKENS = {
    "rm",
    "awk",
    "perl",
    "python",
    "python3",
    "node",
}
NON_DESTRUCTIVE_EXEC_REDIRECTION_PATTERNS = (
    ">>",
    "<<",
    ">",
    "<",
)
NON_DESTRUCTIVE_EXEC_SEGMENT_SEPARATORS = (
    "&&",
    "||",
    "|",
    ";",
)
