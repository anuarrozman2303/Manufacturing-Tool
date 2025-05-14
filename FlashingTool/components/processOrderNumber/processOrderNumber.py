# components/processOrderNumber/processOrderNumber.py

def get_order_numbers(orders):
    order_numbers = list(set(order['order-no'] for order in orders))
    return order_numbers
