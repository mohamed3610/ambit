"""
ambit — scoped, multi-dimensional authorization for Django.

Import from the submodules (kept out of this file so the package loads
before Django's app registry is ready):

    from ambit.dimensions import register_dimension
    from ambit.policies import ScopePolicy, ScopeBinding, GLOBAL_SCOPE_POLICY
    from ambit.services.authorization import (
        has_authorized_scope, authorized_queryset, can_access_object,
    )
"""
__version__ = "0.1.0"
