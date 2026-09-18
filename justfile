# check synchronization state against remote sources
check *flags:
    python3 .github/scripts/source.py check {{flags}}

# update and reconcile skill packages with lockfile
update:
    python3 .github/scripts/source.py update

# link skill packages to destination path (preserves external symlinks)
link path *flags:
    python3 .github/scripts/source.py link {{path}} {{flags}}
