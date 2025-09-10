import decimal
D = decimal.Decimal

def validate_receipt(doc):
    errors = []
    try:
        subtotal = D(doc['totals']['subtotal'])
        tax = D(doc['totals']['tax'])
        total = D(doc['totals']['total'])
        shipping = D(doc.get('charges', {}).get('shipping','0.00'))
        other = D(doc.get('charges', {}).get('other','0.00'))
        items_sum = sum(D(i['amount']) for i in doc.get('items',[]))
        if (items_sum != subtotal):
            errors.append('Items do not sum to subtotal')
        expected_total = (subtotal + tax + shipping + other).quantize(D('0.01'))
        if expected_total != total:
            errors.append('subtotal + tax + shipping + other != total')
    except Exception as e:
        errors.append(f'Computation error: {e}')
    return errors