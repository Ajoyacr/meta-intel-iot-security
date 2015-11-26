# Author:       Patrick Ohly <patrick.ohly@intel.com>
# Copyright:    Copyright (C) 2015 Intel Corporation
#
# This file is licensed under the MIT license, see COPYING.MIT in
# this source distribution for the terms.

# A custom scheduler for bitbake which runs rm_work tasks more
# aggressively than the default schedule chosen by rm_work.
# To use it, add to local.conf:
#   BB_SCHEDULERS = "rmwork.RunQueueSchedulerRmWork"
#   BB_SCHEDULER = "rmwork"
# Then run:
#   PYTHONPATH=<path to the directory with rmwork.py> bitbake ...


import bb
from bb.runqueue import RunQueueSchedulerCompletion as BaseScheduler
import time

class RunQueueSchedulerRmWork(BaseScheduler):
    """
    Similar to RunQueueSchedulerCompletion, but in addition, rm_work tasks
    get a priority higher than anything else and get run even when the maximum
    number of tasks is reached. Together this ensures that nothing blocks running
    the rm_work tasks once they become ready to run.
    """
    name = "rmwork"

    def __init__(self, runqueue, rqdata):
        BaseScheduler.__init__(self, runqueue, rqdata)

        self.number_compile_tasks = int(self.rq.cfgData.getVar("BB_NUMBER_COMPILE_THREADS", True) or \
                                        self.rq.number_tasks)
        if self.number_compile_tasks > self.rq.number_tasks:
            bb.fatal("BB_NUMBER_COMPILE_THREADS %d must be <= BB_NUMBER_THREADS %d" % \
                     (self.number_compile_tasks, self.rq.number_tasks))
        bb.note('BB_NUMBER_COMPILE_THREADS %d BB_NUMBER_THREADS %d' % \
                (self.number_compile_tasks, self.rq.number_tasks))

        self.rmwork_tasks = set()
        for taskid in xrange(self.numTasks):
            taskname = self.rqdata.runq_task[taskid]
            # Detect 'rm_work tasks based on their name.
            # Kind of a hack, but works...
            if taskname == 'do_rm_work':
                self.rmwork_tasks.add(taskid)
                bb.note('Found do_rm_work: %s' % self.describe_task(taskid))

        # Move all rm_work tasks to the head of the queue (because
        # earlier = lower priority = runs earlier).
        rmwork_index = 0
        for index in xrange(self.numTasks):
            taskid = self.prio_map[index]
            if taskid in self.rmwork_tasks:
                del self.prio_map[index]
                self.prio_map.insert(rmwork_index, taskid)
                rmwork_index += 1

    def next(self):
        taskid = self.next_buildable_task()
        if taskid is not None:
            if self.rq.stats.active < self.rq.number_tasks:
                # Impose additional constraint on the number of compile tasks.
                # The reason is that each compile task itself is allowed to run
                # multiple processes, and therefore it makes sense to run less
                # of them without also limiting the number of other tasks.
                taskname = self.rqdata.runq_task[taskid]
                if taskname == 'do_compile':
                    active = [x for x in xrange(self.numTasks) if \
                              self.rq.runq_running[x] and not self.rq.runq_complete[x]]
                    active_compile = [x for x in active if self.rqdata.runq_task[x] == 'do_compile']
                    if len(active_compile) >= self.number_compile_tasks:
                        # bb.note('Not starting compile task %s, already have %d running: %s' % \
                        #         (self.describe_task(taskid),
                        #          len(active_compile),
                        #          [self.describe_task(x) for x in active]))
                        # Enabling the debug output above shows that it gets triggered even
                        # when nothing changed. Returning None here seems to trigger some kind of
                        # busy polling. Work around that for now by sleeping.
                        time.sleep(0.1)
                        return None
                return taskid
            if taskid in self.rmwork_tasks:
                bb.note('Choosing task %s despite task limit.' % self.describe_task(taskid))
                return taskid

    def describe_task(self, taskid):
        result = 'ID %d = %s' % (taskid, self.rqdata.get_user_idstring(taskid))
        if self.rev_prio_map:
            result = result + (' pri %d' % self.rev_prio_map[taskid])
        return result
