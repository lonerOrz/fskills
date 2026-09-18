# Agent skills path
pi_skills := "~/.config/pi/skills"
opencode_skills := "~/.config/opencode/skills"

default:
    @just --list

# check synchronization state against remote sources
check *flags:
    python3 .github/scripts/source.py check {{flags}}

# update and reconcile skill packages with lockfile
update:
    python3 .github/scripts/source.py update

# link skill packages to destination path (preserves external symlinks)
link path *flags:
    python3 .github/scripts/source.py link {{path}} {{flags}}

link-opencode *flags:
    python3 .github/scripts/source.py link {{opencode_skills}} {{flags}}

link-pi *flags:
    python3 .github/scripts/source.py link {{pi_skills}} {{flags}}
