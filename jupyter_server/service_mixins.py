# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
""" Mixin classes for composable services. """

from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbformat.sign import NotebookNotary

from .gateway.managers import GatewayClient
from .services.config import ConfigManager
from .services.contents.manager import ContentsManager
from .services.contents.filemanager import FileContentsManager
from .services.contents.largefilemanager import LargeFileManager
from .services.kernels.kernelmanager import MappingKernelManager
from .services.sessions.sessionmanager import SessionManager


class ApiMixin(object):
    """ Mixin class for the api service. """
    def get_services(self):
        services = ['api']
        services.extend(super(ApiMixin, self).get_services())
        return services


class AuthMixin(object):
    def get_services(self):
        services = ['auth']
        services.extend(super(AuthMixin, self).get_services())
        return services


class ConfigMixin(object):
    """ Mixin class for the config service. """
    def get_services(self):
        services = ['config']
        services.extend(super(ConfigMixin, self).get_services())
        return services

    def get_configurables(self):
        configurables = [ConfigManager]
        configurables.extend(super(ConfigMixin, self).get_configurables())
        return configurables

    def init_configurables(self):
        self.config_manager = self.config_manager_class(
            parent=self,
            log=self.log,
        )
        super(ConfigMixin, self).init_configurables()


class ContentsMixin(object):
    """ Mixin class for the contents service. """
    def get_services(self):
        services = ['contents']
        services.extend(super(ContentsMixin, self).get_services())
        return services

    def get_configurables(self):
        configurables = [ContentsManager, FileContentsManager, NotebookNotary]
        configurables.extend(super(ContentsMixin, self).get_configurables())
        return configurables

    def init_configurables(self):
        self.contents_manager = self.contents_manager_class(
            parent=self,
            log=self.log,
        )
        super(ContentsMixin, self).init_configurables()


class EditMixin(object):
    """ Mixin class for the edit service. """
    def get_services(self):
        services = ['edit']
        services.extend(super(EditMixin, self).get_services())
        return services

    def validate_dependencies(self):
        super(EditMixin, self).validate_dependencies()
        _validate_dependency(__class__.__name__, self, ContentsMixin)


class FilesMixin(object):
    """ Mixin class for the files service. """
    def get_services(self):
        services = ['files']
        services.extend(super(FilesMixin, self).get_services())
        return services

    def validate_dependencies(self):
        super(FilesMixin, self).validate_dependencies()
        _validate_dependency(__class__.__name__, self, ContentsMixin)


class KernelsMixin(object):
    """ Mixin class for the kernels service. """
    def get_services(self):
        services = ['kernels']
        services.extend(super(KernelsMixin, self).get_services())
        return services

    def get_configurables(self):
        configurables = [KernelManager, MappingKernelManager, GatewayClient]
        configurables.extend(super(KernelsMixin, self).get_configurables())
        return configurables

    def init_configurables(self):

        # If gateway server is configured, replace appropriate managers to perform redirection.  To make
        # this determination, instantiate the GatewayClient config singleton.
        self.gateway_config = GatewayClient.instance(parent=self)

        if self.gateway_config.gateway_enabled:
            self.kernel_manager_class = 'jupyter_server.gateway.managers.GatewayKernelManager'
            self.session_manager_class = 'jupyter_server.gateway.managers.GatewaySessionManager'
            self.kernel_spec_manager_class = 'jupyter_server.gateway.managers.GatewayKernelSpecManager'

        self.kernel_manager = self.kernel_manager_class(
            parent=self,
            log=self.log,
            connection_dir=self.runtime_dir,
            kernel_spec_manager=self.kernel_spec_manager,
        )
        super(KernelsMixin, self).init_configurables()

    def validate_dependencies(self):
        super(KernelsMixin, self).validate_dependencies()
        _validate_dependency(__class__.__name__, self, KernelspecsMixin)


class KernelspecsMixin(object):
    """ Mixin class for the kernelspecs service. """
    def get_services(self):
        services = ['kernelspecs']
        services.extend(super(KernelspecsMixin, self).get_services())
        return services

    def get_configurables(self):
        configurables = [KernelSpecManager]
        configurables.extend(super(KernelspecsMixin, self).get_configurables())
        return configurables

    def init_configurables(self):
        self.kernel_spec_manager = self.kernel_spec_manager_class(
            parent=self,
        )
        super(KernelspecsMixin, self).init_configurables()


class NbconvertMixin(object):
    """ Mixin class for the nbconvert service. """
    def get_services(self):
        services = ['nbconvert']
        services.extend(super(NbconvertMixin, self).get_services())
        return services

    def validate_dependencies(self):
        super(NbconvertMixin, self).validate_dependencies()
        _validate_dependency(__class__.__name__, self, ContentsMixin)


class SecurityMixin(object):
    """ Mixin class for the security service. """
    def get_services(self):
        services = ['security']
        services.extend(super(SecurityMixin, self).get_services())
        return services


class SessionsMixin(object):
    """ Mixin class for the sessions service. """
    def get_services(self):
        services = ['sessions']
        services.extend(super(SessionsMixin, self).get_services())
        return services

    def get_configurables(self):
        configurables = [SessionManager]
        configurables.extend(super(SessionsMixin, self).get_configurables())
        return configurables

    def init_configurables(self):
        self.session_manager = self.session_manager_class(
            parent=self,
            log=self.log,
            kernel_manager=self.kernel_manager,
            contents_manager=self.contents_manager,
        )
        super(SessionsMixin, self).init_configurables()

    def validate_dependencies(self):
        super(SessionsMixin, self).validate_dependencies()
        _validate_dependency(__class__.__name__, self, KernelsMixin)
        _validate_dependency(__class__.__name__, self, ContentsMixin)


class ShutdownMixin(object):
    """ Mixin class for the shutdown service. """
    def get_services(self):
        services = ['shutdown']
        services.extend(super(ShutdownMixin, self).get_services())
        return services


class ViewMixin(object):
    """ Mixin class for the view service. """
    def get_services(self):
        services = ['view']
        services.extend(super(ViewMixin, self).get_services())
        return services

    def validate_dependencies(self):
        super(ViewMixin, self).validate_dependencies()
        _validate_dependency(__class__.__name__, self, ContentsMixin)


def _validate_dependency(mixin_name, parent_instance, mixin_class):
    if not isinstance(parent_instance, mixin_class):
        raise TypeError("Mixin '{mixin_name}' has a dependency on {mixin_class} but class {parent} does not derive "
                        "from {mixin_class}.  Add {mixin_class} to {parent}'s class list or remove {mixin_name}.".
                        format(mixin_name=mixin_name,
                               mixin_class=mixin_class.__name__,
                               parent=parent_instance.__class__.__name__))