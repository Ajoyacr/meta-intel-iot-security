# Author:       Patrick Ohly <patrick.ohly@intel.com>
# Copyright:    Copyright (C) 2015 Intel Corporation
#
# This file is licensed under the MIT license, see COPYING.MIT in
# this source distribution for the terms.

# This class is used like rm_work:
# INHERIT += "rm_work_and_downloads"
#
# In addition to removing local build directories of a recipe, it also
# removes the downloaded source. For now, only normal archives are removed,
# repositories are left in place.

inherit rm_work

do_rm_work[postfuncs] += "rm_downloads"
python rm_downloads () {
    if bb.utils.contains('RM_WORK_EXCLUDE', d.getVar('PN', True), True, False, d):
        return
    dl_dir = os.path.normpath(d.getVar('DL_DIR', True)) + '/'
    src_uri = (d.getVar('SRC_URI', True) or "").split()
    fetch = bb.fetch2.Fetch(src_uri, d)
    ud = fetch.ud
    import shutil
    for u in ud.values():
        local = os.path.normpath(fetch.localpath(u.url))
        if os.path.normpath(local).startswith(dl_dir):
            # Different recipes may share the same source, for example
            # cross-localedef-native_2.22.bb and glibc_2.22.bb share
            # git://sourceware.org/git/glibc.git. Therefore it is not
            # entirely clear a) when a source is no longer needed and b)
            # how to remove the downloaded copy safely so that it
            # can be fetched again if used a second time, without
            # leading to race conditions (copy is in use by second recipe
            # while being deleted by the first one).
            #
            # For now, removal of directories is avoided because it
            # is more risky than removing a single file.
            if os.path.isdir(local):
                bb.note('Removing download directory: %s' % local)
                renamed = local + '.deleteme'
                os.rename(local, renamed)
                shutil.rmtree(renamed)
            elif os.path.exists(local):
                bb.note('Removing download file: %s' % local)
                os.unlink(local)
}
