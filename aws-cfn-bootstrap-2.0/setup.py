#!/usr/bin/env python3

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

from distutils.core import setup, Distribution
import sys

name = 'aws-cfn-bootstrap'
version = '2.0'

if sys.version_info[0] == 2 or (sys.version_info[0] == 3 and sys.version_info[1] < 4):
    print("Error: Python 3.4+ is required, but found:\n" + sys.version)
    sys.exit(1)

rpm_requires = ['python >= 3.4', 'python-daemon', 'pystache', 'python-setuptools']
dependencies = ['python-daemon>=2.1,<2.2', 'pystache>=0.4.0', 'docutils', 'setuptools<=57.5.0']

_distclass = Distribution
_opts = {
         'bdist_rpm': {'requires': rpm_requires}
        }
_data_files = [('share/doc/%s-%s' % (name, version), ['license/NOTICE.txt', 'license/LICENSE.txt', 'CHANGELOG.txt']),
               ('init/redhat', ['init/redhat/cfn-hup']),
               ('init/ubuntu', ['init/ubuntu/cfn-hup']),
               ('init/systemd', ['init/systemd/cfn-hup.service'])]
try:
    import py2exe
    class WindowsDistribution(Distribution):
        def __init__(self, attrs):
            self.com_server = []
            self.ctypes_com_server = []
            self.service = ["cfnbootstrap.winhup"]
            self.isapi = []
            self.windows = []
            self.zipfile = 'library.zip'
            self.console = ['bin/cfn-init', 'bin/cfn-signal', 'bin/cfn-get-metadata', 'bin/cfn-hup', 'bin/cfn-elect-cmd-leader', 'bin/cfn-send-cmd-result', 'bin/cfn-send-cmd-event']
            Distribution.__init__(self, attrs)
    _distclass = WindowsDistribution
    _opts['py2exe'] = {
                        'typelibs': [('{000C1092-0000-0000-C000-000000000046}', 1033, 1, 0),
                                     ('{E34CB9F1-C7F7-424C-BE29-027DCC09363A}', 0, 1, 0)],
                        'excludes': ['pyreadline', 'difflib', 'distutils', 'doctest', 'pdb', 'unittest', 'adodbapi'],
                        'includes': ['dbm', 'win32com'],
                        'dll_excludes': ['msvcr71.dll', 'w9xpopen.exe', ''],
                        'skip_archive': True
                      }
    _data_files = [('', ['license/win/NOTICE.txt', 'license/win/LICENSE.rtf', 'cfnbootstrap/packages/requests/cacert.pem', 'cfnbootstrap/resources/documents/endpoints.json', 'CHANGELOG.txt'])]
except ImportError:
    pass

setup(
    distclass=_distclass,
    name='aws-cfn-bootstrap',
    version='2.0',
    description='An EC2 bootstrapper for CloudFormation',
    long_description="Bootstraps EC2 instances by retrieving and processing the Metadata block of a CloudFormation resource.",
    author='AWS CloudFormation',
    url='http://aws.amazon.com/cloudformation/',
    license='Apache 2.0',
    classifiers=['License :: OSI Approved :: Apache Software License'],
    packages=[
        'cfnbootstrap',
        'cfnbootstrap.packages',
        'cfnbootstrap.packages.requests',
        'cfnbootstrap.packages.requests.packages',
        'cfnbootstrap.packages.requests.packages.charset_normalizer',
        'cfnbootstrap.packages.requests.packages.urllib3',
        'cfnbootstrap.packages.requests.packages.urllib3.packages',
        'cfnbootstrap.packages.requests.packages.urllib3.contrib',
        'cfnbootstrap.packages.requests.packages.urllib3.util',
        'cfnbootstrap.packages.requests.packages.urllib3.packages.ssl_match_hostname',
        'cfnbootstrap.resources',
        'cfnbootstrap.resources.documents'
    ],
    excluded=['setup.cfg'],
    install_requires=dependencies,
    scripts=['bin/cfn-init', 'bin/cfn-signal', 'bin/cfn-get-metadata', 'bin/cfn-hup', 'bin/cfn-elect-cmd-leader', 'bin/cfn-send-cmd-result', 'bin/cfn-send-cmd-event'],
    data_files=_data_files,
    package_data={'cfnbootstrap': ['packages/requests/cacert.pem', 'resources/documents/endpoints.json']},
    options=_opts
)
