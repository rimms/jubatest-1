# -*- coding: utf-8 -*-

"""
Provides local process management interface.
"""

import os
import errno
import time
from subprocess import Popen, PIPE

from .unit import JubaTestFixtureFailedError
from .logger import log

class LocalSubprocess(object):
    def __init__(self, args, env=None):
        """
        Prepares for process invocation.
        """
        self.args = args
        if env:
            self.env = env
        else:
            self.env = os.environ
        self.stdout = None
        self.stderr = None
        self._process = None

    def __del__(self):
        """
        Process should be stopped before destruction.
        """
        if not hasattr(self, '_process'):
          # except for constructor failures
          return

        p = self._process
        if p is not None and p.poll() is None:
            log.warning('local process is still running! KILLing... %s', self.args)
            p.kill()

    def start(self):
        """
        Invokes process.
        """
        if self._process:
            raise JubaTestFixtureFailedError('cannot start again using same instance')
        log.debug('starting process: %s', self.args)
        self._process = Popen(self.args, env=self.env, stdin=PIPE, stdout=PIPE, stderr=PIPE, preexec_fn=os.setpgrp, close_fds=True)
        log.debug('started process: %s', self.args)

    def wait(self, stdin=None):
        """
        Wait for the invoked process.
        When the process is stopped, gather the stdin/stdout.
        """
        if not self._process:
            raise JubaTestFixtureFailedError('this instance has not been started yet')

        log.debug('waiting for process to complete: %s', self.args)
        (self.stdout, self.stderr) = self._process.communicate(stdin)
        log.debug('process completed: %s', self.args)
        returncode = self._process.returncode
        self._process = None
        return returncode

    def stop(self, kill=False):
        """
        Stops (usually TERM, but KILL at your will) the invoked process.
        """
        if not self._process:
            raise JubaTestFixtureFailedError('this instance has not been started yet')

        try:
            if kill:
                log.debug('KILLing process')
                self._process.kill()
            else:
                log.debug('terminating process')
                self._process.terminate()
        except OSError as e:
            if e.errno != errno.ESRCH: # "No such process"
                raise e
            # may be a race between poll and signal; just ignore
            log.debug('race between poll and signal detected')
        finally:
            (self.stdout, self.stderr) = self._process.communicate()
            self._process = None

    def is_running(self):
        """
        Returns whether the process we invoked is still running.
        """
        if self._process and self._process.poll() is None:
            return True
        return False
