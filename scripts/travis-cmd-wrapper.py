#!/usr/bin/python
#
# Runs a command, pipes its output to stdout, and injects status
# reports at regular time interval.
#
# This ensures that TravisCI does not abort the command just because
# it is silent for more than 10 minutes, as it can happen with bitbake
# when working on a single complex task, like "bitbake linux-yocto".
#
# Piping bitbake stdout has the advantage that bitbake enters
# non-interactive output mode, which it would do when run by TravisCI
# directly.
#
# Finally, the default status messages give some sense of memory
# and disk usage, which is critical in the rather constrained
# TravisCI environments.

import errno
import optparse
import signal
import subprocess
import sys

parser = optparse.OptionParser()
parser.add_option("-s", "--status",
                  help="invoked in a shell when it is time for a status report",
                  # 200 columns is readable in the TravisCI Web UI without wrapping.
                  # Depends of course on screen and font size.
                  default="date; free; df -h .; top -n 1; ps x --cols 200 --forest",
                  metavar="SHELL-CMD")
parser.add_option("-i", "--interval",
                  help="repeat status at intervals of this amount of seconds, 0 to disable",
                  default=300,
                  metavar="SECONDS", type="int")

(options, args) = parser.parse_args()

# Set up status alarm.
def status(signum, frame):
    subprocess.call(options.status, shell=True)
    if options.interval > 0:
        signal.alarm(options.interval)

# Run command.
try:
    cmd = subprocess.Popen(args, stdout=subprocess.PIPE)

    # Arm timer and handler.
    signal.signal(signal.SIGALRM, status)
    if options.interval > 0:
        signal.alarm(options.interval)

    while cmd.poll() is None:
        try:
            line = cmd.stdout.readline()
            sys.stdout.write(line)
            sys.stdout.flush()
        except IOError, ex:
            if ex.errno != errno.EINTR:
                raise
finally:
    # If we go down, so must our child...
    if cmd.poll() is None:
        cmd.kill()

exit(1 if cmd.returncode else 0)
