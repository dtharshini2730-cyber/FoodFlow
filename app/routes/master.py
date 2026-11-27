from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app import db
from app.models.master import Customer, Supplier, Product, RawMaterial, PackagingMaterial, Unit
from app.models.user import User, Role
from app.models.audit import AuditLog
from app.utils.decorators import roles_required, role_forbidden

master_bp = Blueprint('master', __name__)


# ---------------- CUSTOMERS ----------------
@master_bp.route('/customers')
@login_required
def customers():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    state_filter = request.args.get('state', '').strip()
    
    query = Customer.query
    if search:
        query = query.filter(Customer.name.ilike(f'%{search}%') | Customer.mobile_number.ilike(f'%{search}%'))
    if state_filter:
        query = query.filter_by(state=state_filter)
        
    # If salesman, can see their assigned customers
    if current_user.has_role('salesman') and not (current_user.has_role('owner') or current_user.has_role('admin')):
        query = query.filter_by(assigned_salesman_id=current_user.id)
        
    pagination = query.order_by(Customer.name.asc()).paginate(page=page, per_page=15, error_out=False)
    salesmen = User.query.join(User.roles).filter_by(name='salesman').all()
    
    return render_template(
        'master/customers.html',
        customers=pagination.items,
        pagination=pagination,
        search=search,
        state_filter=state_filter,
        salesmen=salesmen
    )


@master_bp.route('/customers/add', methods=['POST'])
@login_required
@roles_required('owner', 'admin')
def add_customer():
    name = request.form.get('name', '').strip()
    customer_type = request.form.get('customer_type', 'Retailer')
    contact_person = request.form.get('contact_person', '').strip()
    mobile_number = request.form.get('mobile_number', '').strip()
    address = request.form.get('address', '').strip()
    state = request.form.get('state', 'Tamil Nadu').strip()
    gstin = request.form.get('gstin', '').strip() or None
    assigned_salesman_id = request.form.get('assigned_salesman_id', type=int) or None
    credit_limit = Decimal(request.form.get('credit_limit', '0.00'))
    
    if not name or not mobile_number or not address:
        flash('Customer Name, Mobile Number, and Address are required.', 'danger')
        return redirect(url_for('master.customers'))
        
    customer = Customer(
        name=name,
        customer_type=customer_type,
        contact_person=contact_person,
        mobile_number=mobile_number,
        address=address,
        state=state,
        gstin=gstin,
        assigned_salesman_id=assigned_salesman_id,
        credit_limit=credit_limit,
        is_active=True
    )
    db.session.add(customer)
    db.session.commit()
    
    AuditLog.log(
        user_id=current_user.id,
        action='CREATE',
        module='Customers',
        record_id=customer.id,
        new_values={'name': name, 'state': state},
        description=f"Created customer '{name}'."
    )
    flash(f"Customer '{name}' added successfully.", 'success')
    return redirect(url_for('master.customers'))


@master_bp.route('/customers/<int:id>/toggle-status', methods=['POST'])
@login_required
@roles_required('owner', 'admin')
def toggle_customer_status(id):
    customer = Customer.query.get_or_404(id)
    customer.is_active = not customer.is_active
    db.session.commit()
    status_str = "activated" if customer.is_active else "deactivated"
    flash(f"Customer '{customer.name}' has been {status_str}.", 'info')
    return redirect(url_for('master.customers'))


# ---------------- SUPPLIERS ----------------
@master_bp.route('/suppliers')
@login_required
@roles_required('owner', 'admin', 'auditor')
def suppliers():
    suppliers_list = Supplier.query.order_by(Supplier.name.asc()).all()
    return render_template('master/suppliers.html', suppliers=suppliers_list)


@master_bp.route('/suppliers/add', methods=['POST'])
@login_required
@roles_required('owner', 'admin')
def add_supplier():
    name = request.form.get('name', '').strip()
    contact_details = request.form.get('contact_details', '').strip()
    gstin = request.form.get('gstin', '').strip() or None
    address = request.form.get('address', '').strip()
    state = request.form.get('state', 'Tamil Nadu').strip()
    
    if not name or not address:
        flash('Supplier Name and Address are required.', 'danger')
        return redirect(url_for('master.suppliers'))
        
    supplier = Supplier(
        name=name,
        contact_details=contact_details,
        gstin=gstin,
        address=address,
        state=state,
        is_active=True
    )
    db.session.add(supplier)
    db.session.commit()
    
    AuditLog.log(
        user_id=current_user.id,
        action='CREATE',
        module='Suppliers',
        record_id=supplier.id,
        new_values={'name': name, 'state': state},
        description=f"Added supplier '{name}'."
    )
    flash(f"Supplier '{name}' added successfully.", 'success')
    return redirect(url_for('master.suppliers'))


# ---------------- PRODUCTS ----------------
@master_bp.route('/products')
@login_required
def products():
    products_list = Product.query.order_by(Product.name.asc()).all()
    return render_template('master/products.html', products=products_list)


@master_bp.route('/products/add', methods=['POST'])
@login_required
@roles_required('owner', 'admin')
def add_product():
    name = request.form.get('name', '').strip()
    sku = request.form.get('sku', '').strip()
    category = request.form.get('category', 'Snacks').strip()
    pack_size = request.form.get('pack_size', '200 g').strip()
    selling_price = Decimal(request.form.get('selling_price', '50.00'))
    gst_rate = Decimal(request.form.get('gst_rate', '5.00'))
    hsn_code = request.form.get('hsn_code', '19059040').strip()
    unit = request.form.get('unit', 'packets').strip()
    description = request.form.get('description', '').strip()
    
    if not name or not sku:
        flash('Product Name and SKU are required.', 'danger')
        return redirect(url_for('master.products'))
        
    product = Product(
        name=name,
        sku=sku,
        category=category,
        pack_size=pack_size,
        selling_price=selling_price,
        gst_rate=gst_rate,
        hsn_code=hsn_code,
        unit=unit,
        description=description,
        is_active=True
    )
    db.session.add(product)
    db.session.commit()
    
    flash(f"Product '{name}' created successfully.", 'success')
    return redirect(url_for('master.products'))


