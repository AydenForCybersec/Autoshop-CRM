from ..models.customer import Customer


def get_customers_paginated(page: int, per_page: int = 10):
    return Customer.query.order_by(Customer.name).paginate(
        page=page,
        per_page=per_page,
        error_out=False,
    )
