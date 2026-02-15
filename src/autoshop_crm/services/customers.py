from ..extensions import db
from ..models.customer import Customer


def get_customers_paginated(page: int, per_page: int = 10):
    return Customer.query.order_by(Customer.name).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )


def create_customer(name, email=None, phone=None):
    customer = Customer(name=name, email=email, phone=phone)
    db.session.add(customer)
    db.session.commit()
    return customer


def get_customer(customer_id: int):
    return Customer.query.get_or_404(customer_id)


def get_all_customers():
    return Customer.query.order_by(Customer.name).all()
