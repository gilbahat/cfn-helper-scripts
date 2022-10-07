#==============================================================================
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
#==============================================================================

import logging
import sys
import os
import re
import shutil

_scheduler_supported = True
try:
    import win32com.client
    from pythoncom import com_error
except ImportError:
    _scheduler_supported = False

log = logging.getLogger("cfn.init")

def get_scheduler():
    try:
        if win32com.client.gencache.is_readonly == True:
            win32com.client.gencache.is_readonly = False
            win32com.client.gencache.Rebuild()
        scheduler = win32com.client.gencache.EnsureDispatch('{0F87369F-A4E5-4CFC-BD3E-73E6154572DD}', bForDemand=0)
    except Exception as e:
        MODULE_LIST = [m.__name__ for m in sys.modules.values()]
        for module in MODULE_LIST:
            if re.match(r'win32com\.gen_py\..+', module):
                del sys.modules[module]
        path_to_delete = os.path.join(os.environ.get('LOCALAPPDATA'), 'Temp', 'gen_py')
        if os.path.exists(path_to_delete):
            shutil.rmtree(path_to_delete)
        dir_exist = os.path.exists(path_to_delete)
        scheduler = win32com.client.gencache.EnsureDispatch("{0F87369F-A4E5-4CFC-BD3E-73E6154572DD}", bForDemand=0)
    return scheduler

def set_reboot_trigger():
    if not _scheduler_supported:
        log.debug("Not setting a reboot trigger as scheduling support is not available")
        return

    log.debug("Get scheduler for set_reboot_trigger")
    scheduler = get_scheduler()
    scheduler.Connect()

    log.debug("Creating Scheduled Task for cfn-init resume")

    root_folder = scheduler.GetFolder("\\")
    task_definition = scheduler.NewTask(0) # This must always be 0

    registration_info = task_definition.RegistrationInfo
    registration_info.Description = "This will resume cfn-init after the system has booted"
    registration_info.Author = "Amazon Web Services"

    task_definition.Settings.StartWhenAvailable = True
    task_definition.Settings.RunOnlyIfNetworkAvailable = True
    task_definition.Settings.RestartCount = 3
    task_definition.Settings.RestartInterval = "PT1M"

    trigger = task_definition.Triggers.Create(win32com.client.constants.TASK_TRIGGER_BOOT)
    trigger = win32com.client.CastTo(trigger, "IBootTrigger")
    trigger.Id = "CfnInitBootTrigger"
    trigger.Delay = "PT30S"

    action = task_definition.Actions.Create(win32com.client.constants.TASK_ACTION_EXEC)
    action = win32com.client.CastTo(action, "IExecAction")
    action.Path = sys.executable
    action.Arguments = "-v --resume"

    task_definition.Principal.UserId="NT AUTHORITY\SYSTEM"
    task_definition.Principal.RunLevel=win32com.client.constants.TASK_RUNLEVEL_HIGHEST

    try:
        root_folder.RegisterTaskDefinition("cfn-init Resume Trigger",
                                           task_definition,
                                           win32com.client.constants.TASK_CREATE,
                                           None,
                                           None,
                                           win32com.client.constants.TASK_LOGON_SERVICE_ACCOUNT)
    except com_error:
        log.debug("Scheduled task already exists; not updating")
    else:
        log.debug("Scheduled Task created")


def clear_reboot_trigger():
    if not _scheduler_supported:
        log.debug("Not clearing reboot trigger as scheduling support is not available")
        return

    log.debug("Get scheduler for clear_reboot_trigger")
    scheduler = get_scheduler()
    scheduler.Connect()

    log.debug("Deleting Scheduled Task for cfn-init resume")

    root_folder = scheduler.GetFolder("\\")
    try:
        root_folder.DeleteTask("cfn-init Resume Trigger", 0)
        log.debug("Scheduled Task deleted")
    except com_error:
        log.debug("Scheduled Task did not exist")