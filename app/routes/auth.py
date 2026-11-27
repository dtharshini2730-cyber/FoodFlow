from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.models.audit import AuditLog

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact the administrator.', 'danger')
                return render_template('auth/login.html')
                
            login_user(user, remember=remember)
            flash(f'Welcome back, {user.full_name}!', 'success')
            
            # Redirect to role-specific starting screen
            if user.has_role('salesman') and not (user.has_role('owner') or user.has_role('admin')):
                return redirect(url_for('orders.new_order'))
            elif user.has_role('production') and not (user.has_role('owner') or user.has_role('admin')):
                return redirect(url_for('production.index'))
                
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
            
        flash('Invalid email or password. Please check your credentials.', 'danger')
        
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'change_password':
            current_pwd = request.form.get('current_password', '')
            new_pwd = request.form.get('new_password', '')
            confirm_pwd = request.form.get('confirm_password', '')
            
            if not current_user.check_password(current_pwd):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('auth.profile'))
                
            if len(new_pwd) < 6:
                flash('New password must be at least 6 characters.', 'danger')
                return redirect(url_for('auth.profile'))
                
            if new_pwd != confirm_pwd:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('auth.profile'))
                
            current_user.set_password(new_pwd)
            db.session.commit()
            
            AuditLog.log(
                user_id=current_user.id,
                action='UPDATE',
                module='Users',
                record_id=current_user.id,
                description=f"User '{current_user.email}' updated their account password."
            )
            flash('Password updated successfully.', 'success')
            return redirect(url_for('auth.profile'))
            
    return render_template('auth/profile.html', user=current_user)
