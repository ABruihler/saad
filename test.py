import logging
import os
import tempfile
import time
from distutils.dir_util import copy_tree

import core

logging.basicConfig(level=logging.DEBUG)

root_path = os.path.dirname(os.path.abspath(__file__))

with tempfile.TemporaryDirectory() as previous_dirname:
    with tempfile.TemporaryDirectory() as current_dirname:
        print('Copying current directory (as current commit)...')
        copy_tree(root_path, current_dirname)

        print('Copy current directory and resetting to HEAD (as previous commit)...')
        copy_tree(root_path, previous_dirname)
        os.chdir(previous_dirname)
        os.system('git reset --hard HEAD')

        os.chdir(root_path)

        print('Running probes...')
        start = time.time()
        core.iterate_over_configs(current_dirname, previous_dirname)
        # core.iterate_over_configs_parallel(current_dirname, previous_dirname)

        print('Probes finished')
        print('Took ' + str(time.time() - start) + ' seconds to run all probes')
