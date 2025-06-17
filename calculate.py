import math
import random

def calculate_products(product_type_id, material_type_id, total_material, param1, param2):
    product_coefficients = {1: 1.5, 2: 2.0}
    material_defect_rates = {1: 0.1, 2: 0.2}

    if (product_type_id not in product_coefficients
        or material_type_id not in material_defect_rates
        or total_material <= 0
        or param1 <= 0
        or param2 <= 0):
        return -1

    material_per_unit = param1 * param2 * product_coefficients[product_type_id]
    defect_rate = material_defect_rates[material_type_id]
    total_products = (total_material * (1 - defect_rate)) / material_per_unit

    return math.floor(total_products)

def calculate_discount(total_quantity):
    if total_quantity < 10000:
        return 0
    elif 10000 <= total_quantity < 50000:
        return 5
    elif 50000 <= total_quantity < 300000:
        return 10
    else:
        return 15
