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
from cfnbootstrap.rpm_tools import RpmTool
from cfnbootstrap.util import LoggingProcessHelper
from cfnbootstrap.cfn_logging import CfnLogger
from cfnbootstrap.construction_errors import ToolError
import logging

log = CfnLogger(logging.getLogger("cfn.init"))


class ZypperTool(object):
    """Install packages use Zypper package manager"""

    def apply(self, action, auth_config=None):
        packages_changed = []

        if not action:
            log.debug("No packages specified for Zypper")
            return packages_changed

        # TODO: check if Zypper has `apt-cache -q gencaches` equivelant. Currently I don't think there is.

        package_specs_to_upgrade = []
        package_specs_to_downgrade = []

        for package_name in action:
            if action[package_name]:
                if isinstance(action[package_name], str):
                    package_version = action[package_name]
                else:
                    package_version = RpmTool.max_version(
                        action[package_name])
            else:
                package_version = None

            package_specs = "{}-{}".format(
                package_name, package_version) if package_version is not None else package_name

            if self._is_package_installed(package_specs):
                # Exact requested package spec is installed
                log.debug(
                    "{} will not be installed as it is already present".format(package_specs))
            elif not self._is_package_available(package_specs):
                # Not available, returns an error
                log.error(
                    "{} is not available to be installed".format(package_specs))
                raise ToolError(
                    "Zypper does not have {} available for installation".format(package_specs))
            elif package_version is None:
                package_specs_to_upgrade.append(package_specs)
                packages_changed.append(package_name)
            else:
                # a specific version is requested that's available but not installed.
                (_, installed_version) = RpmTool.get_package_version(
                    package_name, False)
                if self._should_upgrade(package_version, installed_version):
                    log.debug("Upgrading to {} from installed version {}".format(
                        package_specs, installed_version))
                    package_specs_to_upgrade.append(package_specs)
                else:
                    log.debug("Downgarding to {} from installed version {}".format(
                        package_specs, installed_version))
                    package_specs_to_downgrade.append(package_specs)
                packages_changed.append(package_name)

        if not packages_changed:
            log.info("All Zypper packages were already installed")
            return []

        if package_specs_to_upgrade:
            log.debug(
                "Installing/updating {} via zypper".format(package_specs_to_upgrade))
            upgrade_result = LoggingProcessHelper(
                ["zypper", "install", "-y"] + package_specs_to_upgrade).call()

            if upgrade_result.returncode != 0:
                log.error("Zypper failed. Output: {}".format(
                    upgrade_result.stdout))
                raise ToolError(
                    "Could not successfully install/update zypper packages", upgrade_result.returncode)

        if package_specs_to_downgrade:
            log.debug("Downgrading {} via zypper".format(
                package_specs_to_downgrade))
            downgrade_result = LoggingProcessHelper(
                ["zypper", "install", "-y", "--oldpackage", "--force-resolution"] + package_specs_to_downgrade).call()

            if downgrade_result.returncode != 0:
                log.error("Zypper failed. Output: {}".format(
                    downgrade_result.stdout))
                raise ToolError(
                    "Could not successfully downgrade zypper packages", downgrade_result.returncode)

        log.info("Zypper installed {}".format(
            package_specs_to_upgrade + package_specs_to_downgrade))

        return packages_changed

    def _should_upgrade(self, requested_package_version, installed_version):
        if not requested_package_version:
            log.debug("No requested version passed, try to upgrade")
            return True
        if not installed_version:
            log.debug("No installed version passed, try to upgrade")
            return True
        version_comparison = RpmTool.compare_rpm_versions(
            requested_package_version, installed_version)
        if version_comparison > 0:
            log.debug("Requested version {} is greater than installed version {}, will upgrade".format(
                requested_package_version, installed_version))
            return True
        else:
            log.debug("Requested version {} is NOT greater than installed version {}, will downgrade".format(
                requested_package_version, installed_version))
            return False

    def _is_package_installed(self, package_key):
        """
        Check if a package has been installed locally.
        package_key: could be package_name such as "git" or a package name with version such as "git-2.15-2.1"
        """
        log.debug("check if {} is already installed".format(package_key))
        query_result = LoggingProcessHelper(
            ["zypper", "search", "--match-exact", "--installed-only", package_key]).call()
        return query_result.returncode == 0

    def _is_package_available(self, package_key):
        """
        Check if a package is available for installation.
        package_key: could be package_name such as "git" or a package name with version such as "git-2.15-2.1"
        """
        query_result = LoggingProcessHelper(
            ["zypper", "search", "--match-exact", "--not-installed-only", package_key]).call()
        return query_result.returncode == 0
