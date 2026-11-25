from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def roles_required(*role_names):
    """
    Decorator to restrict access to specific roles.
    Checks backend permissions on every route.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            user_roles = [r.name for r in current_user.roles]
            # Owner has overall access
            if 'owner' in user_roles:
                return f(*args, **kwargs)
            
            # Check if user has at least one of the required roles
            for role in role_names:
                if role in user_roles:
                    return f(*args, **kwargs)
            
            flash('You do not have permission to access this resource.', 'danger')
            abort(403)
        return decorated_function
    return decorator


def role_forbidden(*role_names):
    """
    Decorator to forbid specific roles (e.g. read-only auditor cannot perform POST/mutations).
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            user_roles = [r.name for r in current_user.roles]
            for role in role_names:
                if role in user_roles and 'owner' not in user_roles and 'admin' not in user_roles:
                    flash('Auditor role is read-only. Modification transactions are not permitted.', 'danger')
                    abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
