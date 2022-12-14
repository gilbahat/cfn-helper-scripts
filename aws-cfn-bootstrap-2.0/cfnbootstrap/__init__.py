# ==============================================================================
# Copyright 2011 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================


import logging.config
import os.path
import sys
import stat
import os
from io import StringIO


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


_config = """[loggers]
keys=root,cfninit,cfnclient,cfnhup,wire,cmd
[handlers]
keys=%(all_handlers)s,null
[formatters]
keys=amzn,amzn_cmd
[logger_root]
level=NOTSET
handlers=%(root_handler)s
[logger_cfninit]
level=NOTSET
handlers=%(root_handler)s
qualname=cfn.init
propagate=0
[logger_wire]
level=NOTSET
handlers=%(wire_handler)s
qualname=wire
propagate=0
[logger_cfnhup]
level=NOTSET
handlers=%(root_handler)s
qualname=cfn.hup
propagate=0
[logger_cfnclient]
level=NOTSET
handlers=%(root_handler)s
qualname=cfn.client
propagate=0
[logger_cmd]
level=NOTSET
handlers=%(cmd_handler)s
qualname=cfn.init.cmd
propagate=0
[handler_default]
class=handlers.RotatingFileHandler
level=%(conf_level)s
formatter=amzn
args=('%(conf_file)s', 'a', 5242880, 5, 'UTF-8')
[handler_wire]
class=handlers.RotatingFileHandler
level=DEBUG
formatter=amzn
args=('%(wire_file)s', 'a', 5242880, 5, 'UTF-8')
[handler_null]
class=cfnbootstrap.NullHandler
args=()
[handler_cmd]
class=handlers.RotatingFileHandler
level=DEBUG
formatter=amzn_cmd
args=('%(cmd_file)s', 'a', 5242880, 5, 'UTF-8')
[handler_tostderr]
class=StreamHandler
level=%(conf_level)s
formatter=amzn
args=(sys.stderr,)
[formatter_amzn]
format=%(asctime)s [%(levelname)s] %(message)s
datefmt=
class=logging.Formatter
[formatter_amzn_cmd]
format=%(asctime)s P%(process)d [%(levelname)s] %(message)s
datefmt=
class=logging.Formatter
"""


def resetGroupWorldWritable(fullname):
    current_file_mode = stat.S_IMODE(os.stat(fullname).st_mode)
    # reset group and world writable attribute
    current_file_mode = current_file_mode & 0o755
    os.chmod(fullname, current_file_mode)


def _getLogFile(log_dir, filename):
    if log_dir:
        return os.path.join(log_dir, filename)
    if os.name == 'nt':
        logdir = os.path.expandvars(r'${SystemDrive}\cfn\log')
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        return logdir + os.path.sep + filename
    return '/var/log/%s' % filename


def configureLogging(level='INFO', quiet=False, filename='cfn-init.log', log_dir=None, wire_log=True, cmd_log=True):

    output_file = _getLogFile(log_dir, filename)

    config = {'conf_level': level,
              'root_handler': 'default',
              'conf_file': output_file}
    all_handlers = ["default"]

    if wire_log:
        wire_file = _getLogFile(log_dir, 'cfn-wire.log')
        config['wire_file'] = wire_file
        config['wire_handler'] = 'wire'
        all_handlers.append("wire")
    else:
        config['wire_handler'] = 'null'

    if cmd_log:
        cmd_file = _getLogFile(log_dir, 'cfn-init-cmd.log')
        config['cmd_file'] = cmd_file
        config['cmd_handler'] = 'cmd'
        all_handlers.append("cmd")
    else:
        config['cmd_handler'] = 'null'

    config['all_handlers'] = ','.join(all_handlers)

    try:
        logging.config.fileConfig(StringIO(_config), config)
        # make sure any generated log files are not world or group writable
        resetGroupWorldWritable(output_file)
        if wire_log:
            resetGroupWorldWritable(wire_file)
        if cmd_log:
            resetGroupWorldWritable(cmd_file)
    except IOError:
        config['all_handlers'] = 'tostderr'
        config['root_handler'] = 'tostderr'
        config['wire_handler'] = 'null'
        config['cmd_handler'] = 'null'
        if not quiet:
            print("Could not open {} for logging.  Using stderr instead.".format(
                output_file), file=sys.stderr)
        logging.config.fileConfig(StringIO(_config), config)
