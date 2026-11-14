# System Inspector descriptor-relative traversal

The unified System Inspector traverses a selected directory tree using pinned
directory file descriptors. It opens every component of the selected root
path from the filesystem root without following symlinks, then opens child
directories and regular files
relative to the already-open parent descriptor and uses O_NOFOLLOW plus
O_DIRECTORY for directory opens. File descriptors are checked with fstat
before reading, and symlink entries are not followed.

This closes the path re-resolution gap in which a directory component could
be replaced between enumeration and a later absolute-path open. The traversal
continues to enforce global entry, file-count, per-file-byte, and aggregate
byte budgets. Files are read through their opened descriptors; growth beyond
the permitted read limit is rejected.

The implementation fails closed on platforms that do not expose both
O_NOFOLLOW and O_DIRECTORY. It does not claim to provide a filesystem
snapshot: files may still be modified in place while being read, and the
inspector does not prevent changes to the contents of already-open regular
files. For forensic reproducibility, inspect an immutable snapshot or
read-only filesystem image. This is static source/metadata inspection, not
sandboxed execution or a proof that the scanned tree is benign.