# ---------------- RAW MATERIALS ----------------
@master_bp.route('/raw-materials')
@login_required
def raw_materials():
    materials = RawMaterial.query.order_by(RawMaterial.name.asc()).all()
    return render_template('master/raw_materials.html', materials=materials)


@master_bp.route('/raw-materials/add', methods=['POST'])
@login_required
@roles_required('owner', 'admin', 'production')
def add_raw_material():
    name = request.form.get('name', '').strip()
    sku = request.form.get('sku', '').strip()
    base_unit = request.form.get('base_unit', 'kg').strip()
    reorder_level = Decimal(request.form.get('reorder_level', '10.000'))
    
    if not name or not sku:
        flash('Material Name and SKU are required.', 'danger')
        return redirect(url_for('master.raw_materials'))
        
    material = RawMaterial(
        name=name,
        sku=sku,
        base_unit=base_unit,
        opening_stock=Decimal('0.000'),
        reorder_level=reorder_level,
        current_rate=Decimal('0.0000'),
        is_active=True
    )
    db.session.add(material)
    db.session.commit()
    
    flash(f"Raw material '{name}' added.", 'success')
    return redirect(url_for('master.raw_materials'))


# ---------------- PACKAGING MATERIALS ----------------
@master_bp.route('/packaging')
@login_required
def packaging():
    packaging_list = PackagingMaterial.query.order_by(PackagingMaterial.name.asc()).all()
    return render_template('master/packaging.html', packaging=packaging_list)


@master_bp.route('/packaging/add', methods=['POST'])
@login_required
@roles_required('owner', 'admin', 'production')
def add_packaging():
    name = request.form.get('name', '').strip()
    sku = request.form.get('sku', '').strip()
    unit = request.form.get('unit', 'pcs').strip()
    reorder_level = Decimal(request.form.get('reorder_level', '50.000'))
    
    if not name or not sku:
        flash('Packaging Name and SKU are required.', 'danger')
        return redirect(url_for('master.packaging'))
        
    pkg = PackagingMaterial(
        name=name,
        sku=sku,
        unit=unit,
        opening_quantity=Decimal('0.000'),
        reorder_level=reorder_level,
        current_rate=Decimal('0.0000'),
        is_active=True
    )
    db.session.add(pkg)
    db.session.commit()
    
    flash(f"Packaging material '{name}' added.", 'success')
    return redirect(url_for('master.packaging'))


# ---------------- USER MANAGEMENT ----------------
@master_bp.route('/users')
@login_required
@roles_required('admin')
def users():
    users_list = User.query.order_by(User.id.asc()).all()
    roles_list = Role.query.all()
    return render_template('master/users.html', users=users_list, roles=roles_list)


@master_bp.route('/users/add', methods=['POST'])
@login_required
@roles_required('admin')
def add_user():
    full_name = request.form.get('full_name', '').strip()
    username = request.form.get('username', '').strip().lower()
    email = request.form.get('email', '').strip().lower()
    phone = request.form.get('phone', '').strip()
    role_name = request.form.get('role', 'salesman').strip().lower()
    password = request.form.get('password', '')
    
    if not full_name or not username or not email or not password:
        flash('Full Name, Username, Email, and Password are required.', 'danger')
        return redirect(url_for('master.users'))
        
    existing = User.query.filter((User.email == email) | (User.username == username)).first()
    if existing:
        flash(f"A user with email '{email}' or username '{username}' already exists.", 'danger')
        return redirect(url_for('master.users'))
        
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        flash(f"Invalid role '{role_name}'.", 'danger')
        return redirect(url_for('master.users'))
        
    new_user = User(
        full_name=full_name,
        username=username,
        email=email,
        phone=phone,
        is_active=True
    )
    new_user.set_password(password)
    new_user.roles.append(role)
    db.session.add(new_user)
    db.session.commit()
    
    AuditLog.log(
        user_id=current_user.id,
        action='CREATE',
        module='Users',
        record_id=new_user.id,
        new_values={'email': email, 'role': role_name},
        description=f"Admin created user account '{full_name}' ({email}) with role '{role_name}'."
    )
    flash(f"User account '{full_name}' created successfully with role '{role_name}'.", 'success')
    return redirect(url_for('master.users'))


@master_bp.route('/users/<int:id>/toggle-status', methods=['POST'])
@login_required
@roles_required('admin')
def toggle_user_status(id):
    if id == current_user.id:
        flash('You cannot deactivate your own account.', 'warning')
        return redirect(url_for('master.users'))
        
    target_user = User.query.get_or_404(id)
    target_user.is_active = not target_user.is_active
    db.session.commit()
    
    status_str = "activated" if target_user.is_active else "deactivated"
    AuditLog.log(
        user_id=current_user.id,
        action='UPDATE',
        module='Users',
        record_id=target_user.id,
        description=f"User '{target_user.email}' was {status_str} by {current_user.email}."
    )
    flash(f"User '{target_user.full_name}' has been {status_str}.", 'info')
    return redirect(url_for('master.users'))
