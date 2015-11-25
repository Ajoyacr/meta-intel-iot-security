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

        self.rev_prio_map = range(self.numTasks)
        for taskid in xrange(self.numTasks):
            self.rev_prio_map[self.prio_map[taskid]] = taskid
        bb.note('Original priorities: %s' % [self.describe_task(x) for x in xrange(self.numTasks)])

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

        self.rev_prio_map = range(self.numTasks)
        for taskid in xrange(self.numTasks):
            self.rev_prio_map[self.prio_map[taskid]] = taskid
        bb.note('Modified priorities: %s' % [self.describe_task(x) for x in xrange(self.numTasks)])

    def next(self):
        taskid = self.next_buildable_task()
        if taskid is not None:
            if self.rq.stats.active < self.rq.number_tasks:
                return taskid
            if taskid in self.rmwork_tasks:
                bb.note('Choosing task %s despite task limit.' % self.describe_task(taskid))
                return taskid

    def describe_task(self, taskid):
        result = 'ID %d = %s' % (taskid, self.rqdata.get_user_idstring(taskid))
        if self.rev_prio_map:
            result = result + (' pri %d' % self.rev_prio_map[taskid])
        return result
