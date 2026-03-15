This directory contains the world files that get scattered across the container
at build time. The creature has to find them.

They are NOT placed in /agent (the creature's workspace).
They go in /home/agent, /opt, /tmp, /usr/share, etc.

The creature needs shell_exec("find / ...") or exploration to discover them.
