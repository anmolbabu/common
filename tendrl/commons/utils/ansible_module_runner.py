import os
import subprocess
import tempfile

import ansible.executor.module_common as module_common
from ansible import modules

from tendrl.commons.event import Event
from tendrl.commons.message import Message

try:
    import json
except ImportError:
    import simplejson as json


class AnsibleExecutableGenerationFailed(Exception):
    def __init__(self, module_path=None, arguments=None, err=None):
        self.message = "Executabe could not be generated for module" \
                       " %s . Error: %s" % (
                           str(module_path), str(err))


class AnsibleModuleNotFound(Exception):
    def __init__(self, module_path=None):
        self.message = "Ansible module %s not found" % str(module_path)


class AnsibleRunner(object):
    """Class that can be used to run ansible modules

    """

    def __init__(
        self,
        module_path,
        publisher=None,
        node_id=None,
        socket_path=None,
        **kwargs
    ):
        self.module_path = modules.__path__[0] + "/" + module_path
        self.publisher = publisher
        self.node_id = node_id
        self.socket_path = socket_path
        if not publisher:
            self.publisher = NS.publisher_id
        if not node_id:
            self.node_id = NS.node_context.node_id
        if not socket_path:
            self.socket_path = NS.config.data['logging_socket_path']
        if not os.path.isfile(self.module_path):
            Event(
                Message(
                    priority="debug",
                    publisher=self.publisher,
                    payload={"message": "Module path: %s does not exist" %
                                        self.module_path
                             },
                    node_id=self.node_id
                ),
                socket_path=self.socket_path
            )
            raise AnsibleModuleNotFound(module_path=self.module_path)
        if kwargs == {}:
            Event(
                Message(
                    priority="error",
                    publisher=self.publisher,
                    payload={"message": "Empty argument dictionary"},
                    node_id=self.node_id
                ),
                socket_path=self.socket_path
            )
            raise ValueError
        else:
            self.argument_dict = kwargs
            self.argument_dict['_ansible_selinux_special_fs'] = \
                ['nfs', 'vboxsf', 'fuse', 'ramfs']

    def __generate_executable_module(self):
        modname = os.path.basename(self.module_path)
        modname = os.path.splitext(modname)[0]
        try:
            (module_data, module_style, shebang) = \
                module_common.modify_module(
                    modname,
                    self.module_path,
                    self.argument_dict,
                    task_vars={}
                )
        except Exception as e:
            Event(
                Message(
                    priority="error",
                    publisher=self.publisher_id,
                    payload={"message": "Could not generate ansible "
                                        "executable data "
                                        "for module  : %s. Error: %s" %
                                        (self.module_path, str(e))
                             },
                    node_id=self.node_id
                ),
                socket_path=self.socket_path
            )
            raise AnsibleExecutableGenerationFailed(
                module_path=self.module_path,
                err=str(e)
            )
        return module_data

    def run(self):
        module_data = self.__generate_executable_module()
        _temp_file = tempfile.NamedTemporaryFile(mode="w+",
                                                 prefix="tendrl_ansible_",
                                                 suffix="exec",
                                                 dir="/tmp",
                                                 delete=False)

        _temp_file.write(module_data)
        _temp_file.close()

        try:
            os.system("chmod +x %s" % _temp_file.name)
            cmd = subprocess.Popen(_temp_file.name, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE
                                   )
            out, err = cmd.communicate()
            result = json.loads(out)

        except (subprocess.CalledProcessError, ValueError) as ex:
            result = repr(ex)
            err = result
        finally:
            os.remove(_temp_file.name)

        return result, err
