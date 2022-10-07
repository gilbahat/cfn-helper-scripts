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

from cfnbootstrap import util
from cfnbootstrap.service_tools import ServiceTool
from cfnbootstrap.util import LoggingProcessHelper
from cfnbootstrap.construction_errors import ToolError
import collections
import logging
import os

log = logging.getLogger("cfn.init")


class SystemDTool(ServiceTool):
    """
    Manage service via SystemD
    """

    def __init__(self) -> None:
        super().__init__()
        self._executable = None

    def _get_executable(self):
        _path = "/usr/bin/systemctl"
        if os.path.exists(_path):
            return _path
        else:
            log.error("systemctl is not available")
            raise ToolError("SystemD is not available on the instance")

    def apply(self, action, changes=collections.defaultdict(list)):
        """
        Take a dict of service config
        Sample input
        {
            "nginx" : {
                "enabled" : "true",
                "ensureRunning" : "true",
                "files" : ["/etc/nginx/nginx.conf"],
                "sources" : ["/var/www/html"]
                },
                "php-fastcgi" : {
                    "enabled" : "true",
                    "ensureRunning" : "true",
                    "packages" : { "yum" : ["php", "spawn-fcgi"] }
                },
                "sendmail" : {
                    "enabled" : "false",
                    "ensureRunning" : "false"
                }
            }
        }
        """
        if not action.keys():
            log.debug("No SystemD scripts specified")
            return

        self._executable = self._get_executable()

        for service_name, service_properties in action.items():
            should_force_restart = self._detect_required_restart(
                service_properties, changes)

            if "enabled" in service_properties:
                self._set_service_enabled(
                    service_name, util.interpret_boolean(service_properties["enabled"]))
            else:
                log.debug(
                    "Not modifying enabled state of service: {}".format(service_name))

            if should_force_restart:
                log.debug(
                    "Restarting {} due to change detected in dependency".format(service_name))
                self._restart_service(service_name)
            elif "ensureRunning" in service_properties:
                should_ensure_running = util.interpret_boolean(
                    service_properties["ensureRunning"])
                is_service_running = self._is_service_running(service_name)
                if should_ensure_running and not is_service_running:
                    log.debug(
                        "Starting service {} as it is not running".format(service_name))
                    self._start_service(service_name)
                elif not should_ensure_running and is_service_running:
                    log.debug(
                        "Stopping service {} as it is running".format(service_name))
                    self._stop_service(service_name)
                else:
                    log.debug(
                        "No need to modify running status of service {}".format(service_name))
            else:
                log.debug(
                    "Not modifying running state of service {}".format(service_name))

    def _restart_service(self, service):
        reload_cmd = [self._executable, "daemon-reload"]
        reload_result = LoggingProcessHelper(reload_cmd).call()

        if reload_result.returncode:
            log.error(
                "SystemD failed to reload configuration for service {}".format(service))
            raise ToolError("Could not relaod configuration for {}".format(
                service), reload_result.returncode)

        restart_cmd = [self._executable, "reload-or-restart", service]
        restart_result = LoggingProcessHelper(restart_cmd).call()

        if restart_result.returncode:
            log.error("SystemD failed to reload or restart service {}".format(service))
            raise ToolError("Could not reload or restart service {}".format(
                service), restart_result.returncode)

    def _start_service(self, service):
        cmd = [self._executable, "start", service]
        result = LoggingProcessHelper(cmd).call()

        if result.returncode:
            log.error("Could not start service {}; return code was {}".format(
                service, result.returncode))
            log.debug("Service output: {}".format(result.stdout))
            raise ToolError("Could not start {}".format(service))
        else:
            log.info("Started {} successfully".format(service))

    def _stop_service(self, service):
        cmd = [self._executable, "stop", service]
        result = LoggingProcessHelper(cmd).call()

        if result.returncode:
            log.error("Could not stop service {}; return code was {}".format(
                service, result.returncode))
            log.debug("Service output: {}".format(result.stdout))
            raise ToolError("Could not stop {}".format(service))
        else:
            log.info("Stopped {} successfully".format(service))

    def _is_service_running(self, service):
        cmd = [self._executable, "is-active", service]
        result = LoggingProcessHelper(cmd).call()

        return result.returncode == 0

    def _set_service_enabled(self, service, enabled=True):
        should_enabled = 'enable' if enabled else 'disable'

        cmd = [self._executable, should_enabled, service]
        result = LoggingProcessHelper(cmd).call()

        if result.returncode:
            log.error("SystemD failed with error {}. Output: {}".format(
                result.returncode, result.stdout))
            raise ToolError("Could not {} service {}".format(
                should_enabled, service))
        else:
            log.info("{} service {}".format(should_enabled, service))
